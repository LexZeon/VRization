import Foundation
import VRizationCore

/// Preview storage has a distinct key as well as a distinct application bundle.
/// Stable settings and session descriptors are never migrated into this profile.
public final class SteamVRPreferencesStore {
    public static let key = "steamvrPhonePreferencesV1"
    private let defaults: UserDefaults
    public init(defaults: UserDefaults = .standard) { self.defaults = defaults }
    public static var initial: PhonePreferences {
        var result = PhonePreferences(); result.port = "8766"; return result
    }
    public func load() -> PhonePreferences {
        guard let data = defaults.data(forKey: Self.key),
              let value = try? JSONDecoder().decode(PhonePreferences.self, from: data),
              let valid = try? value.validated() else { return Self.initial }
        return valid
    }
    public func save(_ preferences: PhonePreferences) throws {
        defaults.set(try JSONEncoder().encode(preferences.validated()), forKey: Self.key)
    }
    public func reset() throws {
        defaults.removeObject(forKey: Self.key)
        var value = Self.initial; value.hasCommittedProfile = true
        try save(value)
    }
}
