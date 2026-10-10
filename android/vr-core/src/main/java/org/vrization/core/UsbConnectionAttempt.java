package org.vrization.core;

/** Main-owner policy for one bounded foreground USB attempt; no timers or worker threads. */
public final class UsbConnectionAttempt {
    /** Only an explicit phone action may request that the computer start streaming. */
    public enum Source { AUTOMATIC, PHONE_ACTION, COMPUTER_ACTION }
    public static final long WINDOW_MILLIS = 30_000, RETRY_MILLIS = 1_000;
    private long epoch, deadline;
    private boolean active, inFlight, socketStarted;
    private Source source = Source.AUTOMATIC;
    private boolean hostWakePending;

    public void start(long session, long now) { start(session, now, Source.AUTOMATIC); }
    public void start(long session, long now, Source source) {
        epoch = session; deadline = now + WINDOW_MILLIS;
        active = true; inFlight = false; socketStarted = false;
        this.source = source; hostWakePending = source == Source.PHONE_ACTION;
    }
    public boolean isActive(long session) { return active && epoch == session; }
    public boolean isAutomatic() { return active && source == Source.AUTOMATIC; }
    public long remaining(long session, long now) { return isActive(session) ? Math.max(0, deadline - now) : 0; }
    /** Called once at the start of a phone action; later discovery/socket retries cannot wake again. */
    public boolean takeHostWake(long session, long now) {
        if (remaining(session, now) == 0 || !hostWakePending) return false;
        hostWakePending = false; return true;
    }
    public boolean beginDiscovery(long session, long now) {
        if (remaining(session, now) == 0 || hostWakePending || socketStarted || inFlight) return false;
        inFlight = true; return true;
    }
    /** Negative means this callback cannot schedule a retry; the owner separately handles expiry. */
    public long discoveryFailed(long session, long now) {
        if (!isActive(session) || socketStarted || !inFlight) return -1;
        inFlight = false;
        long remaining = remaining(session, now);
        return remaining == 0 ? -1 : Math.min(RETRY_MILLIS, remaining);
    }
    public boolean beginSocket(long session, long now) {
        if (remaining(session, now) == 0 || socketStarted || !inFlight) return false;
        inFlight = false; socketStarted = true; return true;
    }
    /** A transient failure before the validated hello returns to discovery in the same window. */
    public long socketFailed(long session, long now) {
        if (!isActive(session) || !socketStarted) return -1;
        socketStarted = false;
        long remaining = remaining(session, now);
        return remaining == 0 ? -1 : Math.min(RETRY_MILLIS, remaining);
    }
    public boolean established(long session, long now) {
        if (remaining(session, now) == 0 || !socketStarted) return false;
        active = false; return true;
    }
    public void cancel() { active = false; inFlight = false; socketStarted = false; hostWakePending = false; }
}
