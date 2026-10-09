import Foundation

/// Saved phone preferences take priority once per validated connection.
/// Subsequent live PC changes still use the ordinary revision/sequence gate.
public struct LocalProfileSync {
    public enum Reception: Equatable { case restoreLocal, applyHost, ignore }
    private var sync = SettingsSync()
    private var needsInitialSettings = false
    private var restoreSavedProfile = false
    public private(set) var previewing = false
    public init() {}
    public mutating func newSession(hasSavedProfile: Bool = false) {
        sync.newSession(); needsInitialSettings = true; restoreSavedProfile = hasSavedProfile; previewing = false
    }
    public mutating func beginPreview() { if !previewing { previewing = true; sync.beginGesture() } }
    public mutating func endPreview() { if previewing { previewing = false; sync.endGesture() } }
    public mutating func beginGesture() { sync.beginGesture() }
    public mutating func endGesture() { sync.endGesture() }
    public mutating func edited() { sync.edited() }
    public mutating func nextSequence() throws -> Int64 { try sync.nextSequence() }
    public mutating func sent(sequence: Int64, snapshot: VRSettings) throws { try sync.sent(sequence: sequence, snapshot: snapshot) }
    public mutating func receive(snapshot: VRSettings, revision: Int64?, clientSeq: Int64?) -> Reception {
        guard (try? snapshot.validated()) != nil else { return .ignore }
        if needsInitialSettings {
            // StreamClient invokes newSession only after a valid host hello,
            // and its first settings callback is that hello's full snapshot.
            guard clientSeq == nil, sync.accept(snapshot: snapshot, revision: revision, clientSeq: nil) else { return .ignore }
            needsInitialSettings = false
            return restoreSavedProfile ? .restoreLocal : .applyHost
        }
        let accepted = sync.accept(snapshot: snapshot, revision: revision, clientSeq: clientSeq)
        return accepted && !previewing ? .applyHost : .ignore
    }
}
