package org.vrization.app;

import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.Test;
import org.vrization.core.VrSettings;
import org.vrization.core.HeadsetEdit;
import org.vrization.core.HeadsetGeometry;
import static org.junit.Assert.*;

public final class PhoneProfileTest {
    @Test public void everyCommittedVrFieldRestoresAfterRestartWithoutAConnection() {
        PhoneProfile profile = new PhoneProfile(null); assertFalse(profile.hasSavedProfile());
        VrSettings value = new VrSettings(); value.mode = "fps"; value.scale = .91f;
        value.offsetX = .23f; value.offsetY = -.24f; value.eyeSeparation = .15f; value.fov = 109;
        value.distance = 7; value.distortion = .49f; value.sensitivity = 2999; value.stabilization = .83f; value.invertY = true;
        profile.commit(value);
        PhoneProfile restarted = new PhoneProfile(SettingsValues.encode(profile.snapshot()));
        assertTrue(restarted.hasSavedProfile());
        assertEquals(SettingsValues.encode(value), SettingsValues.encode(restarted.snapshot()));
        value.scale = .5f; restarted.snapshot().offsetX = 0;
        assertEquals(.91f, restarted.snapshot().scale, 0); assertEquals(.23f, restarted.snapshot().offsetX, 0);
    }
    @Test public void resetRestoresFullVrDefaultsAndPhonePreferenceDefaults() {
        PhoneProfile profile = new PhoneProfile(null); VrSettings changed = new VrSettings();
        changed.mode = "fps"; changed.scale = .5f; changed.invertY = true; changed.stabilization = .9f; profile.commit(changed);
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
    @Test public void negativeSeamContactSavesAndRestoresThroughTheStrictCompleteProfile() {
        VrSettings original = new VrSettings(); original.scale = .5f; original.mode = "fps";
        HeadsetEdit edit = new HeadsetEdit(original);
        edit.update(HeadsetGeometry.mirroredPan(edit.draft(), .5f, 1, -1, 2, .1f));
        PhoneProfile profile = new PhoneProfile(null); profile.commit(edit.save());
        PhoneProfile restarted = new PhoneProfile(SettingsValues.encode(profile.snapshot()));
        assertEquals(-.75f, restarted.snapshot().eyeSeparation, 0);
        assertEquals(.1f, restarted.snapshot().offsetY, 0); assertEquals("fps", restarted.snapshot().mode);
        assertEquals(.5f, restarted.snapshot().scale, 0); assertEquals(.03f, original.eyeSeparation, 0);
    }
    @Test public void separationWireBoundsAcceptOldProfilesAndNegativeEndpointsButRejectOvershoot() {
        for (double valid : new double[]{-1, -.75, 0, .03, .2}) {
            Map<String, Object> fields = new LinkedHashMap<>(SettingsValues.encode(new VrSettings()));
            fields.put("eyeSeparation", valid);
            assertEquals((float)valid, new PhoneProfile(fields).snapshot().eyeSeparation, 0);
        }
        for (double invalid : new double[]{-1.000001, .200001, Double.NaN}) {
            Map<String, Object> fields = new LinkedHashMap<>(SettingsValues.encode(new VrSettings()));
            fields.put("eyeSeparation", invalid);
            try { new PhoneProfile(fields); fail(); } catch (IllegalArgumentException expected) { }
        }
    }
    @Test public void completeLegacyProfileMigratesWithoutLosingAnyOtherCommittedField() {
        VrSettings original = new VrSettings(); original.mode = "fps"; original.scale = .61f;
        original.eyeSeparation = -.72f; original.offsetY = -.21f; original.invertY = true;
        original.sensitivity = 2200; original.stabilization = .8f;
        Map<String, Object> legacy = SettingsValues.encodeForHost(original, false);
        assertEquals(10, legacy.size());
        PhoneProfile migrated = new PhoneProfile(legacy);
        assertTrue(migrated.hasSavedProfile()); assertEquals(0, migrated.snapshot().stabilization, 0);
        assertEquals(legacy, SettingsValues.encodeForHost(migrated.snapshot(), false));
        assertEquals(11, SettingsValues.encode(migrated.snapshot()).size());
        VrSettings nonDefaultBase = original.copy();
        assertEquals(0, SettingsValues.decode(legacy, nonDefaultBase, true).stabilization, 0);
    }
    @Test public void legacyMigrationDoesNotAcceptMissingRequiredFieldsOrExtraKeys() {
        Map<String, Object> incomplete = SettingsValues.encodeForHost(new VrSettings(), false);
        incomplete.remove("distance");
        assertThrows(IllegalArgumentException.class, () -> new PhoneProfile(incomplete));
        Map<String, Object> extra = SettingsValues.encodeForHost(new VrSettings(), false);
        extra.put("futureField", 0);
        assertThrows(IllegalArgumentException.class, () -> new PhoneProfile(extra));
    }
    @Test public void stabilizationWireValuesMustBeFiniteNumbersInsideClosedBounds() {
        for (Object invalid : new Object[]{"0.5", Boolean.TRUE, Double.NaN, Double.POSITIVE_INFINITY,
            Double.NEGATIVE_INFINITY, -.00001, 1.00001}) {
            Map<String, Object> fields = SettingsValues.encode(new VrSettings()); fields.put("stabilization", invalid);
            assertThrows(IllegalArgumentException.class, () -> new PhoneProfile(fields));
        }
        for (double valid : new double[]{0, .37, 1}) {
            Map<String, Object> fields = SettingsValues.encode(new VrSettings()); fields.put("stabilization", valid);
            assertEquals((float)valid, new PhoneProfile(fields).snapshot().stabilization, 0);
        }
    }
    @Test public void legacyHostPartialUpdateCannotEraseTheLocallySavedStabilization() {
        VrSettings saved = new VrSettings(); saved.stabilization = .76f;
        Map<String, Object> legacy = SettingsValues.encodeForHost(saved, false); legacy.put("scale", .64);
        VrSettings accepted = SettingsValues.decode(legacy, saved, false);
        PhoneProfile profile = new PhoneProfile(null); profile.commit(accepted);
        assertEquals(.76f, profile.snapshot().stabilization, 0); assertEquals(.64f, profile.snapshot().scale, 0);
        assertEquals(.76f, saved.stabilization, 0);
    }
    @Test public void freshProfileWaitsForAdvertisedExtendedValueBeforeSensorFallbackCanSendDefaults() {
        PhoneProfile fresh = new PhoneProfile(null);
        assertTrue(fresh.waitForExtendedSnapshot(true, false));
        assertFalse(fresh.waitForExtendedSnapshot(false, false));
        assertFalse(fresh.hasSavedProfile());
        VrSettings remote = new VrSettings(); remote.mode = "fps"; remote.stabilization = .72f;
        assertFalse(fresh.waitForExtendedSnapshot(true, true));
        VrSettings complete = SettingsValues.decode(SettingsValues.encode(remote), fresh.snapshot(), false);
        // The no-sensor fallback changes mode, while preserving the now-known host filter value.
        complete.mode = "full"; fresh.commit(complete);
        assertEquals(.72f, fresh.snapshot().stabilization, 0); assertEquals("full", fresh.snapshot().mode);
    }
    @Test public void explicitSavedPhoneProfileStillWinsTheInitialLegacyCapabilitySnapshot() {
        PhoneProfile saved = new PhoneProfile(null); VrSettings local = new VrSettings(); local.stabilization = .81f;
        saved.commit(local); assertFalse(saved.waitForExtendedSnapshot(true, false));
        assertEquals(.81f, saved.snapshot().stabilization, 0);
    }
}
