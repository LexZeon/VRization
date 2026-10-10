import Foundation
import VRizationCore

public enum SteamVRProtocol {
    public static let capabilities = ["enhanced-first-person", "stereo-sbs", "hmd-orientation"]
    public static func hello(editing: Bool = false) -> Data {
        var object: [String: Any] = ["v": 1, "type": "hello", "settingsSchema": 2, "capabilities": capabilities]
        if editing { object["editing"] = true }
        return try! JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
    }
    public static func recenter(epoch: Int64) throws -> Data {
        guard (1...VRProtocol.maximumSequence).contains(epoch) else { throw SteamVRSessionError.invalid("Invalid recenter epoch") }
        return try JSONSerialization.data(withJSONObject: ["v": 1, "type": "recenter", "epoch": epoch], options: [.sortedKeys])
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
