import Foundation
import CoreGraphics
import VRizationCore

/// All connection transitions and callbacks belong to the main queue.
/// URLSession callbacks recheck task identity and generation after dispatching there.
final class StreamClient: NSObject, URLSessionWebSocketDelegate {
    enum State: Equatable { case disconnected, connecting, connected }
    enum Transport: String { case usb, lan }
    private(set) var state: State = .disconnected
    private(set) var transport: Transport = .lan
    var onState: ((State, String) -> Void)?
    var onSessionStarted: (() -> Void)?
    var onSettings: ((VRSettings, Int64?, Int64?) -> Void)?
    var onFrame: ((CGImage) -> Void)?
    var onRTT: ((Double?) -> Void)?
    private var session: URLSession?
    private var socket: URLSessionWebSocketTask?
    private let sessions = SessionGeneration()
    private var generation: UInt64 { sessions.current }
    private let decoder = JPEGDecoder()
    private let usb = USBListener()
    private var heartbeat: Timer?
    private var sending = false
    private var pendingHello: Data?
    private var pendingSettings: Data?
    private var pendingPose: Data?
    private var pendingPing = false
    private var pingSentAt: TimeInterval?
    private var pendingRecenter = false
    private var poseSequence: Int64 = 0

    override init() {
        super.init()
        decoder.onImage = { [weak self] image, epoch in
            guard let self = self, epoch == self.generation, self.state == .connected else { return }
            self.onFrame?(image)
        }
        usb.onFrame = { [weak self] frame in
            guard let self = self, self.transport == .usb, self.state != .disconnected else { return }
            if frame.kind == .jpeg {
                if self.state == .connected { self.decoder.submit(frame.payload, generation: self.generation) }
            } else {
                guard let message = try? VRProtocol.decodeHostMessage(frame.payload) else { self.disconnect(reason: "usbFailed"); return }
                if self.state == .connecting {
                    guard case .hello = message else { self.disconnect(reason: "usbFailed"); return }
                    self.usb.acknowledgedHost(); self.beginConnected()
                }
                self.handleMessage(message)
            }
        }
        usb.onFailure = { [weak self] in
            guard let self = self, self.transport == .usb, self.state != .disconnected else { return }
            self.disconnect(reason: "usbFailed")
        }
    }

    func connectUSB() -> Bool {
        precondition(Thread.isMainThread)
        disconnect(notify: false); transport = .usb
        state = .connecting; onState?(state, "usbWaiting")
        do { try usb.start(); return true }
        catch { disconnect(reason: "usbFailed"); return false }
    }

    func connect(host: String, port: Int, code: String) -> Bool {
        precondition(Thread.isMainThread)
        disconnect(notify: false)
        transport = .lan
        guard let url = try? ConnectionInput.url(host: host, port: String(port), token: code) else { return false }
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 15
        config.httpCookieStorage = nil
        config.urlCache = nil
        let session = URLSession(configuration: config, delegate: self, delegateQueue: .main)
        let task = session.webSocketTask(with: url)
        task.maximumMessageSize = 8 * 1024 * 1024
        self.session = session; socket = task
        state = .connecting; onState?(state, "connecting")
        task.resume()
        return true
    }

    func disconnect(notify: Bool = true, reason: String = "disconnected") {
        precondition(Thread.isMainThread)
        sessions.invalidate()
        state = .disconnected
        heartbeat?.invalidate(); heartbeat = nil
        usb.stop()
        socket?.cancel(with: .normalClosure, reason: nil); socket = nil
        session?.invalidateAndCancel(); session = nil
        sending = false; pendingHello = nil; pendingSettings = nil; pendingPose = nil; pendingRecenter = false; pendingPing = false
        pingSentAt = nil; onRTT?(nil)
        decoder.reset(generation: generation)
        if notify { onState?(state, reason) }
    }

    func sendSettings(_ settings: VRSettings, sequence: Int64) -> Bool {
        guard state == .connected, let data = try? VRProtocol.encodeSettings(settings, clientSeq: sequence) else { return false }
        pendingSettings = data; drain()
        return true
    }
    func sendPose(yaw: Double, pitch: Double) {
        guard state == .connected, yaw.isFinite, pitch.isFinite, poseSequence < 9_007_199_254_740_991 else { return }
        poseSequence += 1
        pendingPose = try? VRProtocol.encodePose(sequence: poseSequence, yaw: yaw, pitch: pitch)
        drain()
    }
    func recenter() {
        // A queued old-origin pose must never follow the recenter control message.
        pendingPose = nil
        if state == .connected { pendingRecenter = true; drain() }
    }

