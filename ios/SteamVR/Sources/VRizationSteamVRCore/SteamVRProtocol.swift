import Foundation
import VRizationCore

public enum SteamVRProtocol {
    public static let capabilities = ["enhanced-first-person", "stereo-sbs", "hmd-orientation", "video-refresh"]
    public static func hello(editing: Bool = false) -> Data {
        var object: [String: Any] = ["v": 1, "type": "hello", "settingsSchema": 2, "capabilities": capabilities]
        if editing { object["editing"] = true }
        return try! JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
    }
    public static func recenter(epoch: Int64) throws -> Data {
        guard (1...VRProtocol.maximumSequence).contains(epoch) else { throw SteamVRSessionError.invalid("Invalid recenter epoch") }
        return try JSONSerialization.data(withJSONObject: ["v": 1, "type": "recenter", "epoch": epoch], options: [.sortedKeys])
    }
    public static func refreshVideo(session: StreamSession, requestId: Int64) throws -> Data {
        guard session.virtualHMD, session.stereo, (1...VRProtocol.maximumSequence).contains(session.epoch),
              (1...VRProtocol.maximumSequence).contains(requestId) else {
            throw SteamVRSessionError.invalid("Video refresh requires accepted virtual HMD and safe counters")
        }
        return try JSONSerialization.data(withJSONObject: ["v": 1, "type": "refreshVideo",
            "epoch": session.epoch, "requestId": requestId], options: [.sortedKeys])
    }
    public static func hmdPose(session: StreamSession, sequence: Int64, timeUs: Int64,
                               quaternion: HMDQuaternion?) throws -> Data {
        guard session.virtualHMD, session.stereo, (1...VRProtocol.maximumSequence).contains(session.epoch),
              (1...VRProtocol.maximumSequence).contains(sequence), (0...VRProtocol.maximumSequence).contains(timeUs) else {
            throw SteamVRSessionError.invalid("HMD pose requires accepted virtual-HMD session and safe counters")
        }
        var object: [String: Any] = ["v": 1, "type": "hmdPose", "epoch": session.epoch,
                                  "seq": sequence, "timeUs": timeUs, "trackingValid": quaternion != nil]
        if let q = quaternion { object["q"] = try q.validated().xyzw }
        return try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
    }
}

/// Video has an independent generation: rebuilding it must never reset HMD
/// orientation, its sequence, the accepted session, or the local input pause.
public struct VideoRefreshGate {
    public struct Request: Equatable {
        public let epoch: Int64, requestId: Int64
        public let transportGeneration: UInt64
        public let deadline: Double
    }
    public static let timeout: Double = 8
    public private(set) var frameGeneration: UInt64 = 0
    public private(set) var lastRequestId: Int64 = 0
    public private(set) var pending: Request?
    public init() {}
    public var acceptsFrames: Bool { pending == nil }
    public mutating func cancel() { pending = nil; frameGeneration &+= 1 }
    public mutating func begin(session: StreamSession, supported: Bool, transportGeneration: UInt64, now: Double) throws -> Data {
        guard supported, pending == nil, now.isFinite, now >= 0,
              lastRequestId < VRProtocol.maximumSequence else {
            throw SteamVRSessionError.invalid("Video refresh unavailable or already pending")
        }
        let requestId = lastRequestId + 1
        let data = try SteamVRProtocol.refreshVideo(session: session, requestId: requestId)
        lastRequestId = requestId; frameGeneration &+= 1
        pending = Request(epoch: session.epoch, requestId: requestId,
                          transportGeneration: transportGeneration, deadline: now + Self.timeout)
        return data
    }
    public func expired(now: Double, transportGeneration: UInt64) -> Bool {
        guard let request = pending, now.isFinite, request.transportGeneration == transportGeneration else { return false }
        return now >= request.deadline
    }
    /// The paused value is a status hint only. It never grants Resume.
    /// Well-formed late ACKs cannot open a newer request or transport.
    public mutating func acknowledge(_ data: Data, session: StreamSession?, supported: Bool,
                                     transportGeneration: UInt64, now: Double) throws -> Bool? {
        guard supported, let session = session, session.virtualHMD, session.stereo,
              now.isFinite, now >= 0,
              data.count <= VRProtocol.maximumTextBytes,
              let object = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              try StrictValue.integer(object["v"]) == 1, object["type"] as? String == "videoRefresh" else {
            throw SteamVRSessionError.invalid("Invalid video refresh acknowledgement")
        }
        let epoch = try StrictValue.integer(object["epoch"]), requestId = try StrictValue.integer(object["requestId"])
        let paused = try StrictValue.boolean(object["paused"])
        guard (1...VRProtocol.maximumSequence).contains(epoch), (1...VRProtocol.maximumSequence).contains(requestId) else {
            throw SteamVRSessionError.invalid("Invalid video refresh acknowledgement counters")
        }
        guard let request = pending, request.epoch == epoch, session.epoch == epoch,
              request.requestId == requestId, request.transportGeneration == transportGeneration,
              now < request.deadline else { return nil }
        pending = nil
        return paused
    }
    public func acceptsFrame(_ captured: UInt64) -> Bool { acceptsFrames && captured == frameGeneration }
}

/// Recenter controls do not reset the monotonic pose sequence; skipped queued
/// samples may leave gaps but can never reuse an earlier accepted sequence.
public struct HMDPoseSequencer {
    public private(set) var lastSequence: Int64 = 0
    public init() {}
    public mutating func encode(session: StreamSession, timeUs: Int64, quaternion: HMDQuaternion?) throws -> Data {
        guard lastSequence < VRProtocol.maximumSequence else { throw SteamVRSessionError.invalid("Pose sequence exhausted") }
        let next = lastSequence + 1
        let data = try SteamVRProtocol.hmdPose(session: session, sequence: next, timeUs: timeUs, quaternion: quaternion)
        lastSequence = next
        return data
    }
    public func recenter(session: StreamSession) throws -> Data {
        guard session.virtualHMD else { throw SteamVRSessionError.invalid("Recenter requires an accepted virtual HMD") }
        return try SteamVRProtocol.recenter(epoch: session.epoch)
    }
}
