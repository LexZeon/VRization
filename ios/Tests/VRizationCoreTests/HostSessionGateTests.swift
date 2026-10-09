import XCTest
@testable import VRizationCore

/// Exercises the same fail-closed gate used before either transport reaches ImageIO.
final class HostSessionGateTests: XCTestCase {
    private func helloObject() throws -> [String: Any] {
        ["v": 1, "type": "hello", "name": "VRization", "version": "0.2.0",
         "settings": try JSONSerialization.jsonObject(with: JSONEncoder().encode(VRSettings())),
         "mouseArmed": false, "stream": ["codec": "jpeg", "fps": 30, "maxWidth": 1280]]
    }
    private func hello() throws -> Data { try JSONSerialization.data(withJSONObject: helloObject()) }
    private func settings() throws -> Data {
        try JSONSerialization.data(withJSONObject: ["v": 1, "type": "settings", "revision": 1, "clientSeq": 2,
            "settings": JSONSerialization.jsonObject(with: JSONEncoder().encode(VRSettings()))])
    }

    func testOnlyValidatedHelloEstablishesSessionThenMessagesAndVideoAreAccepted() throws {
        var gate = HostSessionGate()
        XCTAssertFalse(gate.isEstablished)
        guard case .established(let host) = try gate.receiveText(hello()) else { return XCTFail("Expected one establishment") }
        XCTAssertEqual(host.stream.codec, "jpeg")
        XCTAssertTrue(gate.isEstablished)
        XCTAssertNoThrow(try gate.receiveJPEG(byteCount: 4))
        XCTAssertNoThrow(try gate.receiveJPEG(byteCount: HostSessionGate.maximumJPEGBytes))
        XCTAssertEqual(try gate.receiveText(Data("{\"v\":1,\"type\":\"pong\"}".utf8)), .message(.pong))
        guard case .message(.settings(let update)) = try gate.receiveText(settings()) else { return XCTFail("Expected settings") }
        XCTAssertEqual(update.clientSeq, 2)
        XCTAssertEqual(update.revision, 1)
    }

    func testPreHelloJPEGIsRejectedAndCannotBeRescuedByLaterHello() throws {
        var gate = HostSessionGate()
        XCTAssertThrowsError(try gate.receiveJPEG(byteCount: 100))
        XCTAssertFalse(gate.isEstablished)
        XCTAssertThrowsError(try gate.receiveText(hello()))
        gate.reset()
        XCTAssertNoThrow(try gate.receiveText(hello()))
        XCTAssertTrue(gate.isEstablished)
    }

    func testSettingsPongAndErrorCannotSubstituteForHandshake() throws {
        let messages = [try settings(), Data("{\"v\":1,\"type\":\"pong\"}".utf8),
                        Data("{\"v\":1,\"type\":\"error\",\"message\":\"rejected\"}".utf8)]
        for message in messages {
            var gate = HostSessionGate()
            XCTAssertThrowsError(try gate.receiveText(message))
            XCTAssertFalse(gate.isEstablished)
            XCTAssertThrowsError(try gate.receiveText(hello()))
        }
    }

    func testMalformedVersionCodecJSONAndOversizedTextPoisonBothSessionPhases() throws {
        var wrongVersion = try helloObject(); wrongVersion["v"] = 2
        var wrongCodec = try helloObject(); wrongCodec["stream"] = ["codec": "h264", "fps": 30, "maxWidth": 1280]
        let invalid = [try JSONSerialization.data(withJSONObject: wrongVersion),
                       try JSONSerialization.data(withJSONObject: wrongCodec), Data("{".utf8), Data([0xff]),
                       Data(repeating: 32, count: VRProtocol.maximumTextBytes + 1)]
        for alreadyEstablished in [false, true] {
            for data in invalid {
                var gate = HostSessionGate()
                if alreadyEstablished { _ = try gate.receiveText(hello()) }
                XCTAssertThrowsError(try gate.receiveText(data))
                XCTAssertFalse(gate.isEstablished)
                XCTAssertThrowsError(try gate.receiveJPEG(byteCount: 100))
                XCTAssertThrowsError(try gate.receiveText(hello()))
            }
        }
    }

