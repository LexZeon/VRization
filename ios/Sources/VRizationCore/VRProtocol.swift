import Foundation

public struct StreamInfo: Equatable {
    public let codec: String
    public let fps: Int64
    public let maxWidth: Int64
}
public struct HostHello: Equatable {
    public let settings: VRSettings
    public let revision: Int64?
    public let stream: StreamInfo
    public let name: String
    public let version: String
    public let mouseArmed: Bool
    public let supportsStabilization: Bool
    public let includesStabilization: Bool
    public let supportsEnhancedFirstPerson: Bool
    public let enhancedFirstPerson: Bool
}
public struct SettingsUpdate: Equatable {
    public let settings: VRSettings
    public let revision: Int64?
    public let clientSeq: Int64?
    public let includesStabilization: Bool
    public let isComplete: Bool
    public let enhancedFirstPerson: Bool?
    public let includesEnhancedMode: Bool
}
public enum HostMessage: Equatable {
    case hello(HostHello)
    case settings(SettingsUpdate)
    case pong
    case error(String)
}

public enum VRProtocol {
    public static let maximumSequence: Int64 = 9_007_199_254_740_991
    public static let maximumTextBytes = 16 * 1024
    public static let settingsSchema = 2

    public static func decodeHostMessage(_ data: Data, settingsBase: VRSettings = .defaults,
                                         supportsEnhancedFirstPerson: Bool = false) throws -> HostMessage {
        guard data.count <= maximumTextBytes,
              let object = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              try WireValue.integer(object["v"], name: "v") == 1,
              let kind = object["type"] as? String else {
            throw VRCoreError.invalid("Expected protocol version 1 message")
        }
        switch kind {
        case "hello":
            guard let stream = object["stream"] as? [String: Any], stream["codec"] as? String == "jpeg",
                  let name = object["name"] as? String, let version = object["version"] as? String,
                  let armed = object["mouseArmed"] else {
                throw VRCoreError.invalid("Unsupported host handshake or codec")
            }
            let fps = try WireValue.integer(stream["fps"], name: "fps")
            let width = try WireValue.integer(stream["maxWidth"], name: "maxWidth")
            guard fps > 0, width > 0 else { throw VRCoreError.invalid("Invalid stream dimensions or frame rate") }
            let settings = try VRSettings.complete(object["settings"])
            var capabilities: [String] = []
            if let raw = object["capabilities"] {
                guard let strings = raw as? [String] else { throw VRCoreError.invalid("Capabilities must be a string array") }
                capabilities = strings
            }
            let hasStabilization = (object["settings"] as? [String: Any])?["stabilization"] != nil
            let hasEnhanced = capabilities.contains("enhanced-first-person")
            let enhancedNegotiated = try object["enhancedFirstPerson"].map { try WireValue.boolean($0, name: "enhancedFirstPerson") } ?? false
            guard !enhancedNegotiated || hasEnhanced,
                  settings.mode != "fps_enhanced" || (hasEnhanced && enhancedNegotiated) else {
                throw VRCoreError.invalid("Enhanced mode requires host capability negotiation")
            }
            return .hello(HostHello(settings: settings,
                                    revision: try WireValue.optionalInteger(object, key: "revision"),
                                    stream: StreamInfo(codec: "jpeg", fps: fps, maxWidth: width),
                                    name: name, version: version,
                                    mouseArmed: try WireValue.boolean(armed, name: "mouseArmed"),
                                    supportsStabilization: hasStabilization || capabilities.contains("stabilization"),
                                    includesStabilization: hasStabilization,
                                    supportsEnhancedFirstPerson: hasEnhanced,
                                    enhancedFirstPerson: enhancedNegotiated))
        case "settings":
            guard let patch = object["settings"] as? [String: Any] else { throw VRCoreError.invalid("Expected settings object") }
            let enhancedNegotiated = try object["enhancedFirstPerson"].map { try WireValue.boolean($0, name: "enhancedFirstPerson") }
            guard enhancedNegotiated != true || supportsEnhancedFirstPerson else {
                throw VRCoreError.invalid("Unexpected enhanced negotiation marker")
            }
            guard patch["mode"] as? String != "fps_enhanced" || supportsEnhancedFirstPerson else {
                throw VRCoreError.invalid("Unnegotiated enhanced settings")
            }
            // Legacy full snapshots and partial ACKs retain local-only values.
            // Applying validates every supplied key/type before accepting it.
            return .settings(SettingsUpdate(settings: try settingsBase.applying(patch),
                                             revision: try WireValue.optionalInteger(object, key: "revision"),
                                             clientSeq: try WireValue.optionalInteger(object, key: "clientSeq"),
                                             includesStabilization: patch["stabilization"] != nil,
                                             isComplete: Set(patch.keys) == VRSettings.names,
                                             enhancedFirstPerson: enhancedNegotiated,
                                             includesEnhancedMode: patch["mode"] as? String == "fps_enhanced"))
        case "pong": return .pong
        case "error":
            guard let message = object["message"] as? String else { throw VRCoreError.invalid("Expected error text") }
            return .error(message)
        default: throw VRCoreError.invalid("Unknown host message")
        }
    }

