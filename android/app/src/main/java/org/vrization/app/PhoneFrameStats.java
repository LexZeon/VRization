package org.vrization.app;

/** Constant-space, session-bound phone measurements from one monotonic clock.
 * Texture submission excludes PC capture, transport before reception and physical presentation.
 */
final class PhoneFrameStats {
    private long epoch = -1, decodedAt = -1, uploadAt = -1;
    private int decodedCount, uploadedCount;
    private double processingNanos;

    synchronized void newSession(long value) {
        epoch = value; decodedAt = uploadAt = -1;
        decodedCount = uploadedCount = 0; processingNanos = 0;
    }
    synchronized void clear() { newSession(-1); }
    synchronized Double decoded(long value, long now) {
        if (value != epoch || now < 0) return null;
        if (decodedAt < 0) { decodedAt = now; return null; }
        if (now < decodedAt) return null;
        decodedCount++;
        long elapsed = now - decodedAt;
        if (elapsed < 1_000_000_000L) return null;
        double fps = decodedCount * 1_000_000_000d / elapsed;
        decodedAt = now; decodedCount = 0;
        return fps;
    }
    synchronized Double uploaded(long value, long received, long submitted) {
        if (value != epoch || received < 0 || submitted < received) return null;
        if (uploadAt < 0) uploadAt = submitted;
        if (submitted < uploadAt) return null;
        processingNanos += submitted - received;
        uploadedCount++;
        if (submitted - uploadAt < 1_000_000_000L) return null;
        double milliseconds = processingNanos / uploadedCount / 1_000_000d;
        uploadAt = submitted; uploadedCount = 0; processingNanos = 0;
        return milliseconds;
    }
}
