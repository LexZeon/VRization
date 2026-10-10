package org.vrization.core;

import java.util.ArrayDeque;
import org.junit.Test;
import static org.junit.Assert.*;

public final class SocketAttemptTest {
    @Test public void explicitDisconnectCancelsTheTransportExactlyOnceAndBlocksLateFrames() {
        SocketAttempt socket = new SocketAttempt();
        int[] cancellations = {0}, frames = {0};
        long current = socket.start(); socket.attach(current, () -> cancellations[0]++);
        assertTrue(socket.deliverCurrent(current, () -> frames[0]++));
        socket.cancel(); socket.cancel();
        assertEquals(1, cancellations[0]);
        assertFalse(socket.deliverCurrent(current, () -> frames[0]++));
        assertEquals(1, frames[0]);
    }

    @Test public void aSocketRegisteredAfterDisconnectIsCancelledInsteadOfBecomingAnOrphan() {
        SocketAttempt socket = new SocketAttempt(); int[] cancellations = {0};
        long late = socket.start(); socket.cancel();
        socket.attach(late, () -> cancellations[0]++);
        assertEquals(1, cancellations[0]); assertFalse(socket.isCurrent(late));
    }

    @Test public void aRetryCancelsTheOldSocketAndItsQueuedHelloAndFailureCannotTouchTheNewOne() {
        ArrayDeque<Runnable> queue = new ArrayDeque<>();
        SocketAttempt socket = new SocketAttempt();
        long old = socket.start(); int[] cancellations = {0}, hellos = {0};
        socket.attach(old, () -> cancellations[0]++);
        queue.add(() -> socket.deliverCurrent(old, () -> hellos[0]++));
        queue.add(() -> socket.deliverCurrent(old, socket::cancel));
        long current = socket.start(); socket.attach(current, () -> cancellations[0]++);
        assertEquals(1, cancellations[0]);
        queue.remove().run(); queue.remove().run();
        assertTrue(socket.isCurrent(current)); assertEquals(0, hellos[0]); assertEquals(1, cancellations[0]);
        assertTrue(socket.deliverCurrent(current, () -> hellos[0]++)); assertEquals(1, hellos[0]);
    }

    @Test public void aPreviousConnectionCannotDeliverToANewSocketAfterTheUserReconnects() {
        ArrayDeque<Runnable> queue = new ArrayDeque<>();
        SocketAttempt socket = new SocketAttempt();
        long previousSocket = socket.start(); int[] frames = {0};
        queue.add(() -> socket.deliverCurrent(previousSocket, () -> frames[0]++));
        socket.cancel(); long current = socket.start();
        queue.remove().run(); assertEquals(0, frames[0]); assertTrue(socket.isCurrent(current));
    }
}
