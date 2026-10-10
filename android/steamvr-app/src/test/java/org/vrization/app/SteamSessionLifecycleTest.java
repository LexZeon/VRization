package org.vrization.app;
import java.util.ArrayDeque;
import java.util.Queue;
import org.junit.Test;
import org.vrization.core.SocketAttempt;
import static org.junit.Assert.*;

public final class SteamSessionLifecycleTest {
    @Test public void oldAcceptedSnapshotAndBinaryCannotReachAReconnectedMonoSession() {
        Queue<Runnable> owner=new ArrayDeque<>(); SessionDispatcher dispatch=new SessionDispatcher(owner::add);
        long old=dispatch.invalidate(); StreamSession[] active={SteamFixtures.session(19,false,true)}; int[] frames={0};
        dispatch.dispatch(old,()->active[0]=SteamFixtures.session(19,true,true));
        dispatch.dispatch(old,()->frames[0]++); dispatch.invalidate(); active[0]=StreamSession.legacy();
        while(!owner.isEmpty())owner.remove().run(); assertFalse(active[0].stereo); assertEquals(0,frames[0]);
    }
    @Test public void oldUsbRetryCannotChangeTheNewSocketsLayout() {
        Queue<Runnable> owner=new ArrayDeque<>(); SessionDispatcher dispatch=new SessionDispatcher(owner::add);
        SocketAttempt socket=new SocketAttempt(); long session=dispatch.invalidate(),old=socket.start();
        StreamSession[] active={StreamSession.legacy()};
        dispatch.dispatch(session,()->socket.deliverCurrent(old,()->active[0]=SteamFixtures.session(19,true,true)));
        socket.start(); while(!owner.isEmpty())owner.remove().run(); assertFalse(active[0].stereo);
    }
    @Test public void backgroundShutdownRejectsAnAlreadyQueuedStereoFrame() {
        Queue<Runnable> owner=new ArrayDeque<>(); SessionDispatcher dispatch=new SessionDispatcher(owner::add);
        long session=dispatch.invalidate(); int[] frames={0}; dispatch.dispatch(session,()->frames[0]++);
        dispatch.close(); while(!owner.isEmpty())owner.remove().run(); assertEquals(0,frames[0]);
    }
    @Test public void editorAndQueueBackpressureStopOrientationUntilTheLocalGateAllowsIt() {
        PoseSendGate gate=new PoseSendGate(); assertTrue(gate.maySend(true,0)); gate.setEnabled(false);
        assertFalse(gate.maySend(true,0)); gate.setEnabled(true); assertFalse(gate.maySend(false,0));
        assertFalse(gate.maySend(true,65536)); assertTrue(gate.maySend(true,0));
    }
}
