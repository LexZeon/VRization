import XCTest
@testable import VRizationCore

final class SettingsTests: XCTestCase {
    func testDefaultsAndCompleteCodableRoundTrip() throws {
        let defaults = VRSettings()
        XCTAssertEqual(defaults.scale, 0.85)
        XCTAssertEqual(defaults.eyeSeparation, 0.03)
        XCTAssertEqual(defaults.sensitivity, 1000)
        XCTAssertEqual(defaults.stabilization, 0)
        XCTAssertEqual(try VRSettings.decode(JSONEncoder().encode(defaults)), defaults)
    }
    func testPartialUpdatePreservesOtherValuesAndAcceptsExactBounds() throws {
        let settings = try VRSettings().applying(["offsetX": 0.3, "offsetY": -0.3, "eyeSeparation": 0.2,
                                                  "scale": 0.5, "invertY": true, "mode": "fps"])
        XCTAssertEqual(settings.offsetX, 0.3)
        XCTAssertEqual(settings.offsetY, -0.3)
        XCTAssertEqual(settings.fov, 80)
        XCTAssertTrue(settings.invertY)
        let wire = try VRProtocol.encodeSettings(settings, clientSeq: 1)
        guard let object = try JSONSerialization.jsonObject(with: wire) as? [String: Any],
              let body = object["settings"] as? [String: Any] else { return XCTFail("Missing settings") }
        XCTAssertEqual((body["offsetX"] as? NSNumber)?.doubleValue, 0.3)
        XCTAssertEqual((body["eyeSeparation"] as? NSNumber)?.doubleValue, 0.2)
    }
    func testInvalidPartialUpdatesNeverCoerceOrClamp() throws {
        let invalid: [[String: Any]] = [[:], ["unknown": 1], ["scale": true], ["scale": "0.8"],
            ["invertY": 1], ["mode": "vr"], ["distance": NSNull()], ["offsetX": 0.30000001],
            ["eyeSeparation": -1.01], ["fov": Double.nan], ["distortion": Double.infinity]]
        for patch in invalid { XCTAssertThrowsError(try VRSettings().applying(patch), "Accepted \(patch)") }
    }
    func testCompleteDecodeRejectsMissingUnknownAndWrongTypedFields() throws {
        let encoded = try JSONEncoder().encode(VRSettings())
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: encoded) as? [String: Any])
        object["extra"] = 1
        XCTAssertThrowsError(try VRSettings.decode(JSONSerialization.data(withJSONObject: object)))
        object.removeValue(forKey: "extra"); object.removeValue(forKey: "scale")
        XCTAssertThrowsError(try VRSettings.decode(JSONSerialization.data(withJSONObject: object)))
        object["scale"] = true
        XCTAssertThrowsError(try VRSettings.decode(JSONSerialization.data(withJSONObject: object)))
    }
    func testPublicMutableSettingsStillValidateBeforeEncoding() throws {
        var settings = VRSettings(); settings.sensitivity = 3001
        XCTAssertThrowsError(try JSONEncoder().encode(settings))
        XCTAssertThrowsError(try VRProtocol.encodeSettings(settings))
    }
    func testStabilizationBoundsAndStrictTypes() throws {
        for value in [0.0, 0.37, 1.0] {
            let settings = try VRSettings().applying(["stabilization": value])
            XCTAssertEqual(settings.stabilization, value)
            XCTAssertEqual(try VRSettings.decode(JSONEncoder().encode(settings)), settings)
        }
        let invalid: [Any] = [-0.001, 1.001, Double.nan, Double.infinity, true, "0.5", NSNull()]
        for value in invalid {
            XCTAssertThrowsError(try VRSettings().applying(["stabilization": value]))
        }
        var invalid = VRSettings(); invalid.stabilization = 2
        XCTAssertThrowsError(try JSONEncoder().encode(invalid))
    }
    func testExactLegacyTenFieldProfileMigratesAndKeepsOtherValues() throws {
        let previous = try VRSettings().applying(["mode": "fps", "scale": 0.61, "eyeSeparation": -0.4,
                                                   "offsetY": 0.12, "sensitivity": 1720, "invertY": true])
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(previous)) as? [String: Any])
        object.removeValue(forKey: "stabilization")
        XCTAssertEqual(object.count, 10)
        let migrated = try VRSettings.decode(JSONSerialization.data(withJSONObject: object))
        XCTAssertEqual(migrated, previous); XCTAssertEqual(migrated.stabilization, 0)
        let upgraded = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(migrated)) as? [String: Any])
        XCTAssertEqual(upgraded.count, 11); XCTAssertEqual(upgraded["stabilization"] as? Double, 0)
        object.removeValue(forKey: "fov")
        XCTAssertThrowsError(try VRSettings.decode(JSONSerialization.data(withJSONObject: object)))
        object["stabilization"] = 0
        XCTAssertThrowsError(try VRSettings.decode(JSONSerialization.data(withJSONObject: object)))
    }
}
