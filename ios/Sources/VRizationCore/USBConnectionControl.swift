import Foundation

/// Separate from the video protocol: a paired PC can request a foreground USB listener.
public enum USBConnectionControl {
    public enum Action: String { case connect, stop }
    public static let port: UInt16 = 18767
    public static func connectMessage() -> Data { Data("{\"v\":1,\"type\":\"connect\"}".utf8) }
    public static func stopMessage() -> Data { Data("{\"v\":1,\"type\":\"stop\"}".utf8) }
    public static func stoppedMessage() -> Data { Data("{\"v\":1,\"type\":\"stopped\"}".utf8) }
    public static func action(_ frame: USBFrame) throws -> Action {
        guard frame.kind == .json, frame.payload.count <= VRProtocol.maximumTextBytes,
              let object = try JSONSerialization.jsonObject(with: frame.payload) as? [String: Any],
              Set(object.keys) == ["v", "type"],
              try WireValue.integer(object["v"], name: "v") == 1,
              let kind = object["type"] as? String, let action = Action(rawValue: kind) else {
            throw VRCoreError.invalid("Expected USB connection control")
        }
        return action
    }
    public static func validateConnect(_ frame: USBFrame) throws {
        guard try action(frame) == .connect else { throw VRCoreError.invalid("Expected USB video readiness") }
    }
}
