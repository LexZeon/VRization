import Foundation
import VRizationCore
#if STEAMVR_PREVIEW
import VRizationSteamVRCore
typealias AppPreferencesStore = SteamVRPreferencesStore
#else
typealias AppPreferencesStore = PhonePreferencesStore
#endif

enum L {
    static var language: String {
        get { AppPreferencesStore().load().language }
        set { var profile = AppPreferencesStore().load(); profile.language = newValue == "zh-Hans" ? "zh-Hans" : "en"; try? AppPreferencesStore().save(profile) }
    }
    static func text(_ key: String) -> String {
        guard let path = Bundle.main.path(forResource: language, ofType: "lproj"), let bundle = Bundle(path: path)
        else { return key }
        return bundle.localizedString(forKey: key, value: key, table: nil)
    }
}
