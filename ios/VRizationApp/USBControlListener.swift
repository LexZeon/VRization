import Foundation
import Network
import VRizationCore

/// Foreground-only, device-loopback control. Its lifetime is independent of video disconnect.
final class USBControlListener {
    var onConnect: (() -> Void)?
    var onStop: (() -> Void)?
    var onFailure: (() -> Void)?
    private var listener: NWListener?
    private var connection: NWConnection?
    private var timeout: Timer?
    private var generation: UInt64 = 0

    func start() throws {
        precondition(Thread.isMainThread)
        guard listener == nil else { return }
        let epoch = generation
        let parameters = NWParameters.tcp
        parameters.allowLocalEndpointReuse = true
#if STEAMVR_PREVIEW
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: 18777)
#else
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: NWEndpoint.Port(rawValue: USBConnectionControl.port)!)
#endif
        let listener = try NWListener(using: parameters)
        self.listener = listener
        listener.stateUpdateHandler = { [weak self] state in
            guard let self = self, self.generation == epoch else { return }
            if case .failed = state { self.stop(); self.onFailure?() }
        }
        listener.newConnectionHandler = { [weak self] incoming in
            guard let self = self, self.generation == epoch, self.connection == nil else { incoming.cancel(); return }
            self.connection = incoming
            incoming.stateUpdateHandler = { [weak self, weak incoming] state in
                guard let self = self, let incoming = incoming, self.matches(incoming, epoch) else { return }
                switch state {
                case .ready: self.receiveHeader(incoming, epoch: epoch)
                case .failed: self.closePeer()
                default: break
                }
            }
            let timer = Timer(timeInterval: 2, repeats: false) { [weak self, weak incoming] _ in
                guard let self = self, let incoming = incoming, self.matches(incoming, epoch) else { return }
                self.closePeer()
            }
            self.timeout = timer; RunLoop.main.add(timer, forMode: .common)
            incoming.start(queue: .main)
        }
        listener.start(queue: .main)
    }
    private func matches(_ incoming: NWConnection, _ epoch: UInt64) -> Bool {
        generation == epoch && connection === incoming
    }
    private func receiveHeader(_ incoming: NWConnection, epoch: UInt64) {
        incoming.receive(minimumIncompleteLength: 4, maximumLength: 4) { [weak self, weak incoming] data, _, _, error in
            guard let self = self, let incoming = incoming, self.matches(incoming, epoch) else { return }
            guard error == nil, let data = data, let length = try? USBFraming.length(fromHeader: data),
                  length <= VRProtocol.maximumTextBytes + 1 else { self.closePeer(); return }
            incoming.receive(minimumIncompleteLength: length, maximumLength: length) { [weak self, weak incoming] data, _, _, error in
                guard let self = self, let incoming = incoming, self.matches(incoming, epoch) else { return }
                guard error == nil, let data = data, data.count == length,
                      let frame = try? USBFraming.decode(body: data),
                      let action = try? USBConnectionControl.action(frame) else { self.closePeer(); return }
                switch action {
                case .connect:
                    self.closePeer(); self.onConnect?()
                case .stop:
                    guard let stopVideo = self.onStop,
                          let ack = try? USBFraming.encode(USBFrame(kind: .json, payload: USBConnectionControl.stoppedMessage()))
                    else { self.closePeer(); return }
                    // Main-queue callback closes listener/socket, invalidates
                    // decoder generation and clears the displayed texture first.
                    stopVideo()
                    incoming.send(content: ack, completion: .contentProcessed { [weak self, weak incoming] error in
                        guard let self = self, let incoming = incoming, self.matches(incoming, epoch) else { return }
                        guard error == nil else { self.closePeer(); return }
                        // Let the PC receive acknowledgment and close normally;
                        // the existing short peer timeout still bounds resources.
                        incoming.receive(minimumIncompleteLength: 1, maximumLength: 1) { [weak self, weak incoming] _, _, _, _ in
                            guard let self = self, let incoming = incoming, self.matches(incoming, epoch) else { return }
                            self.closePeer()
                        }
                    })
                }
            }
        }
    }
    private func closePeer() {
        timeout?.invalidate(); timeout = nil
        connection?.cancel(); connection = nil
    }
    func stop() {
        generation &+= 1; closePeer(); listener?.cancel(); listener = nil
    }
    deinit { stop() }
}
