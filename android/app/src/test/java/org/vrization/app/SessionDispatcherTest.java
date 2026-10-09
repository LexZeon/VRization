package org.vrization.app;

import java.util.ArrayDeque;
import java.util.Queue;
import org.junit.Test;
import static org.junit.Assert.*;

public final class SessionDispatcherTest {
    @Test public void queuedOldConnectionCallbacksCannotOverwriteNewSession() {
        Queue<Runnable> owner = new ArrayDeque<>();
        SessionDispatcher sessions = new SessionDispatcher(owner::add);
        String[] status = {"connecting"}; boolean[] connected = {false};
        long old = sessions.invalidate();
        sessions.dispatch(old, () -> { connected[0] = true; status[0] = "old open"; });
        sessions.dispatch(old, () -> { connected[0] = false; status[0] = "old failure"; });
        long current = sessions.invalidate();
        sessions.dispatch(current, () -> { connected[0] = true; status[0] = "new open"; });
        while (!owner.isEmpty()) owner.remove().run();
        assertTrue(connected[0]); assertEquals("new open", status[0]);
    }
    @Test public void disconnectInvalidatesCallbacksAlreadyPostedToOwner() {
        Queue<Runnable> owner = new ArrayDeque<>();
        SessionDispatcher sessions = new SessionDispatcher(owner::add);
        int[] calls = {0}; long connection = sessions.invalidate();
        sessions.dispatch(connection, () -> calls[0]++);
        sessions.invalidate(); owner.remove().run();
        assertEquals(0, calls[0]);
    }
    @Test public void shutdownPreventsAllFurtherDelivery() {
        Queue<Runnable> owner = new ArrayDeque<>();
        SessionDispatcher sessions = new SessionDispatcher(owner::add);
        int[] calls = {0}; long connection = sessions.invalidate();
        sessions.dispatch(connection, () -> calls[0]++);
        sessions.close();
        sessions.dispatch(sessions.invalidate(), () -> calls[0]++);
        while (!owner.isEmpty()) owner.remove().run();
        assertEquals(0, calls[0]); assertTrue(sessions.isClosed());
    }
}
