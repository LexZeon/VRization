import UIKit
import MetalKit
import VRizationCore

final class ViewerController: UIViewController {
    private let client = StreamClient()
    private let motion = MotionSource()
    private var settings = VRSettings()
    private var sync = SettingsSync()
    private var renderer: StereoRenderer?
    private var metalView: MTKView!
    private let overlay = UIView()
    private var scroll: UIScrollView!
    private var content: UIStackView!
    private var status = UILabel(), frameStatus = UILabel()
    private var hostField = UITextField(), portField = UITextField(), codeField = UITextField()
    private var connectButton = UIButton(type: .system)
    private var modes = UISegmentedControl()
    private var invert = UISwitch()
    private var sliders: [SettingSlider] = []
    private var active = true
    private var statusKey = "waiting"
    private var frames = 0
    private var lastSent: TimeInterval = 0
    private var startedInitialUSB = false
    private var sampleFrames = 0
    private var frameSampleAt: TimeInterval = 0
    private var receiveFPS: Double = 0
    private var rtt: Double?
    private var frameWidth = 0, frameHeight = 0
    private var selectedTransport: StreamClient.Transport {
        let choice = argument("--transport") ?? UserDefaults.standard.string(forKey: "transport") ?? "usb"
        return choice == "lan" ? .lan : .usb
    }

    override var prefersStatusBarHidden: Bool { true }
    override var prefersHomeIndicatorAutoHidden: Bool { true }
    override var supportedInterfaceOrientations: UIInterfaceOrientationMask { .landscape }
    override var shouldAutorotate: Bool { true }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        overrideUserInterfaceStyle = .dark
        if let data = UserDefaults.standard.data(forKey: "displaySettings"),
           let saved = try? JSONDecoder().decode(VRSettings.self, from: data),
           let valid = try? saved.validated() { settings = valid }
        if !motion.available { settings.mode = "full" }
        metalView = MTKView(frame: .zero, device: MTLCreateSystemDefaultDevice())
        metalView.translatesAutoresizingMaskIntoConstraints = false
        metalView.accessibilityIdentifier = "vr.surface"
        metalView.isAccessibilityElement = true
        metalView.accessibilityLabel = "VRization"
        view.addSubview(metalView)
        NSLayoutConstraint.activate([
            metalView.leadingAnchor.constraint(equalTo: view.leadingAnchor), metalView.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            metalView.topAnchor.constraint(equalTo: view.topAnchor), metalView.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
        do { renderer = try StereoRenderer(view: metalView); renderer?.setSettings(settings) }
        catch { statusKey = "metalUnavailable" }
        let longPress = UILongPressGestureRecognizer(target: self, action: #selector(showSettings(_:)))
        metalView.addGestureRecognizer(longPress)
        let doubleTap = UITapGestureRecognizer(target: self, action: #selector(recenter))
        doubleTap.numberOfTapsRequired = 2; metalView.addGestureRecognizer(doubleTap)
        overlay.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(overlay)
        let width = overlay.widthAnchor.constraint(equalToConstant: 440)
        width.priority = .defaultHigh
        NSLayoutConstraint.activate([
            overlay.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 10),
            overlay.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 6),
            overlay.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -6), width,
            overlay.trailingAnchor.constraint(lessThanOrEqualTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -10)
        ])
        buildControls()
        wireCallbacks()
    }

