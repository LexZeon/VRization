package org.vrization.app;

import org.junit.Test;
import static org.junit.Assert.*;

public final class PingTrackerTest {
    @Test public void roundTripUsesOnlyOnePendingPing() {
        PingTracker tracker = new PingTracker();
        assertTrue(tracker.shouldSend(100)); tracker.sent(100);
        assertFalse(tracker.shouldSend(200));
        assertEquals(Long.valueOf(23), tracker.pong(123));
        assertTrue(tracker.shouldSend(124)); assertNull(tracker.pong(125));
    }
    @Test public void staleAndNegativeMeasurementsAreNotDisplayed() {
        PingTracker tracker = new PingTracker(); tracker.sent(100);
        assertNull(tracker.pong(5100));
        tracker.sent(100); assertNull(tracker.pong(99));
    }
    @Test public void timeoutDoesNotMisattributeDelayedPongToANewPing() {
        PingTracker tracker = new PingTracker(); tracker.sent(100);
        assertFalse(tracker.shouldSend(5100));
        assertNull(tracker.pong(5100)); assertTrue(tracker.shouldSend(5101));
        tracker.reset(); assertNull(tracker.pong(5110));
        tracker.sent(5200); assertEquals(Long.valueOf(2), tracker.pong(5202));
    }
}
