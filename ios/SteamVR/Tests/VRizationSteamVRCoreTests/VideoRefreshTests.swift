import XCTest
import VRizationCore
@testable import VRizationSteamVRCore

final class VideoRefreshTests: XCTestCase {
    private let session = StreamSession(epoch: 11, accepted: true, streamLayout: .sbs, inputTarget: .virtualHMD)
    private func ack(epoch: Int64 = 11, requestId: Int64 = 1, paused: Bool = false) throws -> Data {
        try JSONSerialization.data(withJSONObject: ["v": 1, "type": "videoRefresh", "epoch": epoch,
                                                   "requestId": requestId, "paused": paused])
    }
    func testRequestIsVideoOnlyAndRequiresAcceptedHMDAndSafeCounters() throws {
        let object = try JSONSerialization.jsonObject(with: SteamVRProtocol.refreshVideo(session: session, requestId: 7)) as! [String: Any]
        XCTAssertEqual(Set(object.keys), ["v", "type", "epoch", "requestId"])
        XCTAssertEqual(object["type"] as? String, "refreshVideo")
        XCTAssertNil(object["q"]); XCTAssertNil(object["editing"]); XCTAssertNil(object["arm"])
        for id in [Int64(0), -1, VRProtocol.maximumSequence + 1] {
            XCTAssertThrowsError(try SteamVRProtocol.refreshVideo(session: session, requestId: id))
        }
        for rejected in [StreamSession.legacy, StreamSession(epoch: 11, accepted: false, streamLayout: .sbs, inputTarget: .virtualHMD),
                         StreamSession(epoch: 11, accepted: true, streamLayout: .sbs, inputTarget: .mouse)] {
            XCTAssertThrowsError(try SteamVRProtocol.refreshVideo(session: rejected, requestId: 1))
        }
    }
    func testVideoGenerationBlocksPreACKAndLateDecodeWithoutChangingSession() throws {
        var gate = VideoRefreshGate(); let oldFrame = gate.frameGeneration
        _ = try gate.begin(session: session, supported: true, transportGeneration: 6, now: 100)
        let newFrame = gate.frameGeneration
        XCTAssertFalse(gate.acceptsFrames); XCTAssertFalse(gate.acceptsFrame(oldFrame)); XCTAssertFalse(gate.acceptsFrame(newFrame))
        XCTAssertEqual(try gate.acknowledge(ack(), session: session, supported: true, transportGeneration: 6, now: 101), false)
        XCTAssertTrue(gate.acceptsFrame(newFrame)); XCTAssertFalse(gate.acceptsFrame(oldFrame))
        XCTAssertEqual(session.epoch, 11); XCTAssertTrue(session.virtualHMD)
    }
    func testACKPausedIsStrictCompletedTransactionStatus() throws {
        for paused in [true, false] {
            var gate = VideoRefreshGate()
            _ = try gate.begin(session: session, supported: true, transportGeneration: 6, now: 100)
            XCTAssertEqual(try gate.acknowledge(ack(paused: paused), session: session, supported: true, transportGeneration: 6, now: 101), paused)
            XCTAssertNil(gate.pending); XCTAssertEqual(gate.lastRequestId, 1)
        }
        var good = try JSONSerialization.jsonObject(with: ack()) as! [String: Any]
        for (key, value) in [("v", true as Any), ("epoch", true as Any), ("epoch", 1.5 as Any),
                             ("requestId", 0 as Any), ("requestId", true as Any), ("paused", 1 as Any),
                             ("paused", "false" as Any)] {
            var gate = VideoRefreshGate(); _ = try gate.begin(session: session, supported: true, transportGeneration: 6, now: 100)
            var object = good; object[key] = value
            XCTAssertThrowsError(try gate.acknowledge(JSONSerialization.data(withJSONObject: object), session: session,
                supported: true, transportGeneration: 6, now: 101))
            XCTAssertFalse(gate.acceptsFrames)
        }
        good.removeValue(forKey: "paused")
        var gate = VideoRefreshGate(); _ = try gate.begin(session: session, supported: true, transportGeneration: 6, now: 100)
        XCTAssertThrowsError(try gate.acknowledge(JSONSerialization.data(withJSONObject: good), session: session,
            supported: true, transportGeneration: 6, now: 101))
    }
    func testACKIgnoresAdditionalServerFieldsWithoutAuthorizingResume() throws {
        var gate = VideoRefreshGate()
        _ = try gate.begin(session: session, supported: true, transportGeneration: 6, now: 100)
        var object = try JSONSerialization.jsonObject(with: ack(paused: true)) as! [String: Any]
        object["futureField"] = ["resume": true]
        XCTAssertEqual(try gate.acknowledge(JSONSerialization.data(withJSONObject: object), session: session,
            supported: true, transportGeneration: 6, now: 101), true)
        XCTAssertNil(gate.pending); XCTAssertEqual(session.epoch, 11)
    }
    func testStaleEpochRequestAndTransportACKNeverOpenVideo() throws {
        var gate = VideoRefreshGate(); _ = try gate.begin(session: session, supported: true, transportGeneration: 6, now: 100)
        XCTAssertNil(try gate.acknowledge(ack(epoch: 10), session: session, supported: true, transportGeneration: 6, now: 101))
        XCTAssertNil(try gate.acknowledge(ack(requestId: 2), session: session, supported: true, transportGeneration: 6, now: 101))
        XCTAssertNil(try gate.acknowledge(ack(), session: session, supported: true, transportGeneration: 7, now: 101))
        XCTAssertFalse(gate.acceptsFrames)
        _ = try gate.acknowledge(ack(), session: session, supported: true, transportGeneration: 6, now: 101)
        _ = try gate.begin(session: session, supported: true, transportGeneration: 6, now: 110)
        XCTAssertEqual(gate.lastRequestId, 2)
        XCTAssertNil(try gate.acknowledge(ack(), session: session, supported: true, transportGeneration: 6, now: 111))
        XCTAssertFalse(gate.acceptsFrames)
        _ = try gate.acknowledge(ack(requestId: 2), session: session, supported: true, transportGeneration: 6, now: 111)
        XCTAssertTrue(gate.acceptsFrames)
    }
    func testCancelForLifecycleOrDisconnectInvalidatesFramesAndPendingDeadline() throws {
        var gate = VideoRefreshGate(); _ = try gate.begin(session: session, supported: true, transportGeneration: 6, now: 100)
        let oldFrame = gate.frameGeneration
        gate.cancel(); XCTAssertNil(gate.pending); XCTAssertFalse(gate.acceptsFrame(oldFrame))
        XCTAssertFalse(gate.expired(now: 200, transportGeneration: 6))
        XCTAssertNil(try gate.acknowledge(ack(), session: session, supported: true, transportGeneration: 6, now: 101))
        _ = try gate.begin(session: session, supported: true, transportGeneration: 7, now: 200)
        XCTAssertEqual(gate.pending?.requestId, 2)
        XCTAssertNil(try gate.acknowledge(ack(), session: session, supported: true, transportGeneration: 7, now: 201))
        XCTAssertFalse(gate.acceptsFrames)
    }
    func testEightSecondDeadlineRemainsClosedUntilFallbackOrACK() throws {
        var gate = VideoRefreshGate(); _ = try gate.begin(session: session, supported: true, transportGeneration: 6, now: 100)
        XCTAssertFalse(gate.expired(now: 107.999, transportGeneration: 6))
        XCTAssertTrue(gate.expired(now: 108, transportGeneration: 6))
        XCTAssertFalse(gate.expired(now: 108, transportGeneration: 7))
        XCTAssertFalse(gate.expired(now: .nan, transportGeneration: 6))
        XCTAssertNil(try gate.acknowledge(ack(), session: session, supported: true, transportGeneration: 6, now: 108))
        XCTAssertFalse(gate.acceptsFrames)
        XCTAssertThrowsError(try gate.begin(session: session, supported: true, transportGeneration: 6, now: 110))
        XCTAssertEqual(gate.lastRequestId, 1)
    }
    func testOldOrDirectHostCannotBeginOrAcknowledgeLiveRefresh() throws {
        var gate = VideoRefreshGate()
        XCTAssertThrowsError(try gate.begin(session: session, supported: false, transportGeneration: 6, now: 100))
        XCTAssertEqual(gate.lastRequestId, 0); XCTAssertEqual(gate.frameGeneration, 0)
        _ = try gate.begin(session: session, supported: true, transportGeneration: 6, now: 100)
        XCTAssertThrowsError(try gate.acknowledge(ack(), session: session, supported: false, transportGeneration: 6, now: 101))
        XCTAssertThrowsError(try gate.acknowledge(ack(), session: .legacy, supported: true, transportGeneration: 6, now: 101))
        XCTAssertThrowsError(try gate.acknowledge(ack(), session: nil, supported: true, transportGeneration: 6, now: 101))
        XCTAssertFalse(gate.acceptsFrames)
    }
    func testOrdinaryConnectionDoesNotCarryRefreshIntent() {
        var intent = RefreshReconnectIntent()
        XCTAssertFalse(intent.consume(transportGeneration: 6, handshakeComplete: true,
            session: session, supported: true))
        XCTAssertNil(intent.transportGeneration)
    }
    func testRefreshIntentWaitsForCompleteAcceptedHandshakeAndConsumesOnce() {
        var intent = RefreshReconnectIntent(); intent.arm(transportGeneration: 6)
        XCTAssertFalse(intent.consume(transportGeneration: 6, handshakeComplete: false,
            session: nil, supported: true))
        XCTAssertEqual(intent.transportGeneration, 6)
        XCTAssertTrue(intent.consume(transportGeneration: 6, handshakeComplete: true,
            session: session, supported: true))
        XCTAssertNil(intent.transportGeneration)
        XCTAssertFalse(intent.consume(transportGeneration: 6, handshakeComplete: true,
            session: session, supported: true))
    }
    func testLateHandshakeCannotConsumeNewerRefreshIntent() {
        var intent = RefreshReconnectIntent(); intent.arm(transportGeneration: 7)
        XCTAssertFalse(intent.consume(transportGeneration: 6, handshakeComplete: true,
            session: session, supported: true))
        XCTAssertEqual(intent.transportGeneration, 7)
        XCTAssertTrue(intent.consume(transportGeneration: 7, handshakeComplete: true,
            session: session, supported: true))
    }
    func testRefreshIntentNeverResumesLegacyMouseUnacceptedOrUnsupportedPeer() {
        let rejected = [StreamSession.legacy,
            StreamSession(epoch: 11, accepted: false, streamLayout: .sbs, inputTarget: .virtualHMD),
            StreamSession(epoch: 11, accepted: true, streamLayout: .sbs, inputTarget: .mouse)]
        for candidate in rejected {
            var intent = RefreshReconnectIntent(); intent.arm(transportGeneration: 6)
            XCTAssertFalse(intent.consume(transportGeneration: 6, handshakeComplete: true,
                session: candidate, supported: true))
            XCTAssertNil(intent.transportGeneration)
        }
        var intent = RefreshReconnectIntent(); intent.arm(transportGeneration: 6)
        XCTAssertFalse(intent.consume(transportGeneration: 6, handshakeComplete: true,
            session: session, supported: false))
        XCTAssertNil(intent.transportGeneration)
    }
    func testStopLifecycleOrEditorCancelsReconnectRefreshIntent() {
        var intent = RefreshReconnectIntent(); intent.arm(transportGeneration: 6)
        intent.cancel()
        XCTAssertFalse(intent.consume(transportGeneration: 6, handshakeComplete: true,
            session: session, supported: true))
        intent.arm(transportGeneration: 7)
        XCTAssertTrue(intent.consume(transportGeneration: 7, handshakeComplete: true,
            session: session, supported: true))
        // Consuming does not re-arm itself on a timeout or another snapshot.
        XCTAssertFalse(intent.consume(transportGeneration: 7, handshakeComplete: true,
            session: session, supported: true))
    }
}
