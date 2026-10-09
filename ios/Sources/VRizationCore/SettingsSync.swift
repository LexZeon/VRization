import Foundation

/// Reconciliation state owned by one serial executor (normally the main queue).
/// Call edited() for every local change, then sent() only for an actual outgoing snapshot.
public struct SettingsSync {
    public private(set) var highestRevision: Int64 = -1
    public private(set) var awaitingAcknowledgment = false
    private var allocatedSequence: Int64 = 0
    private var latestSentSequence: Int64?
    private var editVersion: UInt64 = 0
    private var sentEditVersion: UInt64 = 0
    private var gestures = 0
    private var sentSnapshot: VRSettings?

    public init() {}
    public mutating func newSession() {
        self = SettingsSync()
    }
    public mutating func beginGesture() { gestures += 1 }
    public mutating func endGesture() { if gestures > 0 { gestures -= 1 } }
    public mutating func edited() { editVersion &+= 1 }
    public mutating func nextSequence() throws -> Int64 {
        guard allocatedSequence < VRProtocol.maximumSequence else { throw VRCoreError.invalid("Settings sequence exhausted; reconnect") }
        allocatedSequence += 1
        return allocatedSequence
    }
    public mutating func sent(sequence: Int64, snapshot: VRSettings) throws {
        _ = try snapshot.validated()
        guard sequence > (latestSentSequence ?? 0), sequence <= allocatedSequence else {
            throw VRCoreError.invalid("Settings sequence was not allocated in order")
        }
        latestSentSequence = sequence
        sentEditVersion = editVersion
        sentSnapshot = snapshot
        awaitingAcknowledgment = true
    }
    public mutating func accept(snapshot: VRSettings, revision: Int64?, clientSeq: Int64?) -> Bool {
        guard (try? snapshot.validated()) != nil,
              revision.map({ (0...VRProtocol.maximumSequence).contains($0) }) ?? true,
              clientSeq.map({ (0...VRProtocol.maximumSequence).contains($0) }) ?? true else { return false }
        if let sequence = clientSeq {
            guard let latest = latestSentSequence, sequence <= latest else { return false }
        }
        let oldRevision = revision.map { $0 < highestRevision } ?? false
        if let revision = revision { highestRevision = max(highestRevision, revision) }
        // Equal revisions may acknowledge different sends after host broadcast coalescing.
        if !oldRevision, let sequence = clientSeq, sequence == latestSentSequence { awaitingAcknowledgment = false }
        if oldRevision { return false }
        if let sequence = clientSeq, sequence != latestSentSequence { return false }
        if gestures > 0 || editVersion > sentEditVersion { return false }
        if awaitingAcknowledgment && clientSeq == nil {
            // Legacy hosts have no sequence/revision; only the exact sent snapshot is an ack.
            if revision == nil && snapshot == sentSnapshot { awaitingAcknowledgment = false }
            else { return false }
        }
        return true
    }
}
