import Foundation
import CoreFoundation
import VRizationCore

public enum SteamVRSessionError: Error, Equatable {
    case invalid(String)
    case changed
}

public enum StreamLayout: String { case mono, sbs }
public enum InputTarget: String { case mouse, virtualHMD = "virtual-hmd" }

/// Transient session metadata. This is deliberately absent from persisted VRSettings.
public struct StreamSession: Equatable {
    public let epoch: Int64
    public let accepted: Bool
    public let streamLayout: StreamLayout
    public let inputTarget: InputTarget
    public init(epoch: Int64, accepted: Bool, streamLayout: StreamLayout, inputTarget: InputTarget) {
        self.epoch = epoch; self.accepted = accepted; self.streamLayout = streamLayout; self.inputTarget = inputTarget
    }
    public static let legacy = StreamSession(epoch: 0, accepted: true, streamLayout: .mono, inputTarget: .mouse)
    public var virtualHMD: Bool { accepted && inputTarget == .virtualHMD }
    public var stereo: Bool { accepted && streamLayout == .sbs }

    public static func decode(_ raw: Any, capabilities: Set<String>) throws -> StreamSession {
        guard let object = raw as? [String: Any],
              Set(object.keys) == ["v", "epoch", "accepted", "streamLayout", "inputTarget"],
              try StrictValue.integer(object["v"]) == 1,
              let layoutString = object["streamLayout"] as? String, let layout = StreamLayout(rawValue: layoutString),
              let targetString = object["inputTarget"] as? String, let target = InputTarget(rawValue: targetString) else {
            throw SteamVRSessionError.invalid("Invalid streamSession descriptor")
        }
        let epoch = try StrictValue.integer(object["epoch"])
        guard (1...VRProtocol.maximumSequence).contains(epoch) else { throw SteamVRSessionError.invalid("Invalid stream epoch") }
        let accepted = try StrictValue.boolean(object["accepted"])
        guard layout != .sbs || capabilities.contains("stereo-sbs"),
              target != .virtualHMD || capabilities.contains("hmd-orientation"),
              target != .virtualHMD || layout == .sbs else {
            throw SteamVRSessionError.invalid("Stream route requires negotiated capabilities")
        }
        return StreamSession(epoch: epoch, accepted: accepted, streamLayout: layout, inputTarget: target)
    }
}

internal enum StrictValue {
    static func integer(_ raw: Any?) throws -> Int64 {
        guard let value = raw as? NSNumber, CFGetTypeID(value) != CFBooleanGetTypeID(),
              value.doubleValue.isFinite, value.doubleValue.rounded() == value.doubleValue,
              abs(value.doubleValue) <= Double(VRProtocol.maximumSequence) else {
            throw SteamVRSessionError.invalid("Expected exact safe integer")
        }
        return value.int64Value
    }
    static func boolean(_ raw: Any?) throws -> Bool {
        guard let value = raw as? NSNumber, CFGetTypeID(value) == CFBooleanGetTypeID() else {
            throw SteamVRSessionError.invalid("Expected strict boolean")
        }
        return value.boolValue
    }
}

/// Extends the stable handshake validator without changing its legacy semantics.
/// A capable host's initial hello cannot attach a layout to unlabelled JPEGs:
/// acceptance requires its complete post-client-hello authoritative snapshot.
public struct SteamVRSessionGate {
    private var stable = HostSessionGate()
    private var capabilities = Set<String>()
    private var failed = false
    private var awaitingStreamSnapshot = false
    private var proposed: StreamSession?
    public private(set) var descriptor: StreamSession?
    public var supportsStabilization: Bool { stable.supportsStabilization }
    public var supportsEnhancedFirstPerson: Bool { stable.supportsEnhancedFirstPerson }
    public var isEstablished: Bool { stable.isEstablished && !failed }
    public var awaitingSettingsSnapshot: Bool { stable.awaitingSettingsSnapshot || awaitingStreamSnapshot }
    public var canReceiveFrames: Bool { isEstablished && !awaitingSettingsSnapshot && descriptor?.accepted == true }
    public var acceptsHMDPose: Bool { canReceiveFrames && descriptor?.virtualHMD == true && capabilities.contains("hmd-orientation") }
    public init() {}
    public mutating func reset() { self = SteamVRSessionGate() }

    public mutating func receiveText(_ data: Data, settingsBase: VRSettings = .defaults) throws -> HostSessionGate.Event {
        do {
            guard !failed, data.count <= VRProtocol.maximumTextBytes,
                  let object = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let kind = object["type"] as? String else { throw SteamVRSessionError.invalid("Invalid host message") }
            let wasEstablished = stable.isEstablished
            if kind == "hello" && !wasEstablished {
                if let raw = object["capabilities"] {
                    guard let strings = raw as? [String] else { throw SteamVRSessionError.invalid("Invalid capabilities") }
                    capabilities = Set(strings)
                }
                let capable = capabilities.contains("stereo-sbs") || capabilities.contains("hmd-orientation")
                if let raw = object["streamSession"] {
                    proposed = try StreamSession.decode(raw, capabilities: capabilities)
                    guard capable else { throw SteamVRSessionError.invalid("Descriptor without stream capability") }
                } else if capable { throw SteamVRSessionError.invalid("Capable hello is missing streamSession") }
                awaitingStreamSnapshot = capable
                descriptor = capable ? nil : .legacy
            }
            let event = try stable.receiveText(data, settingsBase: settingsBase)
            if kind == "settings" && wasEstablished {
                let capable = capabilities.contains("stereo-sbs") || capabilities.contains("hmd-orientation")
                if capable {
                    guard let raw = object["streamSession"] else { throw SteamVRSessionError.invalid("Capable settings missing streamSession") }
                    let next = try StreamSession.decode(raw, capabilities: capabilities)
                    if let accepted = descriptor, accepted != next { throw SteamVRSessionError.changed }
                    if let previous = proposed {
                        guard previous.epoch == next.epoch, previous.streamLayout == next.streamLayout,
                              previous.inputTarget == next.inputTarget,
                              !previous.accepted || next.accepted else { throw SteamVRSessionError.changed }
                    }
                    if case .message(.settings(let update)) = event,
                       update.isComplete && update.clientSeq == nil && !stable.awaitingSettingsSnapshot {
                        descriptor = next.accepted ? next : nil
                        awaitingStreamSnapshot = !next.accepted
                    }
                } else if object["streamSession"] != nil {
                    throw SteamVRSessionError.invalid("Legacy host cannot change stream route")
                }
            }
            return event
        } catch {
            failed = true; descriptor = nil
            throw error
        }
    }
    public mutating func receiveJPEG(byteCount: Int) throws {
        guard !failed else { throw SteamVRSessionError.invalid("Session failed") }
        try stable.receiveJPEG(byteCount: byteCount)
    }
    /// Late decoded callbacks are bound to both transport generation and layout epoch.
    public func acceptsFrame(generation: UInt64, activeGeneration: UInt64, captured: StreamSession?) -> Bool {
        canReceiveFrames && generation == activeGeneration && captured == descriptor
    }
}
