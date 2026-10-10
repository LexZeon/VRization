package org.vrization.core;

/** One explicit USB connection request, consumed at foreground entry without replaying it. */
public final class UsbConnectRequest {
    public static final String INTENT_EXTRA = "vrization_connect_usb";
    private boolean pending;

    public void request() { pending = true; }
    public boolean isPending() { return pending; }

    /** Established sessions and explicit attempts consume repeated requests without restarting. */
    public boolean consume(boolean preserveCurrentConnection) {
        boolean connect = pending && !preserveCurrentConnection;
        pending = false;
        return connect;
    }

    /** Explicit cancellation wins over a request that has not reached the foreground yet. */
    public void cancel() { pending = false; }
}
