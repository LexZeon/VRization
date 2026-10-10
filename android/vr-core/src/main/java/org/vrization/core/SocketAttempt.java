package org.vrization.core;

/** Owns one socket and rejects callbacks from a replaced or explicitly cancelled socket. */
public final class SocketAttempt {
    private volatile long generation;
    private volatile boolean active;
    private Runnable cancellation;

    public synchronized long start() {
        cancel();
        active = true;
        return generation;
    }

    /** A socket that finishes opening after cancellation must be closed immediately. */
    public synchronized void attach(long value, Runnable cancelSocket) {
        if (!isCurrent(value)) { cancelSocket.run(); return; }
        cancellation = cancelSocket;
    }

    public boolean isCurrent(long value) { return active && generation == value; }

    public synchronized boolean deliverCurrent(long value, Runnable action) {
        if (!isCurrent(value)) return false;
        action.run();
        return true;
    }

    public synchronized void cancel() {
        active = false;
        generation++;
        Runnable previous = cancellation;
        cancellation = null;
        if (previous != null) previous.run();
    }
}
