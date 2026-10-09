package org.vrization.app;

/** At most one application ping is outstanding; this measures round trip, not video delay. */
final class PingTracker {
    private static final long EXPIRY_MS = 5000;
    private long sentAt = -1;
    // v1 pong carries no id. Never replace an outstanding ping: a delayed old
    // pong could otherwise look like an impossibly fast reply to the new one.
    boolean shouldSend(long now) { return sentAt < 0; }
    void sent(long now) { sentAt = now; }
    Long pong(long now) {
        long start = sentAt;
        sentAt = -1;
        return start >= 0 && now >= start && now - start < EXPIRY_MS ? now - start : null;
    }
    void reset() { sentAt = -1; }
}
