import XCTest
import VRizationCore
@testable import VRizationSteamVRCore

final class SteamVRCoreTests: XCTestCase {
    private let caps = Set(["enhanced-first-person", "stabilization", "stereo-sbs", "hmd-orientation"])
    private var session: [String: Any] { ["v": 1, "epoch": 11, "accepted": true, "streamLayout": "sbs", "inputTarget": "virtual-hmd"] }
    private func data(_ object: [String: Any]) throws -> Data { try JSONSerialization.data(withJSONObject: object) }
    private func settings(_ settings: VRSettings = .defaults) throws -> [String: Any] {
        try JSONSerialization.jsonObject(with: JSONEncoder().encode(settings)) as! [String: Any]
    }
    private func hello(accepted: Bool = false, legacy: Bool = false) throws -> Data {
        var object: [String: Any] = ["v": 1, "type": "hello", "name": "VRization", "version": "0.5.0",
            "mouseArmed": false, "revision": 1, "stream": ["codec": "jpeg", "fps": 60, "maxWidth": 1920],
            "settings": try settings()]
        if !legacy {
            var descriptor = session; descriptor["accepted"] = accepted
            object["capabilities"] = Array(caps); object["streamSession"] = descriptor; object["enhancedFirstPerson"] = true
        }
        return try data(object)
    }
    private func snapshot(_ descriptor: [String: Any]? = nil, complete: Bool = true, seq: Int? = nil) throws -> Data {
        let body: [String: Any]
        if complete { body = try settings() } else { body = ["scale": 0.7] }
        var object: [String: Any] = ["v": 1, "type": "settings", "revision": 2,
            "settings": body,
            "enhancedFirstPerson": true, "streamSession": descriptor ?? session]
        if let seq = seq { object["clientSeq"] = seq }
        return try data(object)
    }
    private func acceptedGate() throws -> SteamVRSessionGate {
        var gate = SteamVRSessionGate()
        _ = try gate.receiveText(hello())
        _ = try gate.receiveText(snapshot())
        return gate
    }
    private func assertQuaternion(_ actual: HMDQuaternion, _ expected: [Double], file: StaticString = #file, line: UInt = #line) {
        for (a, e) in zip(actual.xyzw, expected) { XCTAssertEqual(a, e, accuracy: 1e-10, file: file, line: line) }
    }
    private func assertMatrix(_ actual: [Double], _ expected: [Double], file: StaticString = #file, line: UInt = #line) {
        for (a, e) in zip(actual, expected) { XCTAssertEqual(a, e, accuracy: 1e-10, file: file, line: line) }
    }

