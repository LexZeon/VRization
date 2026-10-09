import XCTest
@testable import VRizationCore

final class ProtocolTests: XCTestCase {
    func testEditorHelloNegotiatesSchemaAndCarriesOnlyDisarmControl() throws {
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: VRProtocol.editorHello()) as? [String: Any])
        XCTAssertEqual(Set(object.keys), Set(["v", "type", "editing", "settingsSchema"]))
        XCTAssertEqual(object["settingsSchema"] as? Int, 2)
        XCTAssertEqual(object["type"] as? String, "hello")
        XCTAssertEqual(object["editing"] as? Bool, true)
        XCTAssertEqual(object["v"] as? Int, 1)
        XCTAssertNil(object["arm"]); XCTAssertNil(object["settings"])
    }
    private func settingsObject() throws -> Any {
        return try JSONSerialization.jsonObject(with: JSONEncoder().encode(VRSettings()))
    }
    private func data(_ object: [String: Any]) throws -> Data { return try JSONSerialization.data(withJSONObject: object) }
    func testHelloAndRevisionAcknowledgment() throws {
        let hello = try data(["v": 1, "type": "hello", "name": "VRization", "version": "0.1.2",
            "revision": 4, "settings": settingsObject(), "mouseArmed": false,
            "stream": ["codec": "jpeg", "fps": 30, "maxWidth": 1280]])
        guard case .hello(let value) = try VRProtocol.decodeHostMessage(hello) else { return XCTFail("Expected hello") }
        XCTAssertEqual(value.revision, 4)
        XCTAssertEqual(value.settings, VRSettings())
        XCTAssertFalse(value.mouseArmed)
        XCTAssertEqual(value.stream.maxWidth, 1280)
        let update = try data(["v": 1, "type": "settings", "revision": 5, "clientSeq": 2, "settings": settingsObject()])
        guard case .settings(let value2) = try VRProtocol.decodeHostMessage(update) else { return XCTFail("Expected settings") }
        XCTAssertEqual(value2.revision, 5); XCTAssertEqual(value2.clientSeq, 2)
    }
    func testLegacySettingsWithoutMetadataRemainCompatible() throws {
        let message = try data(["v": 1, "type": "settings", "settings": settingsObject()])
        guard case .settings(let update) = try VRProtocol.decodeHostMessage(message) else { return XCTFail("Expected settings") }
        XCTAssertNil(update.revision); XCTAssertNil(update.clientSeq)
    }
    func testMetadataRejectsBooleansFractionsNegativeAndUnsafeIntegers() throws {
        for key in ["revision", "clientSeq"] {
            let invalidValues: [Any] = [true, -1, 1.5, "2", NSNull(), 9_007_199_254_740_992 as Int64]
            for invalid in invalidValues {
                let message = try data(["v": 1, "type": "settings", "settings": settingsObject(), key: invalid])
                XCTAssertThrowsError(try VRProtocol.decodeHostMessage(message))
            }
        }
        for raw in ["{\"v\":true,\"type\":\"pong\"}", "{\"v\":2,\"type\":\"pong\"}",
                    "[]", "{\"v\":1,\"type\":\"arm\"}", "{\"v\":1,\"type\":\"error\",\"message\":1}"] {
            XCTAssertThrowsError(try VRProtocol.decodeHostMessage(Data(raw.utf8)))
        }
    }
    func testUnknownCodecIsRejectedBeforeFrameDecoding() throws {
        let message = try data(["v": 1, "type": "hello", "name": "VRization", "version": "1",
            "settings": settingsObject(), "mouseArmed": false,
            "stream": ["codec": "h264", "fps": 30, "maxWidth": 1280]])
        XCTAssertThrowsError(try VRProtocol.decodeHostMessage(message))
        XCTAssertThrowsError(try VRProtocol.decodeHostMessage(Data(repeating: 32, count: 16_385)))
    }
    func testPoseLimitsAndControlMessages() throws {
        let value = try VRProtocol.encodePose(sequence: VRProtocol.maximumSequence, yaw: .pi, pitch: -0.2)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: value) as? [String: Any])
        XCTAssertEqual(object["type"] as? String, "pose")
        XCTAssertThrowsError(try VRProtocol.encodePose(sequence: -1, yaw: 0, pitch: 0))
        XCTAssertThrowsError(try VRProtocol.encodePose(sequence: 0, yaw: .infinity, pitch: 0))
        XCTAssertThrowsError(try VRProtocol.encodePose(sequence: 0, yaw: 0, pitch: 101))
        for control in [VRProtocol.hello(), VRProtocol.recenter(), VRProtocol.ping()] {
            let message = try XCTUnwrap(JSONSerialization.jsonObject(with: control) as? [String: Any])
            XCTAssertNil(message["arm"])
            XCTAssertEqual((message["v"] as? NSNumber)?.intValue, 1)
        }
    }
    func testLegacyNetworkEncodingRetainsLocalStabilization() throws {
        let local = try VRSettings().applying(["stabilization": 0.73, "scale": 0.64, "eyeSeparation": -0.3])
        for supported in [false, true] {
            let data = try VRProtocol.encodeSettings(local, clientSeq: 9, supportsStabilization: supported)
            let message = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
            let body = try XCTUnwrap(message["settings"] as? [String: Any])
            XCTAssertEqual(body.count, supported ? 11 : 10)
            XCTAssertEqual(body["scale"] as? Double, 0.64)
            XCTAssertEqual(body["eyeSeparation"] as? Double, -0.3)
            XCTAssertEqual(message["clientSeq"] as? Int, 9)
            if supported { XCTAssertEqual(body["stabilization"] as? Double, 0.73) }
            else { XCTAssertNil(body["stabilization"]) }
        }
        XCTAssertEqual(local.stabilization, 0.73)
        XCTAssertEqual(try VRSettings.decode(JSONEncoder().encode(local)), local)
    }
    func testPartialAndLegacyAcknowledgmentsMergeIntoLocalBase() throws {
        let local = try VRSettings().applying(["stabilization": 0.73, "scale": 0.64, "mode": "fps"])
        var legacy = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(local)) as? [String: Any])
        legacy.removeValue(forKey: "stabilization")
        for patch in [["scale": 0.64] as [String: Any], legacy] {
            let wire = try data(["v": 1, "type": "settings", "settings": patch, "revision": 2, "clientSeq": 4])
            guard case .settings(let value) = try VRProtocol.decodeHostMessage(wire, settingsBase: local) else { return XCTFail("Expected ACK") }
            XCTAssertEqual(value.settings, local); XCTAssertFalse(value.includesStabilization)
        }
        for patch in [[:], ["unknown": 1], ["stabilization": true], ["stabilization": 1.1]] as [[String: Any]] {
            XCTAssertThrowsError(try VRProtocol.decodeHostMessage(data(["v": 1, "type": "settings", "settings": patch]), settingsBase: local))
        }
    }
    func testClientHelloAdvertisesSchemaWithoutGrantingInput() throws {
        let hello = try XCTUnwrap(JSONSerialization.jsonObject(with: VRProtocol.hello()) as? [String: Any])
        XCTAssertEqual(hello["settingsSchema"] as? Int, 2)
        XCTAssertNil(hello["settings"]); XCTAssertNil(hello["arm"]); XCTAssertNil(hello["editing"])
    }
}
