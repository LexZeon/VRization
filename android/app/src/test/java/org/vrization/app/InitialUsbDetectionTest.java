package org.vrization.app;

import org.junit.Test;
import static org.junit.Assert.*;

public final class InitialUsbDetectionTest {
    @Test public void missingOrOldPreferenceDefaultsToUsbWithoutChangingLanOptIn() {
        assertEquals(ConnectionMode.USB, ConnectionMode.fromPreference(null));
        assertEquals(ConnectionMode.USB, ConnectionMode.fromPreference(""));
        assertEquals(ConnectionMode.USB, ConnectionMode.fromPreference("unknown"));
        assertEquals(ConnectionMode.LAN, ConnectionMode.fromPreference("lan"));
    }
    @Test public void firstForegroundDetectsOnlyOnceAndBackgroundNeverRetries() {
        InitialUsbDetection policy = new InitialUsbDetection(true);
        assertTrue(policy.onForeground(ConnectionMode.USB));
        policy.stop();
        assertFalse(policy.onForeground(ConnectionMode.USB));
        assertFalse(policy.onForeground(ConnectionMode.USB));
    }
    @Test public void languageRecreationAndStateRestoreNeverAutoconnect() {
        assertFalse(new InitialUsbDetection(false).onForeground(ConnectionMode.USB));
        InitialUsbDetection policy = new InitialUsbDetection(true); policy.stop();
        assertFalse(policy.onForeground(ConnectionMode.USB));
    }
    @Test public void lanSelectionConsumesFreshLaunchWithoutHiddenUsbAttempt() {
        InitialUsbDetection policy = new InitialUsbDetection(true);
        assertFalse(policy.onForeground(ConnectionMode.LAN));
        assertFalse(policy.onForeground(ConnectionMode.USB));
    }
}
