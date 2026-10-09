package org.vrization.app;

import java.util.ArrayDeque;
import java.util.Queue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
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
    @Test public void usbDiscoveryCannotOpenSocketAfterSwitchingToLan() {
        Queue<Runnable> owner = new ArrayDeque<>();
        SessionDispatcher sessions = new SessionDispatcher(owner::add);
        String[] destination = {"none"}; long usb = sessions.invalidate();
        sessions.dispatch(usb, () -> destination[0] = "usb");
        long lan = sessions.invalidate();
        sessions.dispatch(lan, () -> destination[0] = "lan");
        while (!owner.isEmpty()) owner.remove().run();
        assertEquals("lan", destination[0]);
    }
    @Test public void backgroundOrLanguageSwitchDropsAlreadyQueuedUsbResponse() {
        Queue<Runnable> owner = new ArrayDeque<>();
        SessionDispatcher sessions = new SessionDispatcher(owner::add);
        boolean[] opened = {false}; long usb = sessions.invalidate();
        sessions.dispatch(usb, () -> opened[0] = true);
        sessions.invalidate(); owner.remove().run();
        assertFalse(opened[0]);
    }
    @Test public void directFrameHandoffDoesNotWaitForQueuedUiWork() {
        Queue<Runnable> owner = new ArrayDeque<>();
        SessionDispatcher sessions = new SessionDispatcher(owner::add);
        long connection = sessions.invalidate(); int[] frames = {0};
        sessions.dispatch(connection, () -> frames[0] += 100);
        assertTrue(sessions.deliverCurrent(connection, () -> frames[0]++));
        assertEquals(1, frames[0]); assertEquals(1, owner.size());
    }
    @Test public void staleDirectFrameIsRejectedAfterReconnectAndShutdown() {
        SessionDispatcher sessions = new SessionDispatcher(Runnable::run);
        long old = sessions.invalidate(); long current = sessions.invalidate();
        int[] frames = {0};
        assertFalse(sessions.deliverCurrent(old, () -> frames[0]++));
        assertTrue(sessions.deliverCurrent(current, () -> frames[0]++));
        sessions.close();
        assertFalse(sessions.deliverCurrent(current, () -> frames[0]++));
        assertEquals(1, frames[0]);
    }
    @Test public void invalidationCannotPassAnInFlightDirectTransfer() throws Exception {
        SessionDispatcher sessions = new SessionDispatcher(Runnable::run);
        long connection = sessions.invalidate();
        CountDownLatch transferring = new CountDownLatch(1), release = new CountDownLatch(1);
        CountDownLatch invalidating = new CountDownLatch(1), invalidated = new CountDownLatch(1);
        ExecutorService threads = Executors.newFixedThreadPool(2);
        try {
            Future<Boolean> frame = threads.submit(() -> sessions.deliverCurrent(connection, () -> {
                transferring.countDown();
                try { assertTrue(release.await(2, TimeUnit.SECONDS)); }
                catch (InterruptedException failure) { throw new AssertionError(failure); }
                assertTrue(sessions.isCurrent(connection));
            }));
            assertTrue(transferring.await(2, TimeUnit.SECONDS));
            Future<?> disconnect = threads.submit(() -> {
                invalidating.countDown(); sessions.invalidate(); invalidated.countDown();
            });
            assertTrue(invalidating.await(2, TimeUnit.SECONDS));
            assertFalse(invalidated.await(40, TimeUnit.MILLISECONDS));
            release.countDown();
            assertTrue(frame.get(2, TimeUnit.SECONDS)); disconnect.get(2, TimeUnit.SECONDS);
            assertFalse(sessions.deliverCurrent(connection, () -> fail("old frame delivered")));
        } finally { release.countDown(); threads.shutdownNow(); }
    }
}
