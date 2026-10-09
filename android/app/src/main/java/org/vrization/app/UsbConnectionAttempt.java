package org.vrization.app;

/** Main-owner policy for one bounded foreground USB attempt; no timers or worker threads. */
final class UsbConnectionAttempt {
    static final long WINDOW_MILLIS = 30_000, RETRY_MILLIS = 1_000;
    private long epoch, deadline;
    private boolean active, inFlight, socketStarted;

    void start(long session, long now) {
        epoch = session; deadline = now + WINDOW_MILLIS;
        active = true; inFlight = false; socketStarted = false;
    }
    boolean isActive(long session) { return active && epoch == session; }
    long remaining(long session, long now) { return isActive(session) ? Math.max(0, deadline - now) : 0; }
    boolean beginDiscovery(long session, long now) {
        if (remaining(session, now) == 0 || socketStarted || inFlight) return false;
        inFlight = true; return true;
    }
    /** Negative means this callback cannot schedule a retry; the owner separately handles expiry. */
    long discoveryFailed(long session, long now) {
        if (!isActive(session) || socketStarted || !inFlight) return -1;
        inFlight = false;
        long remaining = remaining(session, now);
        return remaining == 0 ? -1 : Math.min(RETRY_MILLIS, remaining);
    }
    boolean beginSocket(long session, long now) {
        if (remaining(session, now) == 0 || socketStarted || !inFlight) return false;
        inFlight = false; socketStarted = true; return true;
    }
    boolean established(long session, long now) {
        if (remaining(session, now) == 0 || !socketStarted) return false;
        active = false; return true;
    }
    void cancel() { active = false; inFlight = false; socketStarted = false; }
}
