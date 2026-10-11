package org.vrization.app;

/** One user Refresh may request recovery after its own replacement connection negotiates. */
final class RefreshReconnectIntent {
    private long connectionEpoch = -1;
    private boolean pending;

    void start(long epoch, boolean userRefresh) {
        connectionEpoch = epoch;
        pending = userRefresh;
    }

    boolean isPending() { return pending; }

    boolean take(long epoch, StreamSession session, boolean videoRefreshSupported) {
        if (!pending || epoch != connectionEpoch) return false;
        if (!session.accepted) return false;
        // An accepted legacy/direct/old host consumes the intent without any
        // input authorization. A later settings echo cannot retry this action.
        pending = false;
        return session.explicit && session.hmd && videoRefreshSupported;
    }

    void cancel() { pending = false; connectionEpoch = -1; }
}
