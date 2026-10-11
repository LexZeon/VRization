package org.vrization.app;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Map;
import org.junit.Test;
import static org.junit.Assert.*;

public final class RefreshReconnectIntentTest {
    private static HostSessionGate host(boolean accepted, boolean capability) {
        HostSessionGate result = new HostSessionGate();
        Map<String, Object> hello = SteamFixtures.hello(accepted);
        ArrayList<String> capabilities = new ArrayList<>(SteamFixtures.CAPS);
        if (capability) capabilities.add(VideoRefreshValues.CAPABILITY);
        hello.put("capabilities", capabilities); result.receive(hello); return result;
    }

    @Test public void ordinaryAndAutomaticConnectionsNeverRequestRecovery() {
        RefreshReconnectIntent intent = new RefreshReconnectIntent();
        HostSessionGate host = host(true, true);
        for (long connection : new long[]{1, 2, 3}) {
            intent.start(connection, false);
            assertFalse(intent.take(connection, host.streamSession(), host.supportsVideoRefresh()));
        }
    }

    @Test public void explicitRefreshWaitsForACompleteAcceptedHmdSnapshotThenRunsOnce() {
        RefreshReconnectIntent intent = new RefreshReconnectIntent(); intent.start(7, true);
        HostSessionGate host = host(false, true);
        assertFalse(intent.take(7, host.streamSession(), host.supportsVideoRefresh()));
        assertTrue(intent.isPending());
        host.receive(SteamFixtures.settings(true));
        assertTrue(intent.take(7, host.streamSession(), host.supportsVideoRefresh()));
        assertFalse(intent.isPending());
        host.receive(SteamFixtures.settings(true));
        assertFalse(intent.take(7, host.streamSession(), host.supportsVideoRefresh()));
    }

    @Test public void alreadyAcceptedLanHelloCanConsumeTheSameOneShot() {
        RefreshReconnectIntent intent = new RefreshReconnectIntent(); intent.start(4, true);
        HostSessionGate host = host(true, true);
        assertTrue(intent.take(4, host.streamSession(), host.supportsVideoRefresh()));
        assertFalse(intent.take(4, host.streamSession(), host.supportsVideoRefresh()));
    }

    @Test public void legacyDirectAndOldHostsCannotAuthorizeRecovery() {
        for (StreamSession session : new StreamSession[]{StreamSession.legacy(),
                SteamFixtures.session(19, true, false), SteamFixtures.session(19, true, true)}) {
            RefreshReconnectIntent intent = new RefreshReconnectIntent(); intent.start(9, true);
            assertFalse(intent.take(9, session, session.hmd ? false : true));
            assertFalse(intent.isPending());
            assertFalse("A later echo must not recover an old/direct connection",
                intent.take(9, SteamFixtures.session(19, true, true), true));
        }
    }

    @Test public void wrongConnectionEpochCannotConsumeCurrentUserIntent() {
        RefreshReconnectIntent intent = new RefreshReconnectIntent(); intent.start(12, true);
        assertFalse(intent.take(11, SteamFixtures.session(19, true, true), true));
        assertTrue(intent.isPending());
        assertTrue(intent.take(12, SteamFixtures.session(20, true, true), true));
    }

    @Test public void disconnectBackgroundAndStopCancelInsteadOfTransferringAuthority() {
        RefreshReconnectIntent intent = new RefreshReconnectIntent(); intent.start(3, true); intent.cancel();
        assertFalse(intent.take(3, SteamFixtures.session(19, true, true), true));
        intent.start(4, false);
        assertFalse(intent.take(4, SteamFixtures.session(20, true, true), true));
    }

    @Test public void newConnectReplacesRatherThanInheritsARefreshIntent() {
        RefreshReconnectIntent intent = new RefreshReconnectIntent(); intent.start(3, true); intent.start(4, false);
        assertFalse(intent.take(3, SteamFixtures.session(19, true, true), true));
        assertFalse(intent.take(4, SteamFixtures.session(20, true, true), true));
    }

    @Test public void delayedValidatedSnapshotCannotSendAfterSessionInvalidation() {
        ArrayDeque<Runnable> queue = new ArrayDeque<>(); SessionDispatcher connection = new SessionDispatcher(queue::add);
        RefreshReconnectIntent intent = new RefreshReconnectIntent(); int[] requests = {0};
        long old = connection.invalidate(); intent.start(old, true);
        connection.dispatch(old, () -> {
            if (intent.take(old, SteamFixtures.session(19, true, true), true)) requests[0]++;
        });
        long current = connection.invalidate(); intent.cancel(); intent.start(current, false);
        queue.remove().run(); assertEquals(0, requests[0]);
        connection.dispatch(current, () -> {
            if (intent.take(current, SteamFixtures.session(20, true, true), true)) requests[0]++;
        });
        queue.remove().run(); assertEquals(0, requests[0]);
    }

    @Test public void failedPostHandshakeResetCannotCreateAnAutomaticRecoveryLoop() {
        RefreshReconnectIntent intent = new RefreshReconnectIntent(); intent.start(8, true);
        assertTrue(intent.take(8, SteamFixtures.session(19, true, true), true));
        VideoRefreshGate video = new VideoRefreshGate(); VideoRefreshGate.Request reset = video.begin(19, 100);
        assertTrue(video.expire(reset, 8100));
        // The post-handshake fallback reconnects for video only, with no new
        // user action. Its complete supported hello cannot authorize recovery.
        intent.cancel(); intent.start(9, false);
        assertFalse(intent.take(9, SteamFixtures.session(20, true, true), true));
    }
}
