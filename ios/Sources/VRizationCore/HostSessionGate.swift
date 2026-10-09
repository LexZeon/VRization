import Foundation

/// Application-protocol validation shared by WebSocket and framed USB transports.
/// A transport opening is not a session: exactly one valid host hello must arrive first.
/// Protocol failures poison this gate until the owner starts a new connection.
public struct HostSessionGate {
    public enum Event: Equatable {
        case established(HostHello)
        case message(HostMessage)
    }
    private enum Phase: Equatable { case waiting, established, failed }
    private var phase: Phase = .waiting
    public static let maximumJPEGBytes = 8 * 1024 * 1024
    public var isEstablished: Bool { phase == .established }

    public init() {}
    public mutating func reset() { phase = .waiting }

    public mutating func receiveText(_ data: Data) throws -> Event {
        do {
            guard phase != .failed else { throw VRCoreError.invalid("Session already failed") }
            let message = try VRProtocol.decodeHostMessage(data)
            switch (phase, message) {
            case (.waiting, .hello(let hello)):
                phase = .established
                return .established(hello)
            case (.established, .hello):
                throw VRCoreError.invalid("Repeated host handshake")
            case (.established, _):
                return .message(message)
            default:
                throw VRCoreError.invalid("Expected host handshake before messages")
            }
        } catch {
            phase = .failed
            throw error
        }
    }

    /// Validate before passing bytes to any image decoder, including pre-hello traffic.
    public mutating func receiveJPEG(byteCount: Int) throws {
        guard phase == .established, (4...Self.maximumJPEGBytes).contains(byteCount) else {
            phase = .failed
            throw VRCoreError.invalid("Unexpected or oversized video frame")
        }
    }
}
