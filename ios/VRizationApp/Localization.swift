import Foundation
import VRizationCore

enum L {
    static var language: String {
        get { PhonePreferencesStore().load().language }
        set { var profile = PhonePreferencesStore().load(); profile.language = newValue == "zh-Hans" ? "zh-Hans" : "en"; try? PhonePreferencesStore().save(profile) }
    }
    static func text(_ key: String) -> String {
        guard let path = Bundle.main.path(forResource: language, ofType: "lproj"), let bundle = Bundle(path: path)
        else { return key }
        return bundle.localizedString(forKey: key, value: key, table: nil)
    }
}