    private func wireCallbacks() {
        client.onSessionStarted = { [weak self] in
            self?.sync.newSession(); self?.frames = 0; self?.sampleFrames = 0
            self?.frameSampleAt = ProcessInfo.processInfo.systemUptime; self?.receiveFPS = 0
        }
        client.onState = { [weak self] _, key in
            guard let self = self else { return }
            self.statusKey = key; self.updateStatus(); self.updateTracking()
            if self.client.state == .disconnected { self.renderer?.clear(); self.frameStatus.text = L.text("waitingFrame") }
        }
        client.onSettings = { [weak self] value, revision, sequence in
            guard let self = self, self.sync.accept(snapshot: value, revision: revision, clientSeq: sequence) else { return }
            let oldMode = self.settings.mode
            self.settings = value
            let fallback = !self.motion.available && value.mode != "full"
            if fallback { self.settings.mode = "full" }
            self.saveSettings(); self.refreshControls(); self.renderer?.setSettings(self.settings)
            if oldMode != self.settings.mode { self.recenter() }
            self.updateTracking()
            if fallback { self.statusKey = "sensorFallback"; self.updateStatus(); self.changed(sendNow: true) }
        }
        client.onFrame = { [weak self] image in
            guard let self = self, self.active else { return }
            do { try self.renderer?.submit(image) }
            catch { self.statusKey = "renderError"; self.updateStatus(); return }
            guard self.renderer != nil else { return }
            self.frames += 1; self.sampleFrames += 1
            self.frameWidth = image.width; self.frameHeight = image.height
            let now = ProcessInfo.processInfo.systemUptime
            if self.frames == 1 { self.updateFrameStatus() }
            if now - self.frameSampleAt >= 1 {
                self.receiveFPS = Double(self.sampleFrames) / (now - self.frameSampleAt)
                self.sampleFrames = 0; self.frameSampleAt = now; self.updateFrameStatus()
            }
        }
        client.onRTT = { [weak self] value in self?.rtt = value; if self?.client.state == .connected { self?.updateFrameStatus() } }
        motion.orientation = { [weak self] in self?.view.window?.windowScene?.interfaceOrientation ?? .landscapeRight }
        motion.onPose = { [weak self] pose in
            guard let self = self, self.active else { return }
            if self.settings.mode == "cinema" { self.renderer?.setPose(pose) }
            else if self.settings.mode == "fps" { self.client.sendPose(yaw: pose.yaw, pitch: pose.pitch) }
        }
        motion.onUnavailable = { [weak self] in
            guard let self = self else { return }
            self.settings.mode = "full"; self.statusKey = "sensorFallback"
            self.refreshControls(); self.updateStatus(); self.recenter(); self.changed(sendNow: true)
        }
    }

