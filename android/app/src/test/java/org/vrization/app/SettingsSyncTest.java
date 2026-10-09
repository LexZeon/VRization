package org.vrization.app;

import org.junit.Test;
import org.vrization.core.VrSettings;
import static org.junit.Assert.*;

public final class SettingsSyncTest {
    private static VrSettings scale(float scale) { VrSettings s = new VrSettings(); s.scale = scale; return s; }
    @Test public void delayedEchoCannotReplaceUnsentFinalDragValue() {
        SettingsSync sync = new SettingsSync(); sync.newSession(); sync.beginGesture();
        sync.edited(); long first = sync.nextSequence(); sync.sent(first, scale(.8f));
        sync.edited();
        assertFalse(sync.accept(scale(.8f), 1L, first));
        sync.endGesture(); sync.edited();
        long last = sync.nextSequence(); sync.sent(last, scale(.9f));
        assertFalse(sync.accept(scale(.8f), 1L, first));
        assertTrue(sync.accept(scale(.9f), 2L, last));
    }
    @Test public void sameRevisionCanAcknowledgeLatestRequest() {
        SettingsSync sync = new SettingsSync();
        sync.edited(); long sequence = sync.nextSequence(); sync.sent(sequence, scale(.9f));
        assertFalse(sync.accept(scale(.7f), 8L, null));
        assertTrue(sync.accept(scale(.7f), 8L, sequence));
        assertTrue(sync.accept(scale(.6f), 9L, null));
    }
    @Test public void staleRevisionCanConfirmRequestWithoutReplacingNewerState() {
        SettingsSync sync = new SettingsSync();
        sync.edited(); long sequence = sync.nextSequence(); sync.sent(sequence, scale(.9f));
        assertFalse(sync.accept(scale(.7f), 9L, null));
        assertFalse(sync.accept(scale(.9f), 8L, sequence));
        assertTrue(sync.accept(scale(.7f), 9L, null));
    }
    @Test public void reconnectAcceptsRestartedHostRevision() {
        SettingsSync sync = new SettingsSync();
        assertTrue(sync.accept(scale(.8f), 100L, null));
        sync.newSession(); assertTrue(sync.accept(scale(.7f), 0L, null));
    }
    @Test public void reconnectClearsInterruptedOldGesture() {
        SettingsSync sync = new SettingsSync(); sync.beginGesture(); sync.edited();
        sync.newSession(); assertTrue(sync.accept(scale(.7f), 0L, null));
    }
    @Test public void legacyHostMustEchoLatestSnapshotBeforeApplyingOtherChanges() {
        SettingsSync sync = new SettingsSync();
        sync.edited(); long first = sync.nextSequence(); sync.sent(first, scale(.8f));
        sync.edited(); long latest = sync.nextSequence(); sync.sent(latest, scale(.9f));
        assertFalse(sync.accept(scale(.8f), null, null));
        assertTrue(sync.accept(scale(.9f), null, null));
        assertTrue(sync.accept(scale(.7f), null, null));
    }
}
