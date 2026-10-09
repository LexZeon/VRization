package org.vrization.app;

import org.junit.Test;
import static org.junit.Assert.*;

public final class PhoneFrameStatsTest {
    @Test public void decodedRateCountsIntervalsAndReportsOncePerSecond() {
        PhoneFrameStats stats = new PhoneFrameStats(); stats.newSession(1);
        assertNull(stats.decoded(1, 0));
        for (int frame = 1; frame < 60; frame++) assertNull(stats.decoded(1, frame * 1_000_000_000L / 60));
        assertEquals(60d, stats.decoded(1, 1_000_000_000L), 0.0001);
        assertNull(stats.decoded(1, 1_010_000_000L));
    }
    @Test public void phoneProcessingMeanUsesReceiveAndSubmissionOnOneClock() {
        PhoneFrameStats stats = new PhoneFrameStats(); stats.newSession(7);
        assertNull(stats.uploaded(7, 100_000_000L, 104_000_000L));
        assertNull(stats.uploaded(7, 600_000_000L, 606_000_000L));
        assertEquals(6d, stats.uploaded(7, 1_100_000_000L, 1_108_000_000L), 0.0001);
        assertNull(stats.uploaded(7, 1_200_000_000L, 1_204_000_000L));
    }
    @Test public void newSessionDropsOldCallbacksAndResetsPartialWindows() {
        PhoneFrameStats stats = new PhoneFrameStats(); stats.newSession(1);
        stats.decoded(1, 0); stats.uploaded(1, 0, 900_000_000L);
        stats.newSession(2);
        assertNull(stats.decoded(1, 2_000_000_000L));
        assertNull(stats.uploaded(1, 0, 2_000_000_000L));
        assertNull(stats.uploaded(2, 2_000_000_000L, 2_002_000_000L));
        assertEquals(2d, stats.uploaded(2, 3_000_000_000L, 3_002_000_000L), 0.0001);
        stats.clear(); assertNull(stats.decoded(2, 4_000_000_000L));
        assertNull(stats.uploaded(2, 0, 4_000_000_000L));
    }
    @Test public void invalidNegativeOrReversedTimestampsDoNotPolluteMeasurements() {
        PhoneFrameStats stats = new PhoneFrameStats(); stats.newSession(1);
        assertNull(stats.uploaded(1, -1, 0)); assertNull(stats.uploaded(1, 100, 99));
        assertNull(stats.decoded(1, -1)); assertNull(stats.decoded(1, 1_000_000_000L));
        assertNull(stats.decoded(1, 999_999_999L));
        assertEquals(1d, stats.decoded(1, 2_000_000_000L), 0.0001);
        assertNull(stats.uploaded(1, 0, 2_000_000L));
        assertEquals(2d, stats.uploaded(1, 1_000_000_000L, 1_002_000_000L), 0.0001);
    }
}
