import Foundation
import Dispatch

/// Invalidates old network/decode callbacks; mutations and callback effects still belong
/// on the same owner queue. dispatch rechecks identity when that queue actually executes.
public final class SessionGeneration {
    private let lock = NSLock()
    private var generation: UInt64 = 0
    private var closed = false
    public init() {}
    public var current: UInt64 {
        lock.lock(); defer { lock.unlock() }
        return generation
    }
    @discardableResult public func invalidate() -> UInt64 {
        lock.lock(); defer { lock.unlock() }
        generation &+= 1
        return generation
    }
    public func isCurrent(_ value: UInt64) -> Bool {
        lock.lock(); defer { lock.unlock() }
        return !closed && value == generation
    }
    public func dispatch(on owner: DispatchQueue, generation value: UInt64, action: @escaping () -> Void) {
        owner.async { [weak self] in
            guard self?.isCurrent(value) == true else { return }
            action()
        }
    }
    public func close() {
        lock.lock(); defer { lock.unlock() }
        closed = true
        generation &+= 1
    }
}
