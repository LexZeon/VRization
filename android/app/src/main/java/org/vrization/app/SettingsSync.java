package org.vrization.app;

import org.vrization.core.VrSettings;

/** Main-thread settings reconciliation, independent of Android/UI for deterministic tests. */
final class SettingsSync {
    private long highestRevision = -1, allocatedSeq, latestSentSeq, editVersion, sentEditVersion;
    private int gestures;
    private boolean awaitingAck;
    private VrSettings sentSnapshot;

    void newSession() {
        highestRevision = -1; editVersion = sentEditVersion = 0; awaitingAck = false; gestures = 0;
        sentSnapshot = null;
    }
    void beginGesture() { gestures++; }
    void endGesture() { if (gestures > 0) gestures--; }
    void edited() { editVersion++; }
    long nextSequence() { return ++allocatedSeq; }
    void sent(long sequence, VrSettings snapshot) {
        latestSentSeq = sequence; sentEditVersion = editVersion;
        sentSnapshot = snapshot.copy(); awaitingAck = true;
    }
    boolean accept(VrSettings snapshot, Long revision, Long clientSeq) {
        boolean oldRevision = revision != null && revision < highestRevision;
        if (revision != null) highestRevision = Math.max(highestRevision, revision);
        if (clientSeq != null && clientSeq == latestSentSeq) awaitingAck = false;
        if (oldRevision || (clientSeq != null && clientSeq != latestSentSeq)) return false;
        if (gestures > 0 || editVersion > sentEditVersion) return false;
        if (awaitingAck && clientSeq == null) {
            if (revision == null && same(snapshot, sentSnapshot)) awaitingAck = false;
            else return false;
        }
        return true;
    }
    private static boolean same(VrSettings a, VrSettings b) {
        return b != null && a.mode.equals(b.mode) && a.scale == b.scale && a.offsetX == b.offsetX
            && a.offsetY == b.offsetY && a.eyeSeparation == b.eyeSeparation && a.fov == b.fov
            && a.distance == b.distance && a.distortion == b.distortion
            && a.sensitivity == b.sensitivity && a.invertY == b.invertY;
    }
}
