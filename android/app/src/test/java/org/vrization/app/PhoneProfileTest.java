package org.vrization.app;

import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.Test;
import org.vrization.core.VrSettings;
import static org.junit.Assert.*;

public final class PhoneProfileTest {
    @Test public void everyCommittedVrFieldRestoresAfterRestartWithoutAConnection() {
        PhoneProfile profile = new PhoneProfile(null); assertFalse(profile.hasSavedProfile());
        VrSettings value = new VrSettings(); value.mode = "fps"; value.scale = .91f;
        value.offsetX = .23f; value.offsetY = -.24f; value.eyeSeparation = .15f; value.fov = 109;
        value.distance = 7; value.distortion = .49f; value.sensitivity = 2999; value.invertY = true;
        profile.commit(value);
        PhoneProfile restarted = new PhoneProfile(SettingsValues.encode(profile.snapshot()));
        assertTrue(restarted.hasSavedProfile());
        assertEquals(SettingsValues.encode(value), SettingsValues.encode(restarted.snapshot()));
        value.scale = .5f; restarted.snapshot().offsetX = 0;
        assertEquals(.91f, restarted.snapshot().scale, 0); assertEquals(.23f, restarted.snapshot().offsetX, 0);
    }
    @Test public void resetRestoresFullVrDefaultsAndPhonePreferenceDefaults() {
        PhoneProfile profile = new PhoneProfile(null); VrSettings changed = new VrSettings();
        changed.mode = "fps"; changed.scale = .5f; changed.invertY = true; profile.commit(changed);
        assertEquals(SettingsValues.encode(new VrSettings()), SettingsValues.encode(profile.reset()));
        assertTrue(profile.hasSavedProfile()); assertEquals("en", PhoneProfile.DEFAULT_LANGUAGE);
        assertEquals("usb", PhoneProfile.DEFAULT_TRANSPORT); assertEquals("", PhoneProfile.DEFAULT_HOST);
        assertEquals("8765", PhoneProfile.DEFAULT_PORT);
    }
    @Test public void endpointFloatsRemainInsideTheHostsStrictDecimalBounds() {
        VrSettings value = new VrSettings(); value.offsetX = .3f; value.offsetY = -.3f; value.eyeSeparation = .2f;
        Map<String, Object> encoded = SettingsValues.encode(value);
        assertEquals(.3d, (Double) encoded.get("offsetX"), 0); assertEquals(-.3d, (Double) encoded.get("offsetY"), 0);
        assertEquals(encoded, SettingsValues.encode(SettingsValues.decode(encoded, new VrSettings(), true)));
    }
    @Test public void invalidStoredOrHostValuesAreRejectedRatherThanSilentlyClamped() {
        for (Object invalid : new Object[]{"0.9", Boolean.TRUE, Double.NaN, Double.POSITIVE_INFINITY, .49, 1.01}) {
            Map<String, Object> fields = new LinkedHashMap<>(SettingsValues.encode(new VrSettings())); fields.put("scale", invalid);
            try { new PhoneProfile(fields); fail("Accepted invalid scale " + invalid); } catch (IllegalArgumentException expected) { }
        }
        Map<String, Object> unknown = new LinkedHashMap<>(); unknown.put("secret", "anything");
        try { SettingsValues.decode(unknown, new VrSettings(), false); fail("Unknown setting accepted"); }
        catch (IllegalArgumentException expected) { }
    }
    @Test public void validHostPartialUpdatePreservesTheOtherCommittedFields() {
        VrSettings previous = new VrSettings(); previous.mode = "fps"; previous.invertY = true; previous.sensitivity = 1200;
        Map<String, Object> partial = new LinkedHashMap<>(); partial.put("offsetY", .3);
        VrSettings result = SettingsValues.decode(partial, previous, false);
        assertEquals(.3f, result.offsetY, 0); assertEquals("fps", result.mode); assertTrue(result.invertY);
        assertEquals(1200, result.sensitivity, 0); assertEquals(0, previous.offsetY, 0);
    }
}
