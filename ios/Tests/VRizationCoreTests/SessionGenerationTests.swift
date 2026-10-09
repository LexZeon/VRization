import XCTest
import Dispatch
@testable import VRizationCore

final class SessionGenerationTests: XCTestCase {
    func testReconnectRejectsQueuedCallbackAtExecutionTime() {
        let owner = DispatchQueue(label: "test.session.owner")
        let gate = SessionGeneration()
        let old = gate.invalidate()
        let blocker = DispatchSemaphore(value: 0)
        owner.async { blocker.wait() }
        var staleExecuted = false
        gate.dispatch(on: owner, generation: old) { staleExecuted = true }
        let next = gate.invalidate()
        let current = expectation(description: "Current callback executes")
        gate.dispatch(on: owner, generation: next) { current.fulfill() }
        blocker.signal()
        wait(for: [current], timeout: 5)
        owner.sync { XCTAssertFalse(staleExecuted) }
        XCTAssertFalse(gate.isCurrent(old)); XCTAssertTrue(gate.isCurrent(next))
    }
    func testClosePermanentlyRejectsEvenNewGeneration() {
        let gate = SessionGeneration()
        let old = gate.invalidate(); gate.close()
        XCTAssertFalse(gate.isCurrent(old))
        XCTAssertFalse(gate.isCurrent(gate.invalidate()))
    }
    func testInvalidationIsThreadSafeAndNeverReusesGeneration() {
        let gate = SessionGeneration()
        let collectionLock = NSLock()
        var values = Set<UInt64>()
        DispatchQueue.concurrentPerform(iterations: 100) { _ in
            let value = gate.invalidate()
            collectionLock.lock(); values.insert(value); collectionLock.unlock()
        }
        XCTAssertEqual(values.count, 100)
        XCTAssertEqual(gate.current, 100)
    }
}
