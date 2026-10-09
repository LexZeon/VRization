import XCTest
@testable import VRizationCore

final class ProtocolTests: XCTestCase {
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
}
