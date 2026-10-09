import Foundation
import Network
import VRizationCore

/// usbmuxd opens a TCP connection to the device loopback endpoint. Never listens on Wi-Fi.
/// Its owner starts/stops this listener on the main queue and authorizes one peer at a time.
final class USBListener {
    var onFrame: ((USBFrame) -> Void)?
    var onFailure: (() -> Void)?
    var onHandshakeTimeout: (() -> Void)?
    private var listener: NWListener?
    private var connection: NWConnection?
    private var generation: UInt64 = 0
    private var handshakeTimeout: Timer?

    func start() throws {
        stop()
        let epoch = generation
        let parameters = NWParameters.tcp
        parameters.allowLocalEndpointReuse = true
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: 18766)
        let listener = try NWListener(using: parameters)
        self.listener = listener
        listener.stateUpdateHandler = { [weak self] state in
            guard let self = self, self.generation == epoch else { return }
            if case .failed = state { self.onFailure?() }
        }
        listener.newConnectionHandler = { [weak self] incoming in
            guard let self = self, self.generation == epoch, self.connection == nil else { incoming.cancel(); return }
            self.connection = incoming
            incoming.stateUpdateHandler = { [weak self, weak incoming] state in
                guard let self = self, let incoming = incoming, self.connection === incoming, self.generation == epoch else { return }
                switch state {
                case .ready: self.header(incoming, epoch: epoch)
                case .failed: self.onFailure?()
                default: break
                }
            }
            let timer = Timer(timeInterval: 10, repeats: false) { [weak self, weak incoming] _ in
                guard let self = self, let incoming = incoming, self.matches(incoming, epoch) else { return }
                self.onHandshakeTimeout?()
            }
            self.handshakeTimeout = timer; RunLoop.main.add(timer, forMode: .common)
            incoming.start(queue: .main)
        }
        listener.start(queue: .main)
    }
    func acknowledgedHost() { handshakeTimeout?.invalidate(); handshakeTimeout = nil }
    func stop() {
        generation &+= 1
        handshakeTimeout?.invalidate(); handshakeTimeout = nil
        connection?.cancel(); connection = nil
        listener?.cancel(); listener = nil
    }
    func send(_ data: Data, completion: @escaping (Bool) -> Void) {
        guard let connection = connection,
              let framed = try? USBFraming.encode(USBFrame(kind: .json, payload: data)) else { completion(false); return }
        let epoch = generation
        connection.send(content: framed, completion: .contentProcessed { [weak self, weak connection] error in
            guard let self = self, let connection = connection, self.generation == epoch, self.connection === connection else { return }
            completion(error == nil)
        })
    }
    private func matches(_ connection: NWConnection, _ epoch: UInt64) -> Bool { self.connection === connection && generation == epoch }
    private func header(_ connection: NWConnection, epoch: UInt64) {
        connection.receive(minimumIncompleteLength: 4, maximumLength: 4) { [weak self, weak connection] data, _, _, error in
            guard let self = self, let connection = connection, self.matches(connection, epoch) else { return }
            guard error == nil, let data = data, let length = try? USBFraming.length(fromHeader: data) else { self.onFailure?(); return }
            self.body(connection, length: length, epoch: epoch)
        }
    }
    private func body(_ connection: NWConnection, length: Int, epoch: UInt64) {
        connection.receive(minimumIncompleteLength: length, maximumLength: length) { [weak self, weak connection] data, _, _, error in
            guard let self = self, let connection = connection, self.matches(connection, epoch) else { return }
            guard error == nil, let data = data, data.count == length, let frame = try? USBFraming.decode(body: data) else { self.onFailure?(); return }
            self.onFrame?(frame)
            if self.matches(connection, epoch) { self.header(connection, epoch: epoch) }
        }
    }
    deinit { stop() }
}
