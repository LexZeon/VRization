package org.vrization.app;

/** Video-only generations are independent of the socket epoch and continuous pose sequence. */
final class VideoRefreshGate {
    static final long DEADLINE_MILLIS = 8000;
    static final class Request {
        final long epoch, requestId, generation, deadline;
        Request(long epoch, long requestId, long generation, long deadline) {
            this.epoch = epoch; this.requestId = requestId; this.generation = generation; this.deadline = deadline;
        }
    }
    private long generation, requestId;
    private Request pending;
    private boolean blocked;
    synchronized boolean isPending() { return pending != null; }
    synchronized long generation() { return generation; }
    synchronized long captureGeneration() { return blocked ? -1 : generation; }
    synchronized Request begin(long epoch, long now) {
        HostSessionGate.integer(epoch, 1, VideoRefreshValues.MAX_SAFE);
        if (now < 0 || now > Long.MAX_VALUE - DEADLINE_MILLIS) throw new IllegalArgumentException("Invalid clock");
        if (pending != null) {
            if (pending.epoch != epoch) throw new IllegalArgumentException("Refresh epoch changed");
            return pending; // Coalesce repeated taps without extending the deadline.
        }
        if (requestId == VideoRefreshValues.MAX_SAFE) return null;
        blocked = true; generation++;
        pending = new Request(epoch, ++requestId, generation, now + DEADLINE_MILLIS); return pending;
    }
    synchronized boolean deliverCurrent(long value, Runnable action) {
        if (blocked || value < 0 || generation != value) return false;
        action.run(); return true;
    }
    synchronized boolean acknowledge(VideoRefreshValues.Ack ack, long now, Runnable ready) {
        if (pending == null || now < 0 || now >= pending.deadline
            || ack.epoch != pending.epoch || ack.requestId != pending.requestId) return false;
        // Prepare the renderer/statistics before any post-ACK binary can be accepted.
        ready.run(); pending = null; blocked = false; return true;
    }
    synchronized boolean expire(Request request, long now) {
        if (pending != request || now < request.deadline) return false;
        abort(); return true;
    }
    /** Cancel an outstanding request without ever admitting its late ACK or old JPEG. */
    synchronized void abort() { pending = null; blocked = true; generation++; }
    /** Connection teardown has its own epoch check; the next explicit connection may receive video. */
    synchronized void newConnection() { pending = null; blocked = false; generation++; }
}
