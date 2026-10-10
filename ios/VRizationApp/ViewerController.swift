import UIKit
import MetalKit
import VRizationCore
#if STEAMVR_PREVIEW
import VRizationSteamVRCore
#endif

final class ViewerController: UIViewController, UIScrollViewDelegate {
    private let client = StreamClient()
    private let usbControl = USBControlListener()
    private let motion = MotionSource()
    private var settings = VRSettings()
    private var sync = LocalProfileSync()
    private let preferenceStore = AppPreferencesStore()
    private var preferences = PhonePreferences()
    private var editor: HeadsetEditorView?
    private var editorEntry: VRSettings?
    private var launchOverridesActive = true
    private var renderer: StereoRenderer?
    private var metalView: MTKView!
    private let overlay = UIView()
    private var scroll: UIScrollView!
    private var content: UIStackView!
    private var status = UILabel(), frameStatus = UILabel()
    private var stabilizationNotice = UILabel()
    private var enhancedNotice = UILabel()
#if STEAMVR_PREVIEW
    private var steamNotice = UILabel()
#endif
    private var sensorNotice = UILabel()
    private var hostField = UITextField(), portField = UITextField(), codeField = UITextField()
    private var connectButton = UIButton(type: .system)
    private var modes = UISegmentedControl()
    private var invert = UISwitch()
    private var sliders: [SettingSlider] = []
    private var active = true
    private var statusKey = "waiting"
    private var frames = 0
    private var lastSent: TimeInterval = 0
    private var sampleFrames = 0
    private var frameSampleAt: TimeInterval = 0
    private var receiveFPS: Double = 0
    private var rtt: Double?
    private var frameWidth = 0, frameHeight = 0
    private var sourceIsStereo: Bool {
#if STEAMVR_PREVIEW
        return client.streamSession?.stereo == true
#else
        return false
#endif
    }
    private var selectedTransport: StreamClient.Transport {
        let choice = preferences.transport
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
        preferences = preferenceStore.load()
        if let route = argument("--transport"), ["usb", "lan"].contains(route) { preferences.transport = route }
        settings = preferences.settings
#if !STEAMVR_PREVIEW
        if !motion.available && settings.requiresMotion { settings.mode = "full" }
#endif
        client.setSettingsBase(settings)
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
        usbControl.onStop = { [weak self] in self?.client.disconnect() }
        usbControl.onConnect = { [weak self] in
            guard let self = self, self.active, self.client.state == .disconnected else { return }
            if self.selectedTransport != .usb {
                self.preferences.transport = "usb"; try? self.preferenceStore.save(self.preferences); self.buildControls()
            }
            self.recenter(); _ = self.client.connectUSB()
        }
        usbControl.onFailure = { [weak self] in
            guard let self = self, self.selectedTransport == .usb, self.client.state == .disconnected else { return }
            self.statusKey = "usbFailed"; self.updateStatus()
        }
        client.onSessionStarted = { [weak self] in
            self?.closeEditor(save: false, resumeMotion: false)
            if let self = self { self.sync.newSession(hasSavedProfile: self.preferences.hasCommittedProfile) }
            self?.frames = 0; self?.sampleFrames = 0
            self?.frameSampleAt = ProcessInfo.processInfo.systemUptime; self?.receiveFPS = 0
        }
        client.onState = { [weak self] _, key in
            guard let self = self else { return }
            self.statusKey = key; self.updateStatus(); self.updateTracking()
            self.updateStabilizationNotice()
            if self.client.state == .disconnected {
                self.closeEditor(save: false, resumeMotion: false)
                self.renderer?.clear(); self.frameStatus.text = L.text("waitingFrame")
                self.updateTestingGeometry()
            }
        }
        client.onSettings = { [weak self] value, revision, sequence in
            guard let self = self else { return }
            switch self.sync.receive(snapshot: value, revision: revision, clientSeq: sequence) {
            case .restoreLocal:
                self.sync.edited(); self.sendSettingsSnapshot(); self.updateTracking(); return
            case .ignore: return
            case .applyHost: break
            }
            guard value != self.settings || value != self.preferences.settings || !self.preferences.hasCommittedProfile else { return }
            let oldMode = self.settings.mode
            self.settings = value
            let fallback = !self.motion.available && value.requiresMotion && !self.sourceIsStereo
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
            self.editor?.refreshVideoAspect()
            self.updateTestingGeometry()
            let now = ProcessInfo.processInfo.systemUptime
            if self.frames == 1 { self.updateFrameStatus() }
            if now - self.frameSampleAt >= 1 {
                self.receiveFPS = Double(self.sampleFrames) / (now - self.frameSampleAt)
                self.sampleFrames = 0; self.frameSampleAt = now; self.updateFrameStatus()
            }
        }
        client.onRTT = { [weak self] value in self?.rtt = value; if self?.client.state == .connected { self?.updateFrameStatus() } }
        client.onCapabilitiesChanged = { [weak self] in self?.updateStabilizationNotice() }
#if STEAMVR_PREVIEW
        client.onStreamSession = { [weak self] descriptor in
            guard let self = self else { return }
            self.closeEditor(save: false, resumeMotion: false)
            self.motion.stop(); self.motion.recenter()
            self.renderer?.setStreamSession(descriptor)
            self.frameWidth = 0; self.frameHeight = 0
            self.refreshControls(); self.updateTracking()
        }
        motion.onQuaternion = { [weak self] quaternion in
            guard let self = self, self.active, self.editor == nil,
                  self.client.streamSession?.virtualHMD == true else { return }
            self.client.sendHMDPose(quaternion)
        }
#endif
        motion.orientation = { [weak self] in self?.view.window?.windowScene?.interfaceOrientation ?? .landscapeRight }
        motion.onPose = { [weak self] pose in
            guard let self = self, self.active, self.editor == nil else { return }
#if STEAMVR_PREVIEW
            guard self.client.streamSession?.inputTarget != .virtualHMD else { return }
#endif
            guard !self.sourceIsStereo else { return }
            if self.settings.mode == "cinema" { self.renderer?.setPose(pose) }
            else if self.settings.isFirstPerson { self.client.sendPose(yaw: pose.yaw, pitch: pose.pitch) }
        }
        motion.onUnavailable = { [weak self] in
            guard let self = self else { return }
            self.closeEditor(save: false, resumeMotion: false)
#if STEAMVR_PREVIEW
            if self.sourceIsStereo {
                self.client.invalidateTracking(); self.statusKey = "steamNoTracking"
                self.refreshControls(); self.updateStatus(); return
            }
#endif
            if self.settings.mode != "fps_enhanced" { self.settings.mode = "full" }
            self.statusKey = self.settings.mode == "fps_enhanced" ? "enhancedSensorFallback" : "sensorFallback"
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
        scroll = UIScrollView(); scroll.accessibilityIdentifier = "settings.scroll"; scroll.delegate = self
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
#if STEAMVR_PREVIEW
        let title = label("VRization SteamVR Experimental", size: 23)
#else
        let title = label("VRization", size: 25)
#endif
        title.textColor = .systemTeal; content.addArrangedSubview(title)
        let info = Bundle.main.infoDictionary ?? [:]
        let version = info["CFBundleShortVersionString"] as? String ?? "?"
        let build = info["CFBundleVersion"] as? String ?? "?"
        let versionInfo = label(String(format: L.text("versionInfo"), version, build), size: 13)
        versionInfo.accessibilityIdentifier = "version.info"
        content.addArrangedSubview(versionInfo)
#if STEAMVR_PREVIEW
        steamNotice = label(L.text("steamDirect"), size: 13)
        steamNotice.accessibilityIdentifier = "stream.session"
        steamNotice.textColor = .systemTeal; content.addArrangedSubview(steamNotice)
#endif
        content.addArrangedSubview(button("editorOpen", id: "view.editor", action: #selector(openEditor)))
        content.addArrangedSubview(label(L.text("editorHelp"), size: 12))
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
        hostField = field("host", id: "connection.host", value: argument("--host") ?? preferences.host)
        portField = field("port", id: "connection.port", value: argument("--port") ?? preferences.port)
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
#if STEAMVR_PREVIEW
        content.addArrangedSubview(label(L.text(selectedTransport == .usb ? "steamUSBNotice" : "networkNotice"), size: 12))
#else
        content.addArrangedSubview(label(L.text(selectedTransport == .usb ? "usbNotice" : "networkNotice"), size: 12))
#endif
        sensorNotice = label(L.text("noSensor"), size: 13); sensorNotice.accessibilityIdentifier = "motion.status"
        sensorNotice.isHidden = motion.available; sensorNotice.textColor = .systemTeal; content.addArrangedSubview(sensorNotice)
        modes = UISegmentedControl(items: [L.text("full"), L.text("cinema"), L.text("fps"), L.text("fps_enhanced")])
        modes.apportionsSegmentWidthsByContent = true
        modes.setTitleTextAttributes([.font: UIFont.systemFont(ofSize: 12)], for: .normal)
        modes.accessibilityIdentifier = "view.mode"
        modes.setEnabled(motion.available || sourceIsStereo, forSegmentAt: 1); modes.setEnabled(motion.available || sourceIsStereo, forSegmentAt: 2)
        modes.addTarget(self, action: #selector(modeChanged), for: .valueChanged); content.addArrangedSubview(modes)
        enhancedNotice = label(L.text("enhancedHelp"), size: 12)
        enhancedNotice.accessibilityIdentifier = "view.enhanced.notice"
        content.addArrangedSubview(enhancedNotice)
        content.addArrangedSubview(label(L.text("headsetFit"), size: 18))
        content.addArrangedSubview(label(L.text("precisionHelp"), size: 12))
        addSlider("scale", path: \.scale, min: 0.5, max: 1, steps: 50)
        addSlider("offsetX", path: \.offsetX, min: -0.3, max: 0.3, steps: 120)
        addSlider("offsetY", path: \.offsetY, min: -0.3, max: 0.3, steps: 120)
        addSlider("eyeSeparation", path: \.eyeSeparation, min: -1, max: 0.2, steps: 120)
        addSlider("distortion", path: \.distortion, min: 0, max: 0.5, steps: 100)
        addSlider("fov", path: \.fov, min: 50, max: 110, steps: 60)
        addSlider("distance", path: \.distance, min: 1, max: 8, steps: 140)
        addSlider("sensitivity", path: \.sensitivity, min: 100, max: 3000, steps: 290)
        addSlider("stabilization", path: \.stabilization, min: 0, max: 1, steps: 100)
        stabilizationNotice = label(L.text("stabilizationHelp"), size: 12)
        stabilizationNotice.accessibilityIdentifier = "setting.stabilization.notice"
        content.addArrangedSubview(stabilizationNotice)
        invert = UISwitch(); invert.accessibilityIdentifier = "view.invertY"
        invert.addTarget(self, action: #selector(invertChanged), for: .valueChanged)
        let invertRow = UIStackView(arrangedSubviews: [label(L.text("invertY"), size: 14), invert]); invertRow.spacing = 8
        content.addArrangedSubview(invertRow)
        content.addArrangedSubview(button("reset", id: "view.reset", action: #selector(resetSettings)))
        content.addArrangedSubview(button("licenses", id: "about.licenses", action: #selector(showLicense)))
#if STEAMVR_PREVIEW
        content.addArrangedSubview(label(L.text("steamHelp"), size: 12))
#else
        content.addArrangedSubview(label(L.text("help"), size: 12))
#endif
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
        field.heightAnchor.constraint(equalToConstant: 38).isActive = true
        if key != "code" { field.addTarget(self, action: #selector(addressEdited), for: [.editingChanged, .editingDidEnd]) }
        return field
    }
    private func argument(_ name: String) -> String? {
        guard launchOverridesActive else { return nil }
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
        sliders.append(slider); content.addArrangedSubview(slider.label); content.addArrangedSubview(slider.row)
    }
    private func refreshControls() {
        modes.selectedSegmentIndex = settings.mode == "cinema" ? 1 : settings.mode == "fps" ? 2 : settings.mode == "fps_enhanced" ? 3 : 0
        modes.setEnabled(motion.available || sourceIsStereo, forSegmentAt: 1); modes.setEnabled(motion.available || sourceIsStereo, forSegmentAt: 2)
        for slider in sliders { slider.refresh(settings) }
        invert.isOn = settings.invertY
        updateStabilizationNotice()
    }
    private func updateStabilizationNotice() {
        let unsupported = client.state == .connected && !client.supportsStabilization
        stabilizationNotice.text = L.text(unsupported ? "stabilizationUnsupported" : "stabilizationHelp")
        enhancedNotice.isHidden = settings.mode != "fps_enhanced"
        let legacy = client.state == .connected && !client.supportsEnhancedFirstPerson
        enhancedNotice.text = L.text(legacy ? "enhancedLegacyHost" : "enhancedHelp")
        sensorNotice.isHidden = motion.available
#if STEAMVR_PREVIEW
        sensorNotice.text = L.text(sourceIsStereo ? "steamNoTracking" : "noSensor")
        if sourceIsStereo { enhancedNotice.text = L.text("steamProjectionHelp") }
        if client.streamSession?.virtualHMD == true { stabilizationNotice.text = L.text("steamHMDSettings") }
        steamNotice.text = L.text(sourceIsStereo ? (client.streamSession?.virtualHMD == true ? "steamHMD" : "steamSBS") : "steamDirect")
        if let descriptor = client.streamSession {
            steamNotice.accessibilityValue = "epoch=\(descriptor.epoch);accepted=\(descriptor.accepted);layout=\(descriptor.streamLayout.rawValue);target=\(descriptor.inputTarget.rawValue)"
        } else { steamNotice.accessibilityValue = "unnegotiated" }
#endif
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
    private func saveSettings() {
        client.setSettingsBase(settings)
        preferences.hasCommittedProfile = true
        preferences.settings = settings
        try? preferenceStore.save(preferences)
    }
    @objc private func addressEdited() {
        preferences.host = hostField.text ?? ""; preferences.port = portField.text ?? ""
        try? preferenceStore.save(preferences)
    }
    private func sendSettingsSnapshot() {
        if let sequence = try? sync.nextSequence(), client.sendSettings(settings, sequence: sequence) {
            try? sync.sent(sequence: sequence, snapshot: settings)
        }
    }
    private func changed(sendNow: Bool) {
        guard editor == nil, (try? settings.validated()) != nil else { return }
        sync.edited(); renderer?.setSettings(settings); saveSettings()
        let now = ProcessInfo.processInfo.systemUptime
        if sendNow || now - lastSent >= 0.08 {
            lastSent = now
            sendSettingsSnapshot()
        }
    }
    @objc private func languageChanged(_ picker: UISegmentedControl) {
        let language = picker.selectedSegmentIndex == 1 ? "zh-Hans" : "en"
        guard language != L.language else { return }
        closeEditor(save: false, resumeMotion: false)
        client.disconnect(notify: false); motion.stop(); renderer?.clear()
        preferences.language = language; try? preferenceStore.save(preferences)
        statusKey = "disconnected"; buildControls()
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
        preferences.host = host; preferences.port = port; try? preferenceStore.save(preferences)
        recenter()
        if !client.connect(host: host, port: number, code: code) { statusKey = "invalidAddress"; updateStatus() }
    }
    @objc private func transportChanged(_ picker: UISegmentedControl) {
        closeEditor(save: false, resumeMotion: false)
        client.disconnect(notify: false); motion.stop(); renderer?.clear()
        preferences.transport = picker.selectedSegmentIndex == 0 ? "usb" : "lan"; try? preferenceStore.save(preferences)
        statusKey = "disconnected"; buildControls()
    }
    @objc private func modeChanged() {
        settings.mode = ["full", "cinema", "fps", "fps_enhanced"][modes.selectedSegmentIndex]
        if !motion.available && settings.requiresMotion && !sourceIsStereo { settings.mode = "full"; modes.selectedSegmentIndex = 0 }
        recenter(); changed(sendNow: true); updateTracking(); updateStabilizationNotice()
    }
    @objc private func invertChanged() { settings.invertY = invert.isOn; changed(sendNow: true) }
    @objc private func resetSettings() {
        closeEditor(save: false, resumeMotion: false)
        client.disconnect(notify: false); motion.stop(); renderer?.clear()
        sync = LocalProfileSync(); launchOverridesActive = false
        try? preferenceStore.reset(); preferences = preferenceStore.load(); settings = preferences.settings
        client.setSettingsBase(settings)
        codeField.text = ""; statusKey = "disconnected"
        motion.recenter(); renderer?.setPose(Pose()); renderer?.setSettings(settings)
        overlay.isHidden = false; buildControls()
    }
    @objc private func recenter() {
        guard editor == nil else { return }
        motion.recenter(); renderer?.setPose(Pose()); client.resumePose(); updateTracking()
    }
    @objc private func openEditor() {
        guard editor == nil else { return }
        view.endEditing(true); motion.stop(); client.pauseForEditor(); renderer?.setPose(Pose())
        editorEntry = settings; sync.beginPreview()
        let editing = HeadsetEditorView(entry: settings, imageAspect: { [weak self] in
            guard let self = self, self.frameWidth > 0, self.frameHeight > 0 else { return 16.0 / 9 }
            return Double(self.frameWidth) / Double(self.frameHeight) / (self.sourceIsStereo ? 2 : 1)
        }, projectionAlreadyApplied: sourceIsStereo)
        editing.translatesAutoresizingMaskIntoConstraints = false
        editor = editing; overlay.isHidden = true; view.addSubview(editing)
        NSLayoutConstraint.activate([
            editing.leadingAnchor.constraint(equalTo: view.leadingAnchor), editing.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            editing.topAnchor.constraint(equalTo: view.topAnchor), editing.bottomAnchor.constraint(equalTo: view.bottomAnchor)
        ])
        editing.onDraft = { [weak self] draft in self?.preview(draft) }
        editing.onSave = { [weak self] _ in self?.closeEditor(save: true) }
        editing.onDiscard = { [weak self] in self?.closeEditor(save: false) }
        preview(settings)
    }
    private func preview(_ draft: VRSettings) {
        var flat = draft
        if !sourceIsStereo && flat.mode != "fps_enhanced" { flat.mode = "full"; flat.distortion = 0 }
        renderer?.setSettings(flat); renderer?.setPose(Pose())
    }
    private func closeEditor(save: Bool, resumeMotion: Bool = true) {
        guard let editing = editor, let entry = editorEntry else { return }
        let result = save ? editing.draft : entry
        editing.removeFromSuperview(); editor = nil; editorEntry = nil; sync.endPreview()
        settings = result; renderer?.setSettings(settings); renderer?.setPose(Pose())
        overlay.isHidden = false; refreshControls()
        if save { changed(sendNow: true) }
        motion.recenter()
        if resumeMotion {
            // Rebase the host before any new FPS origin sample can be sent.
            client.resumePose(); updateTracking()
        }
    }
    @objc private func hideSettings() { view.endEditing(true); overlay.isHidden = true }
    @objc private func showSettings(_ gesture: UILongPressGestureRecognizer) { if gesture.state == .began { overlay.isHidden = false } }
    func suspendSession() {
        active = false; closeEditor(save: false, resumeMotion: false)
        usbControl.stop()
        motion.stop(); client.disconnect(reason: "paused"); renderer?.clear(); metalView.isPaused = true
        UIApplication.shared.isIdleTimerDisabled = false
    }
    func resumeDisplay() {
        active = true; metalView.isPaused = false; UIApplication.shared.isIdleTimerDisabled = true; updateTracking()
        startUSBControl()
    }
    private func startUSBControl() {
        guard active else { return }
        do { try usbControl.start() } catch { usbControl.onFailure?() }
    }
    private func updateTracking() {
        var needsMotion = settings.mode != "full"
#if STEAMVR_PREVIEW
        if client.streamSession?.virtualHMD == true { needsMotion = true }
#endif
        if active && editor == nil && client.state == .connected && needsMotion && motion.available { motion.start() }
        else { motion.stop() }
#if STEAMVR_PREVIEW
        if active && editor == nil && client.state == .connected && !motion.available && client.streamSession?.virtualHMD == true {
            client.invalidateTracking()
        }
#endif
    }
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated); UIApplication.shared.isIdleTimerDisabled = true
        // Only control listens automatically. Video starts after an explicit
        // phone action or one PC control request, never by enumeration alone.
        startUSBControl()
    }
    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews(); updateTestingGeometry()
    }
    func scrollViewDidScroll(_ scrollView: UIScrollView) { updateTestingGeometry() }
    private func updateTestingGeometry() {
        guard ProcessInfo.processInfo.arguments.contains("--ui-testing"), let scroll = scroll, let window = view.window else { return }
        sliders.forEach { $0.recordTestingGeometry() }
        // Record actual UIKit geometry, independent of XCTest's screen rotation
        // and accessibility conversion. No address or pairing data is included.
        metalView.accessibilityValue = [
            "sceneOrientation=\(window.windowScene?.interfaceOrientation.rawValue ?? 0)",
            "deviceOrientation=\(UIDevice.current.orientation.rawValue)",
            "windowBounds=\(window.bounds)", "windowFrame=\(window.frame)", "viewBounds=\(view.bounds)",
            "scrollFrame=\(scroll.convert(scroll.bounds, to: view))", "contentSize=\(scroll.contentSize)",
            "contentOffset=\(scroll.contentOffset)", "drawableSize=\(metalView.drawableSize)",
            "texture=\(renderer?.diagnostic ?? "unavailable")"
        ].joined(separator: "; ")
    }
    override func viewWillTransition(to size: CGSize, with coordinator: UIViewControllerTransitionCoordinator) {
        super.viewWillTransition(to: size, with: coordinator)
        closeEditor(save: false, resumeMotion: false)
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
    let row = UIStackView()
    private let decrease = UIButton(type: .system), increase = UIButton(type: .system)
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
        row.axis = .horizontal; row.alignment = .center; row.spacing = 8
        row.addArrangedSubview(control)
        for (button, title, suffix, labelKey, action) in [
            (decrease, "−", "decrease", "decreaseStep", #selector(decrement)),
            (increase, "+", "increase", "increaseStep", #selector(increment))
        ] {
            button.setTitle(title, for: .normal)
            button.titleLabel?.font = .systemFont(ofSize: 23, weight: .medium)
            button.backgroundColor = UIColor(white: 0.22, alpha: 1); button.layer.cornerRadius = 6
            button.accessibilityIdentifier = "setting.\(key).\(suffix)"
            button.accessibilityLabel = String(format: L.text(labelKey), L.text(key))
            button.widthAnchor.constraint(equalToConstant: 44).isActive = true
            button.heightAnchor.constraint(equalToConstant: 44).isActive = true
            button.addTarget(self, action: action, for: .touchUpInside)
            row.addArrangedSubview(button)
        }
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
        let precision = ["offsetX", "offsetY", "eyeSeparation", "distortion"].contains(key) ? "%.3f" : "%.2f"
        let formatted = ["scale", "stabilization"].contains(key) ? String(format: "%.0f%%", value * 100) : String(format: precision, value)
        // Keep UIKit's slider accessibility value tied to its native thumb
        // position. The adjacent accessible label announces the actual value.
        label.text = L.text(key) + "  " + formatted
        decrease.isEnabled = value > lower; increase.isEnabled = value < upper
        recordTestingGeometry()
    }
    private func nudge(_ direction: Int) {
        // Precision is part of the normal UI, using the same discrete steps
        // and final settings-send path as a released slider gesture.
        let step = min(steps, max(0, Int(control.value.rounded()) + direction))
        control.value = Float(step)
        let next = value; show(next); change?(next, true)
    }
    @objc private func decrement() { nudge(-1) }
    @objc private func increment() { nudge(1) }
    func recordTestingGeometry() {
        guard ProcessInfo.processInfo.arguments.contains("--ui-testing"),
              let window = control.window, control.bounds.width > 0, control.bounds.height > 0 else { return }
        // Read native thumb geometry for real XCTest touches. This diagnostics
        // path never changes the slider, settings or connection state.
        let track = control.trackRect(forBounds: control.bounds)
        func rect(_ value: CGRect) -> [String: Double] {
            return ["x": Double(value.minX), "y": Double(value.minY),
                    "width": Double(value.width), "height": Double(value.height)]
        }
        func thumb(_ value: Float) -> [String: Double] {
            return rect(control.convert(control.thumbRect(forBounds: control.bounds, trackRect: track, value: value), to: window))
        }
        let geometry: [String: Any] = [
            "frame": rect(control.convert(control.bounds, to: window)),
            "track": rect(control.convert(track, to: window)),
            "current": thumb(control.value), "minimum": thumb(control.minimumValue), "maximum": thumb(control.maximumValue),
            "nativeValue": Double(control.value), "minimumValue": Double(control.minimumValue), "maximumValue": Double(control.maximumValue)
        ]
        if let data = try? JSONSerialization.data(withJSONObject: geometry, options: [.sortedKeys]),
           let text = String(data: data, encoding: .utf8) { label.accessibilityValue = text }
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
