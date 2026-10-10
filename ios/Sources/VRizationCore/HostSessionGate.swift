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
    public private(set) var supportsStabilization = false
    public private(set) var supportsEnhancedFirstPerson = false
    private var enhancedNegotiated = false
    private var awaitingEnhancedSnapshot = false
    /// A capable host may send legacy settings before the USB client opts in.
    /// That hello validates the transport, but must not become a new profile.
    public private(set) var awaitingSettingsSnapshot = false
    public static let maximumJPEGBytes = 8 * 1024 * 1024
    public var isEstablished: Bool { phase == .established }

    public init() {}
    public mutating func reset() {
        phase = .waiting; supportsStabilization = false; supportsEnhancedFirstPerson = false; awaitingSettingsSnapshot = false
        enhancedNegotiated = false; awaitingEnhancedSnapshot = false
    }

    public mutating func receiveText(_ data: Data, settingsBase: VRSettings = .defaults) throws -> Event {
        do {
            guard phase != .failed else { throw VRCoreError.invalid("Session already failed") }
            let message = try VRProtocol.decodeHostMessage(data, settingsBase: settingsBase,
                supportsEnhancedFirstPerson: supportsEnhancedFirstPerson)
            switch (phase, message) {
            case (.waiting, .hello(let hello)):
                phase = .established
                supportsStabilization = hello.supportsStabilization
                supportsEnhancedFirstPerson = hello.supportsEnhancedFirstPerson
                enhancedNegotiated = hello.enhancedFirstPerson
                awaitingEnhancedSnapshot = hello.supportsEnhancedFirstPerson && !hello.enhancedFirstPerson
                // USB initially uses the legacy fps mode before client opt-in.
                // Adopt only the post-negotiation complete authoritative profile.
                awaitingSettingsSnapshot = (hello.supportsStabilization && !hello.includesStabilization)
                    || awaitingEnhancedSnapshot
                return .established(hello)
            case (.established, .hello):
                throw VRCoreError.invalid("Repeated host handshake")
            case (.established, _):
                if case .settings(let update) = message {
                    if update.enhancedFirstPerson == true { enhancedNegotiated = true }
                    guard !update.includesEnhancedMode || enhancedNegotiated else {
                        throw VRCoreError.invalid("Enhanced settings arrived before opt-in snapshot")
                    }
                    if update.includesStabilization { supportsStabilization = true }
                    if update.isComplete && update.clientSeq == nil,
                       !awaitingEnhancedSnapshot || update.enhancedFirstPerson == true {
                        awaitingSettingsSnapshot = false; awaitingEnhancedSnapshot = false
                    }
                }
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
