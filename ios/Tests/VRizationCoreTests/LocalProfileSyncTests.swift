import XCTest
@testable import VRizationCore

final class LocalProfileSyncTests: XCTestCase {
    func testValidatedHelloRestoresLocalOnceInsteadOfApplyingHostDefaults() throws {
        var session = LocalProfileSync(); session.newSession(hasSavedProfile: true)
        let local = try VRSettings().applying(["scale": 0.61])
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 8, clientSeq: nil), .restoreLocal)
        session.edited(); let seq = try session.nextSequence(); try session.sent(sequence: seq, snapshot: local)
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 8, clientSeq: nil), .ignore)
        XCTAssertEqual(session.receive(snapshot: local, revision: 9, clientSeq: seq), .applyHost)
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 10, clientSeq: nil), .applyHost)
    }
    func testLateAckCannotOverwriteNewSave() throws {
        var session = LocalProfileSync(); session.newSession(hasSavedProfile: true)
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 0, clientSeq: nil), .restoreLocal)
        let first = try session.nextSequence(); try session.sent(sequence: first, snapshot: .defaults)
        let saved = try VRSettings().applying(["scale": 0.66, "offsetY": 0.1])
        session.beginPreview()
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 1, clientSeq: first), .ignore)
        session.endPreview(); session.edited()
        let final = try session.nextSequence(); try session.sent(sequence: final, snapshot: saved)
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 2, clientSeq: first), .ignore)
        XCTAssertEqual(session.receive(snapshot: saved, revision: 3, clientSeq: final), .applyHost)
    }
    func testPreviewDoesNotSendOrAllocateSequencesAndNewSessionCancelsIt() throws {
        var session = LocalProfileSync(); session.newSession(hasSavedProfile: true)
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 0, clientSeq: nil), .restoreLocal)
        session.beginPreview(); XCTAssertTrue(session.previewing)
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 1, clientSeq: nil), .ignore)
        session.endPreview(); XCTAssertFalse(session.previewing)
        XCTAssertEqual(try session.nextSequence(), 1)
        session.beginPreview(); session.newSession(hasSavedProfile: true); XCTAssertFalse(session.previewing)
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 0, clientSeq: nil), .restoreLocal)
    }
    func testInvalidHelloOrFutureAckCannotConsumeRestoration() {
        var session = LocalProfileSync(); session.newSession(hasSavedProfile: true)
        var invalid = VRSettings(); invalid.scale = .nan
        XCTAssertEqual(session.receive(snapshot: invalid, revision: 0, clientSeq: nil), .ignore)
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 0, clientSeq: 1), .ignore)
        XCTAssertEqual(session.receive(snapshot: .defaults, revision: 0, clientSeq: nil), .restoreLocal)
    }
    func testFreshInstallationUsesHostSnapshotInsteadOfOverridingIt() throws {
        var session = LocalProfileSync(); session.newSession(hasSavedProfile: false)
        let host = try VRSettings().applying(["scale": 0.62])
        XCTAssertEqual(session.receive(snapshot: host, revision: 0, clientSeq: nil), .applyHost)
        XCTAssertEqual(session.receive(snapshot: host, revision: 1, clientSeq: nil), .applyHost)
    }
}
