import XCTest
@testable import VRizationCore

final class EnhancedFirstPersonTests: XCTestCase {
    private func enhanced(_ patch: [String: Any] = [:]) throws -> VRSettings {
        var changes = patch; changes["mode"] = "fps_enhanced"
        return try VRSettings().applying(changes)
    }
    private func data(_ object: [String: Any]) throws -> Data {
        try JSONSerialization.data(withJSONObject: object)
    }
    private func hello(settings: VRSettings = .defaults, capable: Bool = true, negotiated: Bool = false) throws -> Data {
        var object: [String: Any] = ["v": 1, "type": "hello", "name": "fixture", "version": "0.4.0",
            "settings": try JSONSerialization.jsonObject(with: JSONEncoder().encode(settings)), "mouseArmed": false,
            "stream": ["codec": "jpeg", "fps": 60, "maxWidth": 640], "enhancedFirstPerson": negotiated]
        if capable { object["capabilities"] = ["enhanced-first-person", "stabilization"] }
        return try data(object)
    }
    private func snapshot(_ settings: VRSettings, marker: Any? = true, sequence: Int64? = nil) throws -> Data {
        var object: [String: Any] = ["v": 1, "type": "settings", "revision": 2,
            "settings": try JSONSerialization.jsonObject(with: JSONEncoder().encode(settings))]
        if let marker = marker { object["enhancedFirstPerson"] = marker }
        if let sequence = sequence { object["clientSeq"] = sequence }
        return try data(object)
    }
    func testEnhancedIsFirstPersonButItsDisplayDoesNotRequireMotion() throws {
        let value = try enhanced()
        XCTAssertTrue(value.isFirstPerson); XCTAssertFalse(value.requiresMotion)
        XCTAssertEqual(try VRSettings.decode(JSONEncoder().encode(value)), value)
        XCTAssertTrue(try VRSettings().applying(["mode": "fps"]).requiresMotion)
        XCTAssertTrue(try VRSettings().applying(["mode": "cinema"]).requiresMotion)
        XCTAssertFalse(VRSettings().isFirstPerson)
    }
    func testEnhancedViewportIsPhysicallySquareForAnySourceAndEyeAspect() throws {
        let settings = try enhanced(["scale": 0.63])
        for eyeAspect in [0.5, 1, 1.7, 2.4] {
            for imageAspect in [0.3, 1, 16.0 / 9, 4] {
                let rect = try HeadsetFit.eyeRect(settings: settings, imageAspect: imageAspect, eyeAspect: eyeAspect, eyeSign: -1)
                XCTAssertEqual(rect.halfSize.x * eyeAspect, rect.halfSize.y, accuracy: 1e-12)
                XCTAssertEqual(rect.halfSize, try HeadsetFit.eyeRect(settings: settings, imageAspect: 1,
                    eyeAspect: eyeAspect, eyeSign: 1).halfSize)
            }
        }
    }
    func testOrdinaryModesKeepSourceAspectGeometry() throws {
        for mode in ["full", "cinema", "fps"] {
            let settings = try VRSettings().applying(["mode": mode])
            XCTAssertEqual(try HeadsetFit.fit(settings: settings, imageAspect: 2.3, eyeAspect: 1.2),
                try HeadsetFit.fit(imageAspect: 2.3, eyeAspect: 1.2))
        }
    }
    func testEnhancedEditorResizeKeepsSquareAndMirroredPanCanReachSeam() throws {
        let start = try enhanced(["scale": 0.6, "eyeSeparation": -0.9, "offsetX": 0.2, "fov": 92.0])
        for eyeAspect in [0.6, 1.3, 2] {
            let resized = try HeadsetFit.resize(entry: start, delta: FitPoint(x: 0.03, y: 0.12),
                cornerSign: FitPoint(x: 1, y: 1), imageAspect: 16.0 / 9, eyeAspect: eyeAspect)
            XCTAssertEqual(resized.mode, "fps_enhanced"); XCTAssertEqual(resized.fov, 92)
            let contact = try HeadsetFit.mirroredPan(entry: resized, delta: FitPoint(x: 2, y: 0.1),
                eyeSign: -1, imageAspect: 16.0 / 9, eyeAspect: eyeAspect)
            let left = try HeadsetFit.eyeRect(settings: contact, imageAspect: 16.0 / 9, eyeAspect: eyeAspect, eyeSign: -1)
            let right = try HeadsetFit.eyeRect(settings: contact, imageAspect: 16.0 / 9, eyeAspect: eyeAspect, eyeSign: 1)
            XCTAssertEqual(left.halfSize.x * eyeAspect, left.halfSize.y, accuracy: 1e-12)
            XCTAssertEqual(left.center.x + left.halfSize.x, 1, accuracy: 1e-12)
            XCTAssertEqual(right.center.x - right.halfSize.x, -1, accuracy: 1e-12)
            XCTAssertEqual(contact.offsetX, 0)
        }
    }
    func testProjectionCenterAndCardinalEdgesRemainAnchored() throws {
        for fov in [50.0, 80, 110] {
            XCTAssertEqual(try EnhancedProjection.sample(point: FitPoint(x: 0, y: 0), fov: fov), FitPoint(x: 0, y: 0))
            for point in [FitPoint(x: 1, y: 0), FitPoint(x: -1, y: 0), FitPoint(x: 0, y: 1), FitPoint(x: 0, y: -1)] {
                let value = try XCTUnwrap(EnhancedProjection.sample(point: point, fov: fov))
                XCTAssertEqual(value.x, point.x, accuracy: 1e-12); XCTAssertEqual(value.y, point.y, accuracy: 1e-12)
            }
        }
    }
    func testProjectionMatchesSharedGoldenCoordinates() throws {
        for (point, expected) in [
            (FitPoint(x: 0.5, y: 0), FitPoint(x: 0.4337628342841029, y: 0)),
            (FitPoint(x: 0.5, y: 0.5), FitPoint(x: 0.45344724847070744, y: 0.45344724847070744)),
            (FitPoint(x: 0.6, y: 0.2), FitPoint(x: 0.5343876845164115, y: 0.1781292281721372))
        ] {
            let value = try XCTUnwrap(EnhancedProjection.sample(point: point, fov: 80))
            XCTAssertEqual(value.x, expected.x, accuracy: 1e-12); XCTAssertEqual(value.y, expected.y, accuracy: 1e-12)
        }
    }
    func testProjectionIsSymmetricAndFovControlsCenterMagnification() throws {
        let point = FitPoint(x: 0.6, y: 0.2)
        let low = try XCTUnwrap(EnhancedProjection.sample(point: point, fov: 50))
        let high = try XCTUnwrap(EnhancedProjection.sample(point: point, fov: 110))
        XCTAssertLessThan(high.x, low.x); XCTAssertLessThan(high.y, low.y)
        let mirror = try XCTUnwrap(EnhancedProjection.sample(point: FitPoint(x: -point.x, y: -point.y), fov: 110))
        XCTAssertEqual(mirror.x, -high.x, accuracy: 1e-12); XCTAssertEqual(mirror.y, -high.y, accuracy: 1e-12)
        let rotated = try XCTUnwrap(EnhancedProjection.sample(point: FitPoint(x: point.y, y: point.x), fov: 110))
        XCTAssertEqual(rotated.x, high.y, accuracy: 1e-12); XCTAssertEqual(rotated.y, high.x, accuracy: 1e-12)
    }
    func testProjectionClipsOutsideViewportAndCurvedCorners() throws {
        for fov in [50.0, 80, 110] {
            XCTAssertNil(try EnhancedProjection.sample(point: FitPoint(x: 1, y: 1), fov: fov))
            XCTAssertNil(try EnhancedProjection.sample(point: FitPoint(x: 1.01, y: 0), fov: fov))
            XCTAssertNil(try EnhancedProjection.sample(point: FitPoint(x: 0, y: -1.01), fov: fov))
            XCTAssertNotNil(try EnhancedProjection.sample(point: FitPoint(x: 0.8, y: 0.6), fov: fov))
        }
    }
    func testProjectionRejectsInvalidFiniteRanges() throws {
        for fov in [49.99, 110.01, Double.nan, Double.infinity] {
            XCTAssertThrowsError(try EnhancedProjection.sample(point: FitPoint(x: 0, y: 0), fov: fov))
        }
        for point in [FitPoint(x: .nan, y: 0), FitPoint(x: 0, y: .infinity)] {
            XCTAssertThrowsError(try EnhancedProjection.sample(point: point, fov: 80))
        }
        XCTAssertThrowsError(try HeadsetFit.fit(settings: enhanced(), imageAspect: .nan, eyeAspect: 1))
    }
    func testHelloAndURLAdvertiseCapabilityWithoutGrantingInput() throws {
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: VRProtocol.hello()) as? [String: Any])
        XCTAssertEqual(object["settingsSchema"] as? Int, 2)
        XCTAssertEqual(object["capabilities"] as? [String], ["enhanced-first-person"])
        XCTAssertNil(object["settings"]); XCTAssertNil(object["arm"])
        let editor = try XCTUnwrap(JSONSerialization.jsonObject(with: VRProtocol.editorHello()) as? [String: Any])
        XCTAssertEqual(editor["editing"] as? Bool, true)
        XCTAssertEqual(editor["capabilities"] as? [String], ["enhanced-first-person"])
        let url = try ConnectionInput.url(host: "pc.local", port: "8765", token: "012345", settingsSchema: 2, enhancedFirstPerson: true)
        XCTAssertEqual(URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems?.last,
            URLQueryItem(name: "enhancedFirstPerson", value: "1"))
    }
    func testLegacyHostFallbackKeepsLocalEnhancedProfileAndAcknowledgesEcho() throws {
        let local = try enhanced(["scale": 0.62, "stabilization": 0.37])
        let wire = try VRProtocol.encodeSettings(local, clientSeq: 1, supportsStabilization: false, supportsEnhancedFirstPerson: false)
        let body = try XCTUnwrap((JSONSerialization.jsonObject(with: wire) as? [String: Any])?["settings"] as? [String: Any])
        XCTAssertEqual(body["mode"] as? String, "fps"); XCTAssertNil(body["stabilization"])
        XCTAssertEqual(local.mode, "fps_enhanced")
        let host = try VRProtocol.wireSettings(local, supportsEnhancedFirstPerson: false)
        let echo = try VRProtocol.localSettings(host, local: local, supportsEnhancedFirstPerson: false)
        var sync = SettingsSync(); sync.edited(); let sequence = try sync.nextSequence(); try sync.sent(sequence: sequence, snapshot: local)
        XCTAssertTrue(sync.accept(snapshot: echo, revision: nil, clientSeq: nil)); XCTAssertFalse(sync.awaitingAcknowledgment)
        XCTAssertEqual(echo, local)
        let full = try VRSettings().applying(["mode": "full"])
        XCTAssertEqual(try VRProtocol.localSettings(full, local: local, supportsEnhancedFirstPerson: false).mode, "full")
        XCTAssertEqual(try VRProtocol.localSettings(host, local: local, supportsEnhancedFirstPerson: true).mode, "fps")
    }
    func testUSBNegotiationWaitsForMarkedCompleteUnacknowledgedSnapshot() throws {
        var gate = HostSessionGate()
        _ = try gate.receiveText(hello(settings: VRSettings().applying(["mode": "fps"])))
        XCTAssertTrue(gate.supportsEnhancedFirstPerson); XCTAssertTrue(gate.awaitingSettingsSnapshot)
        _ = try gate.receiveText(snapshot(.defaults, marker: false)); XCTAssertTrue(gate.awaitingSettingsSnapshot)
        _ = try gate.receiveText(snapshot(.defaults, marker: nil)); XCTAssertTrue(gate.awaitingSettingsSnapshot)
        _ = try gate.receiveText(snapshot(try enhanced(), sequence: 1)); XCTAssertTrue(gate.awaitingSettingsSnapshot)
        _ = try gate.receiveText(data(["v": 1, "type": "settings", "enhancedFirstPerson": true, "settings": ["mode": "fps_enhanced"]]))
        XCTAssertTrue(gate.awaitingSettingsSnapshot)
        _ = try gate.receiveText(snapshot(try enhanced())); XCTAssertFalse(gate.awaitingSettingsSnapshot)
    }
    func testAlreadyNegotiatedLANHelloDoesNotWaitForUSBUpgrade() throws {
        var gate = HostSessionGate()
        guard case .established(let value) = try gate.receiveText(hello(settings: enhanced(), negotiated: true)) else { return XCTFail("Expected hello") }
        XCTAssertTrue(value.enhancedFirstPerson); XCTAssertTrue(gate.supportsEnhancedFirstPerson)
        XCTAssertFalse(gate.awaitingSettingsSnapshot)
        _ = try gate.receiveText(snapshot(try enhanced()))
        gate.reset(); XCTAssertFalse(gate.supportsEnhancedFirstPerson); XCTAssertFalse(gate.awaitingSettingsSnapshot)
    }
    func testUnnegotiatedEnhancedOrMalformedFlagsFailClosed() throws {
        XCTAssertThrowsError(try VRProtocol.decodeHostMessage(hello(settings: enhanced(), capable: false)))
        XCTAssertThrowsError(try VRProtocol.decodeHostMessage(hello(settings: enhanced(), negotiated: false)))
        for marker in [1, "true", NSNull()] as [Any] {
            var invalidHello = try XCTUnwrap(JSONSerialization.jsonObject(with: hello()) as? [String: Any])
            invalidHello["enhancedFirstPerson"] = marker
            XCTAssertThrowsError(try VRProtocol.decodeHostMessage(data(invalidHello)))
            var gate = HostSessionGate(); _ = try gate.receiveText(hello())
            XCTAssertThrowsError(try gate.receiveText(snapshot(.defaults, marker: marker)))
            XCTAssertFalse(gate.isEstablished)
        }
        var old = HostSessionGate(); _ = try old.receiveText(hello(capable: false))
        XCTAssertThrowsError(try old.receiveText(snapshot(try enhanced(), marker: nil)))
        XCTAssertFalse(old.isEstablished)
        var premature = HostSessionGate(); _ = try premature.receiveText(hello())
        XCTAssertThrowsError(try premature.receiveText(snapshot(try enhanced(), marker: false)))
        XCTAssertThrowsError(try VRProtocol.decodeHostMessage(hello(capable: false, negotiated: true)))
    }
    func testEnhancedProfileSurvivesPreferencesRecreation() throws {
        let name = "org.vrization.enhanced-tests.\(UUID().uuidString)", defaults = UserDefaults(suiteName: name)!
        defer { defaults.removePersistentDomain(forName: name) }
        var profile = PhonePreferences(); profile.hasCommittedProfile = true
        profile.settings = try enhanced(["scale": 0.61, "offsetY": 0.1, "eyeSeparation": -0.4, "fov": 95.0])
        try PhonePreferencesStore(defaults: defaults).save(profile)
        XCTAssertEqual(PhonePreferencesStore(defaults: defaults).load(), profile)
    }
}
