package org.vrization.app;

/** One fresh foreground attempt; returning from background never retries automatically. */
final class InitialUsbDetection {
    private boolean pending;
    InitialUsbDetection(boolean freshLaunch) { pending = freshLaunch; }
    boolean onForeground(ConnectionMode mode) {
        boolean detect = pending && mode == ConnectionMode.USB;
        pending = false;
        return detect;
    }
    void stop() { pending = false; }
}