    func testGateWaitsFullAuthoritativeAcceptanceNotHelloOrPartialACK() throws {
        var gate = SteamVRSessionGate()
        _ = try gate.receiveText(hello(accepted: true))
        XCTAssertTrue(gate.isEstablished); XCTAssertTrue(gate.awaitingSettingsSnapshot)
        XCTAssertNil(gate.descriptor); XCTAssertFalse(gate.canReceiveFrames); XCTAssertFalse(gate.acceptsHMDPose)
        _ = try gate.receiveText(snapshot(complete: false))
        _ = try gate.receiveText(snapshot(seq: 3))
        XCTAssertTrue(gate.awaitingSettingsSnapshot); XCTAssertNil(gate.descriptor)
        _ = try gate.receiveText(snapshot())
        XCTAssertFalse(gate.awaitingSettingsSnapshot); XCTAssertTrue(gate.canReceiveFrames); XCTAssertTrue(gate.acceptsHMDPose)
        XCTAssertEqual(gate.descriptor?.epoch, 11)
    }
    func testFalseThenTrueOnlyAcceptanceUpgradeDoesNotAttachPrematureLayout() throws {
        var gate = SteamVRSessionGate()
        _ = try gate.receiveText(hello())
        var descriptor = session; descriptor["accepted"] = false
        _ = try gate.receiveText(snapshot(descriptor))
        XCTAssertNil(gate.descriptor); XCTAssertFalse(gate.canReceiveFrames)
        _ = try gate.receiveText(snapshot())
        XCTAssertTrue(gate.canReceiveFrames)
    }
    func testDescriptorChangePoisonsGateUntilReconnect() throws {
        for (key, value) in [("epoch", 12 as Any), ("accepted", false as Any), ("inputTarget", "mouse" as Any)] {
            var gate = try acceptedGate(); var descriptor = session; descriptor[key] = value
            XCTAssertThrowsError(try gate.receiveText(snapshot(descriptor))) { XCTAssertEqual($0 as? SteamVRSessionError, .changed) }
            XCTAssertNil(gate.descriptor); XCTAssertFalse(gate.canReceiveFrames)
            XCTAssertThrowsError(try gate.receiveText(snapshot()))
            gate.reset(); _ = try gate.receiveText(hello()); _ = try gate.receiveText(snapshot())
            XCTAssertTrue(gate.canReceiveFrames)
        }
    }
    func testWrongPendingEpochRequiresReconnectBeforeAnyFrame() throws {
        var gate = SteamVRSessionGate(); _ = try gate.receiveText(hello())
        var descriptor = session; descriptor["epoch"] = 12
        XCTAssertThrowsError(try gate.receiveText(snapshot(descriptor)))
        XCTAssertFalse(gate.canReceiveFrames)
    }
    func testEveryCapableSettingsMustCarryDescriptor() throws {
        var gate = try acceptedGate()
        let object: [String: Any] = ["v": 1, "type": "settings", "settings": ["scale": 0.7]]
        XCTAssertThrowsError(try gate.receiveText(data(object)))
        XCTAssertFalse(gate.canReceiveFrames)
    }
    func testLegacyPeerIsMonoMouseAndCannotLaterInjectStereo() throws {
        var gate = SteamVRSessionGate(); _ = try gate.receiveText(hello(legacy: true))
        XCTAssertEqual(gate.descriptor, .legacy); XCTAssertTrue(gate.canReceiveFrames); XCTAssertFalse(gate.acceptsHMDPose)
        XCTAssertThrowsError(try gate.receiveText(snapshot()))
    }
    func testDescriptorRejectsMalformedTypesAndMissingCapabilities() throws {
        for (key, value) in [("epoch", true as Any), ("epoch", 0 as Any), ("epoch", 1.1 as Any),
                             ("accepted", 1 as Any), ("v", true as Any), ("streamLayout", "side-by-side" as Any),
                             ("inputTarget", "gamepad" as Any)] {
            var object = session; object[key] = value
            XCTAssertThrowsError(try StreamSession.decode(object, capabilities: caps))
        }
        XCTAssertThrowsError(try StreamSession.decode(session, capabilities: ["stereo-sbs"]))
        XCTAssertThrowsError(try StreamSession.decode(session, capabilities: ["hmd-orientation"]))
        var monoHMD = session; monoHMD["streamLayout"] = "mono"
        XCTAssertThrowsError(try StreamSession.decode(monoHMD, capabilities: caps))
        var extra = session; extra["unknown"] = true
        XCTAssertThrowsError(try StreamSession.decode(extra, capabilities: caps))
    }
    func testFrameCallbacksAreBoundToTransportGenerationAndDescriptor() throws {
        var gate = try acceptedGate(); let old = gate.descriptor
        XCTAssertTrue(gate.acceptsFrame(generation: 6, activeGeneration: 6, captured: old))
        XCTAssertFalse(gate.acceptsFrame(generation: 5, activeGeneration: 6, captured: old))
        XCTAssertFalse(gate.acceptsFrame(generation: 6, activeGeneration: 6, captured: .legacy))
        gate.reset()
        XCTAssertFalse(gate.acceptsFrame(generation: 6, activeGeneration: 6, captured: old))
    }
    func testMalformedJPEGInvalidatesAcceptedDescriptorAndLateFrames() throws {
        var gate = try acceptedGate(); let old = gate.descriptor
        XCTAssertThrowsError(try gate.receiveJPEG(byteCount: HostSessionGate.maximumJPEGBytes + 1))
        XCTAssertNil(gate.descriptor); XCTAssertFalse(gate.isEstablished)
        XCTAssertFalse(gate.acceptsFrame(generation: 6, activeGeneration: 6, captured: old))
        XCTAssertThrowsError(try gate.receiveText(snapshot()))
    }
    func testStereoHalfAspectAndHalfTexelClampNeverCrossEyes() throws {
        let left = try StereoEyeSampling.resolve(width: 1920, height: 1080, eye: 0, layout: .sbs)
        let right = try StereoEyeSampling.resolve(width: 1920, height: 1080, eye: 1, layout: .sbs)
        XCTAssertEqual(left.contentAspect, 960.0/1080, accuracy: 1e-12)
        XCTAssertEqual(right.contentAspect, left.contentAspect)
        XCTAssertLessThan(try left.uv(FitPoint(x: 1, y: 0.5)).x, 0.5)
        XCTAssertGreaterThan(try right.uv(FitPoint(x: 0, y: 0.5)).x, 0.5)
        XCTAssertEqual(try left.uv(FitPoint(x: 3, y: 0)).x, 0.5 - 0.5/1920, accuracy: 1e-12)
        XCTAssertEqual(try right.uv(FitPoint(x: -3, y: 1)).x, 0.5 + 0.5/1920, accuracy: 1e-12)
        XCTAssertThrowsError(try StereoEyeSampling.resolve(width: 1919, height: 1080, eye: 0, layout: .sbs))
        XCTAssertThrowsError(try StereoEyeSampling.resolve(width: 1920, height: 0, eye: 1, layout: .sbs))
    }
    func testMonoSamplingAndSBSProjectionBypassPreserveUserMode() throws {
        let mono = try StereoEyeSampling.resolve(width: 1280, height: 720, eye: 1, layout: .mono)
        XCTAssertEqual(mono.contentAspect, 16.0/9)
        for mode in ["full", "cinema", "fps", "fps_enhanced"] {
            var profile = VRSettings(); profile.mode = mode; profile.distortion = 0.3
            XCTAssertEqual(SteamVRGeometry.renderSettings(profile, layout: .mono), profile)
            let stereo = SteamVRGeometry.renderSettings(profile, layout: .sbs)
            XCTAssertEqual(stereo.mode, "full"); XCTAssertEqual(stereo.distortion, 0.3)
            XCTAssertEqual(SteamVRGeometry.restoringMode(stereo, from: profile), profile)
            let rect = try HeadsetFit.eyeRect(settings: stereo, imageAspect: 0.5, eyeAspect: 1, eyeSign: -1)
            XCTAssertEqual(rect.halfSize.x / rect.halfSize.y, 0.5, accuracy: 1e-12)
        }
    }
    func testQuaternionAxesAndCompoundIndependentGolden() throws {
        let half = sqrt(0.5)
        assertQuaternion(try HMDQuaternion.fromRotation(PoseMath.rotation(yaw: .pi/2, pitch: 0, roll: 0)), [0,-half,0,half])
        assertQuaternion(try HMDQuaternion.fromRotation(PoseMath.rotation(yaw: 0, pitch: .pi/2, roll: 0)), [half,0,0,half])
        assertQuaternion(try HMDQuaternion.fromRotation(PoseMath.rotation(yaw: 0, pitch: 0, roll: .pi/2)), [0,0,-half,half])
        assertQuaternion(try HMDQuaternion.fromRotation(PoseMath.rotation(yaw: 0.7, pitch: -0.4, roll: 0.9)),
            [-0.021869850273803754,-0.3837819133455947,-0.4617914702766405,0.7993633658215358])
    }
    func testQuaternionNonIdentityTiltRecenterUsesFullMatrix() throws {
        var center = HMDQuaternionCenter()
        let origin = try PoseMath.rotation(yaw: 0.3, pitch: 0.5, roll: -0.2)
        XCTAssertEqual(try center.sample(screenToWorld: origin), .identity)
        let relative = try PoseMath.rotation(yaw: 0.7, pitch: -0.4, roll: 0.9)
        let current = try PoseMath.multiply(origin, relative)
        assertQuaternion(try center.sample(screenToWorld: current),
            [-0.021869850273803754,-0.3837819133455947,-0.4617914702766405,0.7993633658215358])
        center.recenter(); XCTAssertEqual(try center.sample(screenToWorld: current), .identity)
    }
    func testQuaternionBothLandscapeBasesPreserveSameRelativeWorldAxes() throws {
        for left in [false, true] {
            let basis: [Double] = left ? [0,-1,0,1,0,0,0,0,1] : [0,1,0,-1,0,0,0,0,1]
            let screen = try PoseMath.rotation(yaw: 0.7, pitch: -0.4, roll: 0.9)
            let device = try PoseMath.multiply(basis, PoseMath.transpose(screen))
            let recovered = try PoseMath.screenToWorld(referenceToDevice: device, landscapeLeft: left)
            assertMatrix(recovered, screen)
            assertQuaternion(try HMDQuaternion.fromRotation(recovered),
                [-0.021869850273803754,-0.3837819133455947,-0.4617914702766405,0.7993633658215358])
        }
    }
    func testQuaternionAllHalfTurnBranchesAreFiniteAndUnit() throws {
        let matrices: [[Double]] = [[1,0,0,0,-1,0,0,0,-1],[-1,0,0,0,1,0,0,0,-1],[-1,0,0,0,-1,0,0,0,1]]
        for matrix in matrices {
            let q = try HMDQuaternion.fromRotation(matrix)
            _ = try q.validated(); assertMatrix(try q.matrix(), matrix)
        }
    }
    func testQuaternionSignContinuityAcrossPiAndInvalidSamplesDoNotRecenter() throws {
        var center = HMDQuaternionCenter()
        _ = try center.sample(screenToWorld: PoseMath.rotation(yaw: 0, pitch: 0, roll: 0))
        let before = try center.sample(screenToWorld: PoseMath.rotation(yaw: .pi - 0.01, pitch: 0, roll: 0))
        XCTAssertThrowsError(try center.sample(screenToWorld: Array(repeating: 0, count: 9)))
        let after = try center.sample(screenToWorld: PoseMath.rotation(yaw: .pi + 0.01, pitch: 0, roll: 0))
        XCTAssertGreaterThan(before.dot(after), 0.99)
        XCTAssertLessThan(after.y, 0); XCTAssertLessThan(after.w, 0)
        XCTAssertThrowsError(try HMDQuaternion(x: .nan, y: 0, z: 0, w: 1).validated())
        XCTAssertThrowsError(try HMDQuaternion(x: 0, y: 0, z: 0, w: 0).validated())
        XCTAssertThrowsError(try HMDQuaternion.fromRotation([1,0,0,0,1,0,0,0,-1]))
    }
    func testHMDWireIsFullQuaternionNoEulerMouseAndInvalidTrackingOmitsQ() throws {
        let accepted = try StreamSession.decode(session, capabilities: caps)
        let q = try HMDQuaternion.fromRotation(PoseMath.rotation(yaw: 0.7, pitch: -0.4, roll: 0.9))
        let object = try JSONSerialization.jsonObject(with: SteamVRProtocol.hmdPose(session: accepted,
            sequence: 7, timeUs: 123456, quaternion: q)) as! [String: Any]
        XCTAssertEqual(Set(object.keys), ["v","type","epoch","seq","timeUs","trackingValid","q"])
        XCTAssertEqual(object["type"] as? String, "hmdPose")
        // JSONSerialization may round a Double by a few ULPs in decimal text.
        let decodedQ = try XCTUnwrap(object["q"] as? [Double])
        XCTAssertEqual(decodedQ.count, 4)
        for (actual, expected) in zip(decodedQ, q.xyzw) { XCTAssertEqual(actual, expected, accuracy: 1e-12) }
        XCTAssertEqual(decodedQ.reduce(0) { $0 + $1*$1 }, 1, accuracy: 1e-12)
        XCTAssertNil(object["yaw"]); XCTAssertNil(object["pitch"])
        let lost = try JSONSerialization.jsonObject(with: SteamVRProtocol.hmdPose(session: accepted,
            sequence: 8, timeUs: 123457, quaternion: nil)) as! [String: Any]
        XCTAssertEqual(lost["trackingValid"] as? Bool, false); XCTAssertNil(lost["q"])
        XCTAssertThrowsError(try SteamVRProtocol.hmdPose(session: .legacy, sequence: 9, timeUs: 1, quaternion: q))
        XCTAssertThrowsError(try SteamVRProtocol.hmdPose(session: accepted, sequence: 0, timeUs: 1, quaternion: q))
        XCTAssertThrowsError(try SteamVRProtocol.hmdPose(session: accepted, sequence: 9, timeUs: -1, quaternion: q))
    }
    func testRecenterAndEditingHelloDoNotGrantInputOrResetSequence() throws {
        let object = try JSONSerialization.jsonObject(with: SteamVRProtocol.hello(editing: true)) as! [String: Any]
        XCTAssertEqual(Set(object.keys), ["v","type","settingsSchema","capabilities","editing"])
        XCTAssertEqual(object["capabilities"] as? [String], SteamVRProtocol.capabilities)
        XCTAssertEqual(object["editing"] as? Bool, true); XCTAssertNil(object["arm"])
        let recenter = try JSONSerialization.jsonObject(with: SteamVRProtocol.recenter(epoch: 11)) as! [String: Any]
        XCTAssertEqual(Set(recenter.keys), ["v","type","epoch"]); XCTAssertNil(recenter["seq"])
        XCTAssertThrowsError(try SteamVRProtocol.recenter(epoch: 0))
    }
    func testPreviewPreferencesAreSeparateAndNeverPersistDescriptorOrCode() throws {
        let suite = "SteamVRCoreTests-\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let stable = PhonePreferencesStore(defaults: defaults), preview = SteamVRPreferencesStore(defaults: defaults)
        var stableProfile = PhonePreferences(); stableProfile.port = "8765"; stableProfile.settings.scale = 0.91
        try stable.save(stableProfile)
        XCTAssertEqual(preview.load().port, "8766"); XCTAssertEqual(preview.load().settings.scale, 0.85)
        var profile = preview.load(); profile.settings.mode = "fps_enhanced"; profile.settings.scale = 0.7
        try preview.save(profile)
        XCTAssertEqual(stable.load(), stableProfile); XCTAssertEqual(preview.load(), profile)
        let raw = try XCTUnwrap(defaults.data(forKey: SteamVRPreferencesStore.key))
        let object = try JSONSerialization.jsonObject(with: raw) as! [String: Any]
        XCTAssertNil(object["streamSession"]); XCTAssertNil(object["code"]); XCTAssertNil(object["token"])
        try preview.reset(); XCTAssertEqual(preview.load().port, "8766"); XCTAssertEqual(stable.load(), stableProfile)
    }
    func testExactStereoRasterRejectsThumbnailOrRotatedPackedInputs() throws {
        XCTAssertNoThrow(try StereoRaster.validate(width: 1280, height: 480))
        XCTAssertNoThrow(try StereoRaster.validate(width: 2048, height: 2048))
        for (width,height,orientation) in [(1281,480,1),(4096,1024,1),(1280,4096,1),(1280,480,6),(0,480,1)] {
            XCTAssertThrowsError(try StereoRaster.validate(width: width, height: height, orientation: orientation))
        }
    }
    func testProductionHMDSequencerStaysContinuousAcrossLocalRecenterAndInvalidSamples() throws {
        let accepted = try StreamSession.decode(session, capabilities: caps)
        var sequencer = HMDPoseSequencer()
        let first = try sequencer.encode(session: accepted, timeUs: 10, quaternion: .identity)
        XCTAssertEqual(try (JSONSerialization.jsonObject(with: first) as! [String: Any])["seq"] as? Int, 1)
        _ = try sequencer.recenter(session: accepted)
        XCTAssertEqual(sequencer.lastSequence, 1)
        let second = try sequencer.encode(session: accepted, timeUs: 11, quaternion: nil)
        XCTAssertEqual(try (JSONSerialization.jsonObject(with: second) as! [String: Any])["seq"] as? Int, 2)
        XCTAssertThrowsError(try sequencer.encode(session: accepted, timeUs: 12, quaternion: HMDQuaternion(x: 0,y: 0,z: 0,w: 0)))
        XCTAssertEqual(sequencer.lastSequence, 2)
        XCTAssertThrowsError(try sequencer.encode(session: .legacy, timeUs: 13, quaternion: .identity))
        XCTAssertEqual(sequencer.lastSequence, 2)
    }
}