    private func drain() {
        guard !sending, state == .connected else { return }
        let data: Data
        if let hello = pendingHello { data = hello; pendingHello = nil }
        else if pendingRecenter { data = VRProtocol.recenter(); pendingRecenter = false }
        else if let settings = pendingSettings { data = settings; pendingSettings = nil }
        else if pendingPing { data = VRProtocol.ping(); pendingPing = false; pingSentAt = ProcessInfo.processInfo.systemUptime }
        else if let pose = pendingPose { data = pose; pendingPose = nil }
        else { return }
        sending = true
        let epoch = generation
        let complete: (Bool) -> Void = { [weak self] ok in
            guard let self = self, self.generation == epoch, self.state == .connected else { return }
            self.sending = false
            if !ok { self.disconnect(reason: "failed") } else { self.drain() }
        }
        if transport == .usb { usb.send(data, completion: complete) }
        else if let task = socket {
            task.send(.string(String(decoding: data, as: UTF8.self))) { error in
                DispatchQueue.main.async { complete(error == nil) }
            }
        } else {
            complete(false)
        }
    }

    private func matches(_ task: URLSessionWebSocketTask, _ epoch: UInt64) -> Bool {
        socket === task && generation == epoch
    }
    private func receive(_ task: URLSessionWebSocketTask, epoch: UInt64) {
        task.receive { [weak self, weak task] result in
            DispatchQueue.main.async {
                guard let self = self, let task = task, self.matches(task, epoch), self.state == .connected else { return }
                switch result {
                case .success(.data(let data)): self.decoder.submit(data, generation: epoch)
                case .success(.string(let text)):
                    if text.utf8.count <= 65536 { self.handle(Data(text.utf8)) }
                case .failure: self.disconnect(reason: "failed"); return
                @unknown default: break
                }
                if self.matches(task, epoch) { self.receive(task, epoch: epoch) }
            }
        }
    }

    private func handle(_ data: Data) {
        guard let message = try? VRProtocol.decodeHostMessage(data) else { return }
        handleMessage(message)
    }
    private func handleMessage(_ message: HostMessage) {
        switch message {
        case .hello(let hello): onSettings?(hello.settings, hello.revision, nil)
        case .settings(let update): onSettings?(update.settings, update.revision, update.clientSeq)
        case .error: onState?(state, "failed")
        case .pong:
            if let sent = pingSentAt { onRTT?((ProcessInfo.processInfo.systemUptime - sent) * 1000); pingSentAt = nil }
        }
    }

    private func beginConnected() {
        state = .connected; onSessionStarted?()
        pendingHello = VRProtocol.hello(); drain(); onState?(state, "connected")
        let epoch = generation
        let timer = Timer(timeInterval: 2, repeats: true) { [weak self] _ in
            guard let self = self, self.generation == epoch, self.state == .connected else { return }
            if let sent = self.pingSentAt {
                if ProcessInfo.processInfo.systemUptime - sent > 10 { self.disconnect(reason: "failed") }
                return
            }
            self.pendingPing = true; self.drain()
        }
        heartbeat = timer; RunLoop.main.add(timer, forMode: .common)
    }

    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol selectedProtocol: String?) {
        DispatchQueue.main.async { [weak self, weak webSocketTask] in
            guard let self = self, let task = webSocketTask, self.socket === task else { return }
            self.beginConnected()
            self.receive(task, epoch: self.generation)
        }
    }
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask,
                    didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        DispatchQueue.main.async { [weak self, weak webSocketTask] in
            guard let self = self, let task = webSocketTask, self.socket === task else { return }
            self.disconnect()
        }
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        guard error != nil else { return }
        DispatchQueue.main.async { [weak self, weak task] in
            guard let self = self, let task = task, self.socket === task else { return }
            let status = (task.response as? HTTPURLResponse)?.statusCode
            self.disconnect(reason: status == 401 ? "pairingError" : status == 409 ? "busyError" : status == 429 ? "rateError" : "failed")
        }
    }
}