    func testDuplicateHelloNeverEstablishesOrResetsSessionTwice() throws {
        var gate = HostSessionGate()
        _ = try gate.receiveText(hello())
        XCTAssertThrowsError(try gate.receiveText(hello()))
        XCTAssertFalse(gate.isEstablished)
        XCTAssertThrowsError(try gate.receiveJPEG(byteCount: 100))
    }

    func testInvalidFrameLengthsCloseAnEstablishedSession() throws {
        for count in [-1, 0, 3, HostSessionGate.maximumJPEGBytes + 1] {
            var gate = HostSessionGate()
            _ = try gate.receiveText(hello())
            XCTAssertThrowsError(try gate.receiveJPEG(byteCount: count))
            XCTAssertFalse(gate.isEstablished)
            XCTAssertThrowsError(try gate.receiveText(hello()))
        }
    }

    func testNewTransportMustPerformItsOwnHandshake() throws {
        var gate = HostSessionGate()
        _ = try gate.receiveText(hello())
        gate.reset()
        XCTAssertFalse(gate.isEstablished)
        XCTAssertThrowsError(try gate.receiveJPEG(byteCount: 100))
        gate.reset()
        guard case .established = try gate.receiveText(hello()) else { return XCTFail("New session must establish once") }
    }
    private func legacyHello(capabilities: Any? = nil) throws -> Data {
        var object = try helloObject()
        var settings = try XCTUnwrap(object["settings"] as? [String: Any])
        settings.removeValue(forKey: "stabilization"); object["settings"] = settings
        if let capabilities = capabilities { object["capabilities"] = capabilities }
        return try JSONSerialization.data(withJSONObject: object)
    }
    func testLegacyUSBHelloCapabilityIsAvailableBeforeProfileRestore() throws {
        var gate = HostSessionGate()
        guard case .established(let host) = try gate.receiveText(legacyHello(capabilities: ["stabilization"])) else { return XCTFail("Expected hello") }
        XCTAssertTrue(host.supportsStabilization); XCTAssertTrue(gate.supportsStabilization)
        XCTAssertTrue(gate.awaitingSettingsSnapshot)
        let full = try JSONSerialization.data(withJSONObject: ["v": 1, "type": "settings", "revision": 0,
            "settings": JSONSerialization.jsonObject(with: JSONEncoder().encode(VRSettings()))])
        guard case .message(.settings(let snapshot)) = try gate.receiveText(full) else { return XCTFail("Expected full snapshot") }
        XCTAssertFalse(gate.awaitingSettingsSnapshot)
        var profileSync = LocalProfileSync(); profileSync.newSession(hasSavedProfile: true)
        let local = try VRSettings().applying(["stabilization": 0.62])
        XCTAssertEqual(profileSync.receive(snapshot: snapshot.settings, revision: snapshot.revision, clientSeq: nil), .restoreLocal)
        let wire = try VRProtocol.encodeSettings(local, supportsStabilization: gate.supportsStabilization)
        let body = try XCTUnwrap((JSONSerialization.jsonObject(with: wire) as? [String: Any])?["settings"] as? [String: Any])
        XCTAssertEqual(body["stabilization"] as? Double, 0.62)
    }
    func testNewSessionCannotInheritPreviousCapability() throws {
        var gate = HostSessionGate()
        _ = try gate.receiveText(hello()); XCTAssertTrue(gate.supportsStabilization)
        gate.reset(); XCTAssertFalse(gate.supportsStabilization)
        _ = try gate.receiveText(legacyHello()); XCTAssertFalse(gate.supportsStabilization)
        let local = try VRSettings().applying(["stabilization": 0.62])
        let data = try JSONSerialization.data(withJSONObject: ["v": 1, "type": "settings", "settings": ["scale": 0.9]])
        guard case .message(.settings(let update)) = try gate.receiveText(data, settingsBase: local) else { return XCTFail("Expected update") }
        XCTAssertEqual(update.settings.stabilization, 0.62); XCTAssertFalse(gate.supportsStabilization)
        let upgraded = try JSONSerialization.data(withJSONObject: ["v": 1, "type": "settings", "settings": ["stabilization": 0.4]])
        guard case .message(.settings(let new)) = try gate.receiveText(upgraded, settingsBase: local) else { return XCTFail("Expected upgrade") }
        XCTAssertEqual(new.settings.stabilization, 0.4); XCTAssertTrue(gate.supportsStabilization)
    }
    func testMalformedCapabilitiesCannotEstablishOrEnableSupport() throws {
        let invalidValues: [Any] = ["stabilization", ["stabilization", 1] as [Any], true, NSNull()]
        for invalid in invalidValues {
            var gate = HostSessionGate()
            XCTAssertThrowsError(try gate.receiveText(legacyHello(capabilities: invalid)))
            XCTAssertFalse(gate.isEstablished); XCTAssertFalse(gate.supportsStabilization)
        }
        var gate = HostSessionGate()
        let premature = try JSONSerialization.data(withJSONObject: ["v": 1, "type": "settings", "settings": ["stabilization": 0.4]])
        XCTAssertThrowsError(try gate.receiveText(premature)); XCTAssertFalse(gate.supportsStabilization)
    }

