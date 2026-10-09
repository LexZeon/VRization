import XCTest
@testable import VRizationCore

final class SettingsSyncTests: XCTestCase {
    func testOlderAcknowledgmentCannotUndoNewerSliderSnapshot() throws {
        var sync = SettingsSync()
        let old = try VRSettings().applying(["scale": 0.6])
        let latest = try old.applying(["scale": 0.9])
        sync.edited(); let seq1 = try sync.nextSequence(); try sync.sent(sequence: seq1, snapshot: old)
        sync.edited(); let seq2 = try sync.nextSequence(); try sync.sent(sequence: seq2, snapshot: latest)
        XCTAssertFalse(sync.accept(snapshot: old, revision: 1, clientSeq: seq1))
        XCTAssertTrue(sync.accept(snapshot: latest, revision: 2, clientSeq: seq2))
        XCTAssertFalse(sync.accept(snapshot: old, revision: 1, clientSeq: nil))
    }
    func testActiveGestureAndUnsentEditProtectLocalValue() throws {
        var sync = SettingsSync()
        sync.beginGesture(); sync.edited()
        let sequence = try sync.nextSequence(); try sync.sent(sequence: sequence, snapshot: VRSettings())
        XCTAssertFalse(sync.accept(snapshot: VRSettings(), revision: 2, clientSeq: sequence))
        sync.edited(); sync.endGesture()
        XCTAssertFalse(sync.accept(snapshot: VRSettings(), revision: 3, clientSeq: nil))
        let final = try VRSettings().applying(["offsetX": 0.3])
        let finalSequence = try sync.nextSequence(); try sync.sent(sequence: finalSequence, snapshot: final)
        XCTAssertTrue(sync.accept(snapshot: final, revision: 4, clientSeq: finalSequence))
    }
    func testEqualRevisionCanAcknowledgeLatestCoalescedSend() throws {
        var sync = SettingsSync()
        let first = try sync.nextSequence(); try sync.sent(sequence: first, snapshot: VRSettings())
        let last = try sync.nextSequence(); try sync.sent(sequence: last, snapshot: VRSettings())
        XCTAssertFalse(sync.accept(snapshot: VRSettings(), revision: 8, clientSeq: first))
        XCTAssertTrue(sync.accept(snapshot: VRSettings(), revision: 8, clientSeq: last))
        XCTAssertFalse(sync.awaitingAcknowledgment)
        XCTAssertFalse(sync.accept(snapshot: VRSettings(), revision: 9, clientSeq: last + 1))
    }
    func testUnsolicitedBroadcastWaitsForPendingAckAndLegacyUsesExactSnapshot() throws {
        var sync = SettingsSync()
        let snapshot = try VRSettings().applying(["mode": "cinema"])
        let sequence = try sync.nextSequence(); try sync.sent(sequence: sequence, snapshot: snapshot)
        XCTAssertFalse(sync.accept(snapshot: VRSettings(), revision: 1, clientSeq: nil))
        XCTAssertFalse(sync.accept(snapshot: VRSettings(), revision: nil, clientSeq: nil))
        XCTAssertTrue(sync.accept(snapshot: snapshot, revision: nil, clientSeq: nil))
        XCTAssertFalse(sync.awaitingAcknowledgment)
    }
    func testReconnectClearsInterruptedGestureAndRevision() throws {
        var sync = SettingsSync()
        sync.beginGesture(); sync.edited()
        XCTAssertFalse(sync.accept(snapshot: VRSettings(), revision: 10, clientSeq: nil))
        sync.newSession()
        XCTAssertTrue(sync.accept(snapshot: VRSettings(), revision: 0, clientSeq: nil))
        XCTAssertEqual(try sync.nextSequence(), 1)
    }
    func testSendRequiresAllocatedMonotonicSequence() throws {
        var sync = SettingsSync()
        XCTAssertThrowsError(try sync.sent(sequence: 1, snapshot: VRSettings()))
        let seq = try sync.nextSequence(); try sync.sent(sequence: seq, snapshot: VRSettings())
        XCTAssertThrowsError(try sync.sent(sequence: seq, snapshot: VRSettings()))
    }
    func testUnknownFutureAckAndStaleRevisionDoNotClearPendingSend() throws {
        var sync = SettingsSync()
        let sequence = try sync.nextSequence(); try sync.sent(sequence: sequence, snapshot: VRSettings())
        XCTAssertFalse(sync.accept(snapshot: VRSettings(), revision: 99, clientSeq: sequence + 1))
        XCTAssertEqual(sync.highestRevision, -1)
        XCTAssertTrue(sync.awaitingAcknowledgment)
        XCTAssertFalse(sync.accept(snapshot: VRSettings(), revision: 5, clientSeq: nil))
        XCTAssertFalse(sync.accept(snapshot: VRSettings(), revision: 4, clientSeq: sequence))
        XCTAssertTrue(sync.awaitingAcknowledgment)
        XCTAssertTrue(sync.accept(snapshot: VRSettings(), revision: 5, clientSeq: sequence))
        XCTAssertFalse(sync.awaitingAcknowledgment)
    }
}
