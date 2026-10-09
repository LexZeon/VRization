import XCTest
@testable import VRizationCore

final class PhonePreferencesTests: XCTestCase {
    private func withStore(_ action: (PhonePreferencesStore, UserDefaults) throws -> Void) rethrows {
        let name = "org.vrization.tests.\(UUID().uuidString)"
        let isolated = UserDefaults(suiteName: name)!
        defer { isolated.removePersistentDomain(forName: name) }
        try action(PhonePreferencesStore(defaults: isolated), isolated)
    }
    func testDefaultsAreEnglishUSBFullAndEmptyAddress() throws {
        try withStore { store, _ in
            XCTAssertEqual(store.load(), .defaults)
            XCTAssertEqual(store.load().language, "en"); XCTAssertEqual(store.load().transport, "usb")
            XCTAssertEqual(store.load().settings.mode, "full"); XCTAssertEqual(store.load().host, ""); XCTAssertEqual(store.load().port, "8765")
        }
    }
    func testCompleteProfileSurvivesStoreRecreation() throws {
        try withStore { store, defaults in
            var profile = PhonePreferences(); profile.language = "zh-Hans"; profile.transport = "lan"; profile.host = "pc.local"; profile.port = "19000"
            profile.hasCommittedProfile = true
            profile.settings = try VRSettings().applying(["mode": "fps", "scale": 0.62, "offsetX": 0.15, "offsetY": -0.11,
                "eyeSeparation": 0.08, "fov": 100.0, "distance": 7.0, "distortion": 0.2, "sensitivity": 1700.0, "invertY": true])
            try store.save(profile)
            XCTAssertEqual(PhonePreferencesStore(defaults: defaults).load(), profile)
            let wire = String(data: defaults.data(forKey: PhonePreferencesStore.key)!, encoding: .utf8)!
            XCTAssertFalse(wire.contains("token")); XCTAssertFalse(wire.contains("pairingCode"))
        }
    }
    func testUpgradeMigratesV02ProfileThenRemovesSplitKeysAndSecrets() throws {
        try withStore { store, defaults in
            let old = try VRSettings().applying(["scale": 0.7, "mode": "cinema"])
            defaults.set(try JSONEncoder().encode(old), forKey: "displaySettings")
            defaults.set("zh-Hans", forKey: "language"); defaults.set("lan", forKey: "transport"); defaults.set("old.local", forKey: "host")
            defaults.set("654321", forKey: "pairingCode")
            let migrated = store.load(); XCTAssertEqual(migrated.settings, old); XCTAssertEqual(migrated.language, "zh-Hans")
            XCTAssertTrue(migrated.hasCommittedProfile)
            try store.save(migrated)
            XCTAssertNil(defaults.object(forKey: "displaySettings")); XCTAssertNil(defaults.object(forKey: "pairingCode"))
            XCTAssertEqual(store.load(), migrated)
        }
    }
    func testCorruptOrOutOfRangeProfileFallsBackToDefaults() throws {
        try withStore { store, defaults in
            defaults.set(Data("broken".utf8), forKey: PhonePreferencesStore.key); XCTAssertEqual(store.load(), .defaults)
            var profile = PhonePreferences(); profile.settings.scale = 1.1
            XCTAssertThrowsError(try store.save(profile)); XCTAssertEqual(store.load(), .defaults)
            profile = .defaults; profile.language = "invalid"; XCTAssertThrowsError(try store.save(profile))
        }
    }
    func testResetClearsAllOwnedPreferencesIncludingLegacySecrets() throws {
        try withStore { store, defaults in
            var profile = PhonePreferences(); profile.language = "zh-Hans"; profile.transport = "lan"; profile.host = "pc.local"; profile.settings.scale = 0.5
            try store.save(profile)
            for key in ["code", "token", "pairingCode"] { defaults.set("secret", forKey: key) }
            try store.reset()
            var reset = PhonePreferences.defaults; reset.hasCommittedProfile = true
            XCTAssertEqual(store.load(), reset)
            for key in ["code", "token", "pairingCode", "language", "transport", "host", "port"] { XCTAssertNil(defaults.object(forKey: key)) }
        }
    }
    func testLanguageAndAddressAloneDoNotClaimACommittedVRProfile() throws {
        try withStore { store, _ in
            var profile = PhonePreferences(); profile.language = "zh-Hans"; profile.host = "pc.local"
            try store.save(profile)
            XCTAssertFalse(store.load().hasCommittedProfile)
        }
    }
}
