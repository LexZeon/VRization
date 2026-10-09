package org.vrization.app;

import java.util.ArrayDeque;
import org.junit.Test;
import static org.junit.Assert.*;

public final class UsbConnectionAttemptTest {
    @Test public void computerFirstOpensExactlyOneSocketAndStopsAtTheValidatedHello() {
        UsbConnectionAttempt attempt = new UsbConnectionAttempt(); attempt.start(1, 100);
        assertTrue(attempt.beginDiscovery(1, 100)); assertFalse(attempt.beginDiscovery(1, 101));
        assertTrue(attempt.beginSocket(1, 150)); assertFalse(attempt.beginSocket(1, 151));
        assertFalse(attempt.beginDiscovery(1, 160)); assertEquals(-1, attempt.discoveryFailed(1, 160));
        assertTrue(attempt.established(1, 200)); assertFalse(attempt.isActive(1));
        assertFalse(attempt.beginDiscovery(1, 201)); assertFalse(attempt.established(1, 201));
    }
    @Test public void phoneFirstRetriesUntilTheComputerOrAuthorizationBecomesReady() {
        UsbConnectionAttempt attempt = new UsbConnectionAttempt(); attempt.start(8, 0);
        assertTrue(attempt.beginDiscovery(8, 0)); assertEquals(1000, attempt.discoveryFailed(8, 10));
        assertTrue(attempt.beginDiscovery(8, 1010)); assertEquals(1000, attempt.discoveryFailed(8, 1020));
        assertTrue(attempt.beginDiscovery(8, 2020)); assertTrue(attempt.beginSocket(8, 2040));
        assertTrue(attempt.established(8, 2050)); assertFalse(attempt.isActive(8));
    }
    @Test public void repeatedFailuresDoNotExtendTheOriginalThirtySecondWindow() {
        UsbConnectionAttempt attempt = new UsbConnectionAttempt(); attempt.start(2, 20);
        assertTrue(attempt.beginDiscovery(2, 20)); assertEquals(1000, attempt.discoveryFailed(2, 25));
        assertTrue(attempt.beginDiscovery(2, 29_000)); assertEquals(40, attempt.discoveryFailed(2, 29_980));
        assertEquals(0, attempt.remaining(2, 30_020)); assertFalse(attempt.beginDiscovery(2, 30_020));
        attempt.cancel(); assertFalse(attempt.isActive(2));
    }
    @Test public void deadlineAlsoBoundsAComputerFoundLateWithAnUnresponsiveHandshake() {
        UsbConnectionAttempt attempt = new UsbConnectionAttempt(); attempt.start(3, 50);
        assertTrue(attempt.beginDiscovery(3, 29_000)); assertTrue(attempt.beginSocket(3, 29_050));
        assertFalse(attempt.established(3, 30_050)); assertEquals(0, attempt.remaining(3, 30_050));
        assertFalse(attempt.beginDiscovery(3, 30_051)); attempt.cancel();
        assertFalse(attempt.established(3, 30_052));
    }
    @Test public void cancelOrBackgroundStopsRequestsRetriesAndLateSuccess() {
        UsbConnectionAttempt attempt = new UsbConnectionAttempt(); attempt.start(4, 0);
        assertTrue(attempt.beginDiscovery(4, 0)); attempt.cancel();
        assertEquals(-1, attempt.discoveryFailed(4, 500)); assertFalse(attempt.beginSocket(4, 500));
        assertFalse(attempt.beginDiscovery(4, 1000)); assertEquals(0, attempt.remaining(4, 1000));
    }
    @Test public void anotherClickStartsANewWindowWithoutAcceptingOldCallbacks() {
        UsbConnectionAttempt attempt = new UsbConnectionAttempt(); attempt.start(5, 0);
        assertTrue(attempt.beginDiscovery(5, 0)); attempt.cancel(); attempt.start(6, 25_000);
        assertEquals(-1, attempt.discoveryFailed(5, 25_100)); assertFalse(attempt.beginSocket(5, 25_100));
        assertEquals(30_000, attempt.remaining(6, 25_000)); assertTrue(attempt.beginDiscovery(6, 25_100));
        assertTrue(attempt.beginSocket(6, 25_200)); assertTrue(attempt.established(6, 25_300));
    }
    @Test public void duplicateFailureCannotScheduleParallelRequestsOrRepeatedConnections() {
        UsbConnectionAttempt attempt = new UsbConnectionAttempt(); attempt.start(7, 0);
        assertTrue(attempt.beginDiscovery(7, 0)); assertEquals(1000, attempt.discoveryFailed(7, 1));
        assertEquals(-1, attempt.discoveryFailed(7, 2)); assertFalse(attempt.beginSocket(7, 3));
        assertTrue(attempt.beginDiscovery(7, 1001)); assertFalse(attempt.beginDiscovery(7, 1002));
        assertTrue(attempt.beginSocket(7, 1003)); assertFalse(attempt.beginSocket(7, 1004));
    }
    @Test public void queuedPreviousGenerationRetryCannotTouchTheCurrentAttempt() {
        ArrayDeque<Runnable> queue = new ArrayDeque<>(); SessionDispatcher sessions = new SessionDispatcher(queue::add);
        UsbConnectionAttempt attempt = new UsbConnectionAttempt(); long old = sessions.invalidate(); attempt.start(old, 0);
        assertTrue(attempt.beginDiscovery(old, 0)); assertEquals(1000, attempt.discoveryFailed(old, 1));
        int[] requestCount = {0}; sessions.dispatch(old, () -> { if (attempt.beginDiscovery(old, 1001)) requestCount[0]++; });
        long current = sessions.invalidate(); attempt.cancel(); attempt.start(current, 500);
        sessions.dispatch(current, () -> { if (attempt.beginDiscovery(current, 500)) requestCount[0]++; });
        queue.remove().run(); assertEquals(0, requestCount[0]);
        queue.remove().run(); assertEquals(1, requestCount[0]); assertTrue(attempt.beginSocket(current, 600));
    }
    @Test public void aStoppedComputerCanOnlyRetryBeforeHandshakeSuccessOrExplicitCancellation() {
        UsbConnectionAttempt attempt = new UsbConnectionAttempt(); attempt.start(9, 0);
        assertTrue(attempt.beginDiscovery(9, 0)); assertEquals(1000, attempt.discoveryFailed(9, 10));
        assertTrue(attempt.beginDiscovery(9, 1010)); assertTrue(attempt.beginSocket(9, 1020));
        attempt.cancel(); assertFalse(attempt.established(9, 1030)); assertFalse(attempt.beginDiscovery(9, 1040));
    }
}
