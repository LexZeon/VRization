package org.vrization.app;

import java.util.concurrent.Executor;
import java.util.concurrent.atomic.AtomicLong;

/** Connection transitions run on one owner executor; queued callbacks recheck identity there. */
final class SessionDispatcher {
    private final Executor owner;
    private final AtomicLong generation = new AtomicLong();
    private volatile boolean closed;
    SessionDispatcher(Executor owner) { this.owner = owner; }
    synchronized long invalidate() { return generation.incrementAndGet(); }
    boolean isCurrent(long value) { return !closed && generation.get() == value; }
    boolean isClosed() { return closed; }
    void dispatch(long value, Runnable action) {
        owner.execute(() -> deliverCurrent(value, action));
    }
    /** A short transport/render handoff can bypass the UI queue without racing invalidation. */
    synchronized boolean deliverCurrent(long value, Runnable action) {
        if (!isCurrent(value)) return false;
        action.run();
        return true;
    }
    synchronized void close() { closed = true; invalidate(); }
}
