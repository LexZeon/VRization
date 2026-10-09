package org.vrization.app;

/** Never accumulate pending poses or replay a pose recorded during editing. */
final class PoseSendGate {
    private volatile boolean enabled = true;
    void setEnabled(boolean value) { enabled = value; }
    boolean maySend(boolean connected, long queuedBytes) { return enabled && connected && queuedBytes == 0; }
}