    public static func encodeSettings(_ settings: VRSettings, clientSeq: Int64? = nil,
                                      supportsStabilization: Bool = true,
                                      supportsEnhancedFirstPerson: Bool = true) throws -> Data {
        let encoded = try JSONEncoder().encode(wireSettings(settings, supportsEnhancedFirstPerson: supportsEnhancedFirstPerson))
        guard var body = try JSONSerialization.jsonObject(with: encoded) as? [String: Any] else {
            throw VRCoreError.invalid("Expected encoded settings object")
        }
        if !supportsStabilization { body.removeValue(forKey: "stabilization") }
        var message: [String: Any] = ["v": 1, "type": "settings", "settings": body]
        if let sequence = clientSeq {
            guard (0...maximumSequence).contains(sequence) else { throw VRCoreError.invalid("Invalid client sequence") }
            message["clientSeq"] = sequence
        }
        return try JSONSerialization.data(withJSONObject: message, options: [.sortedKeys])
    }
    /// Old hosts keep ordinary first-person input while the new viewer retains
    /// its local enhanced display. Never send an unknown mode to a legacy host.
    public static func wireSettings(_ settings: VRSettings, supportsEnhancedFirstPerson: Bool) throws -> VRSettings {
        var value = try settings.validated()
        if !supportsEnhancedFirstPerson && value.mode == "fps_enhanced" { value.mode = "fps" }
        return value
    }
    /// Translate legacy fps echoes to the selected local display before the
    /// revision/sequence gate compares them with the actual saved profile.
    public static func localSettings(_ settings: VRSettings, local: VRSettings,
                                     supportsEnhancedFirstPerson: Bool) throws -> VRSettings {
        var value = try settings.validated()
        _ = try local.validated()
        if !supportsEnhancedFirstPerson && local.mode == "fps_enhanced" && value.mode == "fps" {
            value.mode = "fps_enhanced"
        }
        return value
    }
    public static func encodePose(sequence: Int64, yaw: Double, pitch: Double) throws -> Data {
        guard (0...maximumSequence).contains(sequence), yaw.isFinite, pitch.isFinite,
              abs(yaw) <= 100, abs(pitch) <= 100 else { throw VRCoreError.invalid("Invalid pose") }
        let message: [String: Any] = ["v": 1, "type": "pose", "seq": sequence, "yaw": yaw, "pitch": pitch]
        return try JSONSerialization.data(withJSONObject: message, options: [.sortedKeys])
    }
    public static func hello() -> Data { return Data("{\"v\":1,\"type\":\"hello\",\"settingsSchema\":2,\"capabilities\":[\"enhanced-first-person\"]}".utf8) }
    /// Safety-only request: the host disarms input; it never grants input permission.
    public static func editorHello() -> Data { return Data("{\"v\":1,\"type\":\"hello\",\"editing\":true,\"settingsSchema\":2,\"capabilities\":[\"enhanced-first-person\"]}".utf8) }
    public static func recenter() -> Data { return Data("{\"v\":1,\"type\":\"recenter\"}".utf8) }
    public static func ping() -> Data { return Data("{\"v\":1,\"type\":\"ping\"}".utf8) }
}
