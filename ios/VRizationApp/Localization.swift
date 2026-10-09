import Foundation

enum L {
    static var language: String {
        get { UserDefaults.standard.string(forKey: "language") == "zh-Hans" ? "zh-Hans" : "en" }
        set { UserDefaults.standard.set(newValue == "zh-Hans" ? "zh-Hans" : "en", forKey: "language") }
    }
    static func text(_ key: String) -> String {
        guard let path = Bundle.main.path(forResource: language, ofType: "lproj"), let bundle = Bundle(path: path)
        else { return key }
        return bundle.localizedString(forKey: key, value: key, table: nil)
    }
}
