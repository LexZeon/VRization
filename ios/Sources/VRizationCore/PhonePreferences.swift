import Foundation

/// A complete local profile. Pairing codes and session credentials have no storage field.
public struct PhonePreferences: Codable, Equatable {
    public var settings = VRSettings()
    public var language = "en"
    public var transport = "usb"
    public var host = ""
    public var port = "8765"
    public var hasCommittedProfile = false
    public init() {}
    public static let defaults = PhonePreferences()
    public func validated() throws -> PhonePreferences {
        _ = try settings.validated()
        guard ["en", "zh-Hans"].contains(language), ["usb", "lan"].contains(transport),
              host.utf8.count <= 253, !host.contains(where: { $0.isNewline }),
              port.utf8.count <= 5, port.utf8.allSatisfy({ (48...57).contains($0) }) else {
            throw VRCoreError.invalid("Invalid local preferences")
        }
        // Empty/partly entered connection fields may be remembered; validation
        // for connecting remains the stricter ConnectionInput.url contract.
        return self
    }
}

public final class PhonePreferencesStore {
    private let defaults: UserDefaults
    public static let key = "phonePreferences"
    public init(defaults: UserDefaults = .standard) { self.defaults = defaults }
    public func load() -> PhonePreferences {
        if let data = defaults.data(forKey: Self.key) {
            return ((try? JSONDecoder().decode(PhonePreferences.self, from: data)).flatMap { try? $0.validated() }) ?? .defaults
        }
        // Preserve the v0.2 profile without keeping its obsolete split storage.
        var result = PhonePreferences()
        if let data = defaults.data(forKey: "displaySettings"), let settings = try? VRSettings.decode(data) {
            result.settings = settings; result.hasCommittedProfile = true
        }
        result.language = defaults.string(forKey: "language") == "zh-Hans" ? "zh-Hans" : "en"
        result.transport = defaults.string(forKey: "transport") == "lan" ? "lan" : "usb"
        result.host = defaults.string(forKey: "host") ?? ""; result.port = defaults.string(forKey: "port") ?? "8765"
        return (try? result.validated()) ?? .defaults
    }
    public func save(_ preferences: PhonePreferences) throws {
        defaults.set(try JSONEncoder().encode(preferences.validated()), forKey: Self.key)
        for key in ["displaySettings", "language", "transport", "host", "port", "code", "token", "pairingCode"] { defaults.removeObject(forKey: key) }
    }
    public func reset() throws {
        for key in [Self.key, "displaySettings", "language", "transport", "host", "port", "code", "token", "pairingCode"] { defaults.removeObject(forKey: key) }
        var reset = PhonePreferences.defaults; reset.hasCommittedProfile = true
        try save(reset)
    }
}