    private func buildControls() {
        overlay.subviews.forEach { $0.removeFromSuperview() }
        sliders = []
        let toolbar = UIStackView(arrangedSubviews: [button("hide", id: "settings.hide", action: #selector(hideSettings)),
            button("recenter", id: "view.recenter", action: #selector(recenter))])
        toolbar.axis = .horizontal; toolbar.spacing = 8; toolbar.distribution = .fillEqually
        toolbar.translatesAutoresizingMaskIntoConstraints = false; overlay.addSubview(toolbar)
        scroll = UIScrollView(); scroll.accessibilityIdentifier = "settings.scroll"
        scroll.backgroundColor = UIColor(red: 0.05, green: 0.09, blue: 0.15, alpha: 0.96)
        scroll.keyboardDismissMode = .onDrag
        scroll.translatesAutoresizingMaskIntoConstraints = false; overlay.addSubview(scroll)
        NSLayoutConstraint.activate([
            toolbar.topAnchor.constraint(equalTo: overlay.topAnchor), toolbar.leadingAnchor.constraint(equalTo: overlay.leadingAnchor),
            toolbar.trailingAnchor.constraint(equalTo: overlay.trailingAnchor), toolbar.heightAnchor.constraint(equalToConstant: 40),
            scroll.topAnchor.constraint(equalTo: toolbar.bottomAnchor, constant: 6), scroll.leadingAnchor.constraint(equalTo: overlay.leadingAnchor),
            scroll.trailingAnchor.constraint(equalTo: overlay.trailingAnchor), scroll.bottomAnchor.constraint(equalTo: overlay.bottomAnchor)
        ])
        content = UIStackView(); content.axis = .vertical; content.spacing = 10
        content.translatesAutoresizingMaskIntoConstraints = false; scroll.addSubview(content)
        NSLayoutConstraint.activate([
            content.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor, constant: 12),
            content.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor, constant: -16),
            content.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor, constant: 12),
            content.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor, constant: -12),
            content.widthAnchor.constraint(equalTo: scroll.frameLayoutGuide.widthAnchor, constant: -24)
        ])
        let title = label("VRization", size: 25); title.textColor = .systemTeal; content.addArrangedSubview(title)
        let languages = UISegmentedControl(items: ["English", "中文"])
        languages.accessibilityIdentifier = "language.picker"
        languages.selectedSegmentIndex = L.language == "zh-Hans" ? 1 : 0
        languages.addTarget(self, action: #selector(languageChanged(_:)), for: .valueChanged)
        content.addArrangedSubview(languages)
        let transport = UISegmentedControl(items: ["USB", "LAN"])
        transport.accessibilityIdentifier = "connection.transport"
        transport.selectedSegmentIndex = selectedTransport == .usb ? 0 : 1
        transport.addTarget(self, action: #selector(transportChanged(_:)), for: .valueChanged)
        content.addArrangedSubview(transport)
        status = label(L.text(statusKey), size: 14); status.accessibilityIdentifier = "connection.status"; content.addArrangedSubview(status)
        frameStatus = label(L.text("waitingFrame"), size: 12); frameStatus.accessibilityIdentifier = "frame.status"; content.addArrangedSubview(frameStatus)
        hostField = field("host", id: "connection.host", value: argument("--host") ?? UserDefaults.standard.string(forKey: "host") ?? "")
        portField = field("port", id: "connection.port", value: argument("--port") ?? UserDefaults.standard.string(forKey: "port") ?? "8765")
        portField.keyboardType = .numberPad
        let address = UIStackView(arrangedSubviews: [hostField, portField]); address.spacing = 8
        portField.widthAnchor.constraint(equalToConstant: 85).isActive = true
        address.isHidden = selectedTransport == .usb
        content.addArrangedSubview(address)
        codeField = field("code", id: "connection.code", value: argument("--code") ?? "")
        codeField.keyboardType = .numberPad; codeField.isSecureTextEntry = true
        codeField.isHidden = selectedTransport == .usb
        content.addArrangedSubview(codeField)
        connectButton = button("connect", id: "connection.toggle", action: #selector(toggleConnection))
        content.addArrangedSubview(connectButton)
        content.addArrangedSubview(label(L.text(selectedTransport == .usb ? "usbNotice" : "networkNotice"), size: 12))
        let sensor = label(L.text("noSensor"), size: 13); sensor.accessibilityIdentifier = "motion.status"
        sensor.isHidden = motion.available; sensor.textColor = .systemTeal; content.addArrangedSubview(sensor)
        modes = UISegmentedControl(items: [L.text("full"), L.text("cinema"), L.text("fps")])
        modes.accessibilityIdentifier = "view.mode"
        modes.setEnabled(motion.available, forSegmentAt: 1); modes.setEnabled(motion.available, forSegmentAt: 2)
        modes.addTarget(self, action: #selector(modeChanged), for: .valueChanged); content.addArrangedSubview(modes)
        content.addArrangedSubview(label(L.text("headsetFit"), size: 18))
        addSlider("scale", path: \.scale, min: 0.5, max: 1, steps: 100)
        addSlider("offsetX", path: \.offsetX, min: -0.3, max: 0.3, steps: 120)
        addSlider("offsetY", path: \.offsetY, min: -0.3, max: 0.3, steps: 120)
        addSlider("eyeSeparation", path: \.eyeSeparation, min: 0, max: 0.2, steps: 100)
        addSlider("distortion", path: \.distortion, min: 0, max: 0.5, steps: 100)
        addSlider("fov", path: \.fov, min: 50, max: 110, steps: 60)
        addSlider("distance", path: \.distance, min: 1, max: 8, steps: 140)
        addSlider("sensitivity", path: \.sensitivity, min: 100, max: 3000, steps: 290)
        invert = UISwitch(); invert.accessibilityIdentifier = "view.invertY"
        invert.addTarget(self, action: #selector(invertChanged), for: .valueChanged)
        let invertRow = UIStackView(arrangedSubviews: [label(L.text("invertY"), size: 14), invert]); invertRow.spacing = 8
        content.addArrangedSubview(invertRow)
        content.addArrangedSubview(button("reset", id: "view.reset", action: #selector(resetSettings)))
        content.addArrangedSubview(button("licenses", id: "about.licenses", action: #selector(showLicense)))
        content.addArrangedSubview(label(L.text("help"), size: 12))
        refreshControls(); updateStatus()
        metalView.accessibilityHint = L.text("gestures")
    }

    private func label(_ text: String, size: CGFloat) -> UILabel {
        let label = UILabel(); label.text = text; label.numberOfLines = 0; label.font = .systemFont(ofSize: size)
        label.textColor = .white; return label
    }
    private func button(_ key: String, id: String, action: Selector) -> UIButton {
        let button = UIButton(type: .system); button.setTitle(L.text(key), for: .normal)
        button.titleLabel?.font = .systemFont(ofSize: 16, weight: .medium)
        button.backgroundColor = UIColor(white: 0.22, alpha: 1); button.layer.cornerRadius = 6
        button.accessibilityIdentifier = id; button.heightAnchor.constraint(greaterThanOrEqualToConstant: 38).isActive = true
        button.addTarget(self, action: action, for: .touchUpInside); return button
    }
    private func field(_ key: String, id: String, value: String) -> UITextField {
        let field = UITextField(); field.placeholder = L.text(key); field.text = value
        field.borderStyle = .roundedRect; field.autocorrectionType = .no; field.autocapitalizationType = .none
        field.keyboardType = .URL; field.accessibilityIdentifier = id
        field.heightAnchor.constraint(equalToConstant: 38).isActive = true; return field
    }
    private func argument(_ name: String) -> String? {
        let args = ProcessInfo.processInfo.arguments
        guard let index = args.firstIndex(of: name), args.indices.contains(index + 1) else { return nil }
        return args[index + 1]
    }
    private func addSlider(_ key: String, path: WritableKeyPath<VRSettings, Double>, min: Double, max: Double, steps: Int) {
        let slider = SettingSlider(key: key, path: path, lower: min, upper: max, steps: steps)
        slider.begin = { [weak self] in self?.sync.beginGesture() }
        slider.change = { [weak self] value, final in
            guard let self = self else { return }
            self.settings[keyPath: path] = value; self.changed(sendNow: final)
        }
        slider.end = { [weak self] in self?.sync.endGesture(); self?.changed(sendNow: true) }
        sliders.append(slider); content.addArrangedSubview(slider.label); content.addArrangedSubview(slider.control)
    }
    private func refreshControls() {
        modes.selectedSegmentIndex = settings.mode == "cinema" ? 1 : settings.mode == "fps" ? 2 : 0
        modes.setEnabled(motion.available, forSegmentAt: 1); modes.setEnabled(motion.available, forSegmentAt: 2)
        for slider in sliders { slider.refresh(settings) }
        invert.isOn = settings.invertY
    }
    private func updateStatus() {
        status.text = L.text(statusKey)
        let key = client.state == .connected ? "disconnect" : client.state == .connecting ? (selectedTransport == .usb ? "usbStop" : "cancel") : "connect"
        connectButton.setTitle(L.text(key), for: .normal)
    }
    private func updateFrameStatus() {
        guard frames > 0 else { return }
        let ping = rtt.map { String(format: "%.0f ms", $0) } ?? "—"
        frameStatus.text = String(format: L.text("frameFormat"), frameWidth, frameHeight, receiveFPS, ping, frames)
    }
    private func saveSettings() { if let data = try? JSONEncoder().encode(settings) { UserDefaults.standard.set(data, forKey: "displaySettings") } }
    private func changed(sendNow: Bool) {
        guard (try? settings.validated()) != nil else { return }
        sync.edited(); renderer?.setSettings(settings); saveSettings()
        let now = ProcessInfo.processInfo.systemUptime
        if sendNow || now - lastSent >= 0.08 {
            lastSent = now
            if let sequence = try? sync.nextSequence(), client.sendSettings(settings, sequence: sequence) {
                try? sync.sent(sequence: sequence, snapshot: settings)
            }
        }
    }
    @objc private func languageChanged(_ picker: UISegmentedControl) {
        let language = picker.selectedSegmentIndex == 1 ? "zh-Hans" : "en"
        guard language != L.language else { return }
        client.disconnect(notify: false); motion.stop(); renderer?.clear()
        L.language = language; statusKey = "disconnected"; buildControls()
    }
    @objc private func toggleConnection() {
        view.endEditing(true)
        if client.state != .disconnected { client.disconnect(); return }
        if selectedTransport == .usb { _ = client.connectUSB(); return }
        let host = hostField.text?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let port = (portField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        let code = (codeField.text ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        guard (try? ConnectionInput.url(host: host, port: port, token: code)) != nil, let number = Int(port) else {
            statusKey = "invalidAddress"; updateStatus(); return
        }
        UserDefaults.standard.set(host, forKey: "host"); UserDefaults.standard.set(port, forKey: "port")
        recenter()
        if !client.connect(host: host, port: number, code: code) { statusKey = "invalidAddress"; updateStatus() }
    }
    @objc private func transportChanged(_ picker: UISegmentedControl) {
        client.disconnect(notify: false); motion.stop(); renderer?.clear()
        UserDefaults.standard.set(picker.selectedSegmentIndex == 0 ? "usb" : "lan", forKey: "transport")
        statusKey = "disconnected"; buildControls()
    }
    @objc private func modeChanged() {
        settings.mode = ["full", "cinema", "fps"][modes.selectedSegmentIndex]
        if !motion.available { settings.mode = "full"; modes.selectedSegmentIndex = 0 }
        recenter(); changed(sendNow: true); updateTracking()
    }
    @objc private func invertChanged() { settings.invertY = invert.isOn; changed(sendNow: true) }
    @objc private func resetSettings() { let mode = settings.mode; settings = VRSettings(); settings.mode = mode; refreshControls(); changed(sendNow: true); recenter() }
    @objc private func recenter() { motion.recenter(); renderer?.setPose(Pose()); client.recenter() }
    @objc private func hideSettings() { view.endEditing(true); overlay.isHidden = true }
    @objc private func showSettings(_ gesture: UILongPressGestureRecognizer) { if gesture.state == .began { overlay.isHidden = false } }
    func suspendSession() {
        active = false; motion.stop(); client.disconnect(reason: "paused"); renderer?.clear(); metalView.isPaused = true
        UIApplication.shared.isIdleTimerDisabled = false
    }
    func resumeDisplay() {
        active = true; metalView.isPaused = false; UIApplication.shared.isIdleTimerDisabled = true; updateTracking()
    }
    private func updateTracking() {
        if active && client.state == .connected && settings.mode != "full" && motion.available { motion.start() }
        else { motion.stop() }
    }
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated); UIApplication.shared.isIdleTimerDisabled = true
        if !startedInitialUSB {
            startedInitialUSB = true
            if selectedTransport == .usb { _ = client.connectUSB() }
        }
    }
    override func viewWillTransition(to size: CGSize, with coordinator: UIViewControllerTransitionCoordinator) {
        super.viewWillTransition(to: size, with: coordinator)
        coordinator.animate(alongsideTransition: nil) { [weak self] _ in self?.recenter() }
    }
    @objc private func showLicense() {
        let text = Bundle.main.url(forResource: "LICENSE", withExtension: "txt").flatMap { try? String(contentsOf: $0, encoding: .utf8) } ?? "MIT"
        let controller = LicenseController(text: text)
        present(controller, animated: true)
    }
}

private final class SettingSlider: NSObject {
    let label = UILabel(), control = UISlider()
    let key: String, path: WritableKeyPath<VRSettings, Double>, lower: Double, upper: Double, steps: Int
    var begin: (() -> Void)?, change: ((Double, Bool) -> Void)?, end: (() -> Void)?
    init(key: String, path: WritableKeyPath<VRSettings, Double>, lower: Double, upper: Double, steps: Int) {
        self.key = key; self.path = path; self.lower = lower; self.upper = upper; self.steps = steps
        super.init()
        label.font = .systemFont(ofSize: 14); label.textColor = .white
        label.accessibilityIdentifier = "setting.\(key).label"
        control.minimumValue = 0; control.maximumValue = Float(steps)
        control.accessibilityIdentifier = "setting.\(key)"; control.accessibilityLabel = L.text(key)
        control.addTarget(self, action: #selector(start), for: .touchDown)
        control.addTarget(self, action: #selector(update), for: .valueChanged)
        control.addTarget(self, action: #selector(stop), for: [.touchUpInside, .touchUpOutside, .touchCancel])
    }
    private var value: Double {
        let step = Int(control.value.rounded())
        if step <= 0 { return lower }; if step >= steps { return upper }
        return lower + (upper - lower) * Double(step) / Double(steps)
    }
    func refresh(_ settings: VRSettings) {
        let value = settings[keyPath: path]
        control.value = Float((value - lower) / (upper - lower) * Double(steps)); show(value)
    }
    private func show(_ value: Double) {
        let formatted = key == "scale" ? String(format: "%.0f%%", value * 100) : String(format: "%.2f", value)
        label.text = L.text(key) + "  " + formatted; control.accessibilityValue = formatted
    }
    @objc private func start() { begin?() }
    @objc private func update() { let next = value; show(next); change?(next, !control.isTracking) }
    @objc private func stop() { end?() }
}

private final class LicenseController: UIViewController {
    let text: String
    init(text: String) { self.text = text; super.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { fatalError("init(coder:) is unavailable") }
    override func viewDidLoad() {
        super.viewDidLoad(); view.backgroundColor = .systemBackground
        let body = UITextView(); body.isEditable = false; body.text = text; body.font = .monospacedSystemFont(ofSize: 13, weight: .regular)
        let close = UIButton(type: .system); close.setTitle(L.text("close"), for: .normal)
        close.addTarget(self, action: #selector(dismissLicense), for: .touchUpInside)
        for child in [body, close] { child.translatesAutoresizingMaskIntoConstraints = false; view.addSubview(child) }
        NSLayoutConstraint.activate([
            close.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor), close.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -16),
            close.heightAnchor.constraint(equalToConstant: 44), body.topAnchor.constraint(equalTo: close.bottomAnchor),
            body.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 12), body.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -12),
            body.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor)
        ])
    }
    @objc private func dismissLicense() { dismiss(animated: true) }
}