    func testFreshUSBProfileWaitsForFullSchemaBeforeNoSensorFallback() throws {
        var object = try helloObject()
        var legacy = try XCTUnwrap(object["settings"] as? [String: Any])
        legacy["mode"] = "fps"; legacy.removeValue(forKey: "stabilization")
        object["settings"] = legacy; object["capabilities"] = ["stabilization"]
        var gate = HostSessionGate()
        _ = try gate.receiveText(JSONSerialization.data(withJSONObject: object))
        XCTAssertTrue(gate.awaitingSettingsSnapshot)
        // The owner sends schema metadata, not settings, while callbacks wait.
        let request = try XCTUnwrap(JSONSerialization.jsonObject(with: VRProtocol.hello()) as? [String: Any])
        XCTAssertEqual(request["settingsSchema"] as? Int, 2); XCTAssertNil(request["settings"])
        let host = try VRSettings().applying(["mode": "fps", "stabilization": 0.72])
        let full = try JSONSerialization.data(withJSONObject: ["v": 1, "type": "settings", "revision": 4,
            "settings": JSONSerialization.jsonObject(with: JSONEncoder().encode(host))])
        guard case .message(.settings(let update)) = try gate.receiveText(full) else { return XCTFail("Expected snapshot") }
        XCTAssertFalse(gate.awaitingSettingsSnapshot)
        var profiles = LocalProfileSync(); profiles.newSession(hasSavedProfile: false)
        XCTAssertEqual(profiles.receive(snapshot: update.settings, revision: update.revision, clientSeq: nil), .applyHost)
        // This is the Viewer's sole sensor fallback change after adoption.
        let fallback = try update.settings.applying(["mode": "full"])
        let wire = try VRProtocol.encodeSettings(fallback, supportsStabilization: gate.supportsStabilization)
        let body = try XCTUnwrap((JSONSerialization.jsonObject(with: wire) as? [String: Any])?["settings"] as? [String: Any])
        XCTAssertEqual(body["mode"] as? String, "full"); XCTAssertEqual(body["stabilization"] as? Double, 0.72)
    }

    func testPartialOrAcknowledgedSettingsCannotEndInitialSchemaNegotiation() throws {
        var gate = HostSessionGate()
        _ = try gate.receiveText(legacyHello(capabilities: ["stabilization"]))
        XCTAssertNoThrow(try gate.receiveJPEG(byteCount: 100))
        let partial = try JSONSerialization.data(withJSONObject: ["v": 1, "type": "settings", "settings": ["stabilization": 0.72]])
        _ = try gate.receiveText(partial); XCTAssertTrue(gate.awaitingSettingsSnapshot)
        _ = try gate.receiveText(Data("{\"v\":1,\"type\":\"pong\"}".utf8)); XCTAssertTrue(gate.awaitingSettingsSnapshot)
        _ = try gate.receiveText(settings()); XCTAssertTrue(gate.awaitingSettingsSnapshot)
        gate.reset(); XCTAssertFalse(gate.awaitingSettingsSnapshot)
        _ = try gate.receiveText(legacyHello()); XCTAssertFalse(gate.awaitingSettingsSnapshot)
        gate.reset(); _ = try gate.receiveText(hello()); XCTAssertFalse(gate.awaitingSettingsSnapshot)
    }
}
