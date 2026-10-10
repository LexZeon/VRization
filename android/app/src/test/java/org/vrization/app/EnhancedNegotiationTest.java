package org.vrization.app;

import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.Test;
import org.vrization.core.VrSettings;
import static org.junit.Assert.*;

public final class EnhancedNegotiationTest {
    private static VrSettings enhanced() {
        VrSettings value = new VrSettings(); value.mode = VrSettings.ENHANCED_FIRST_PERSON;
        value.scale = .61f; value.offsetY = -.14f; value.eyeSeparation = -.6f;
        value.fov = 103; value.stabilization = .4f; return value;
    }
    private static Map<String, Object> enhancedHello(boolean negotiated) {
        Map<String, Object> hello = HostSessionGateTest.hello();
        hello.put("capabilities", Arrays.asList("stabilization", "enhanced-first-person"));
        hello.put("enhancedFirstPerson", negotiated); return hello;
    }
    @Test public void strictProfileRoundTripPreservesEnhancedModeAndAllOpticsWithoutAddingFields() {
        VrSettings value = enhanced();
        PhoneProfile first = new PhoneProfile(null); first.commit(value);
        PhoneProfile restored = new PhoneProfile(SettingsValues.encode(first.snapshot()));
        assertEquals(SettingsValues.encode(value), SettingsValues.encode(restored.snapshot()));
        assertEquals(11, SettingsValues.encode(value).size());
        Map<String, Object> wrong = SettingsValues.encode(value); wrong.put("mode", "fps_enhanced_extra");
        assertThrows(IllegalArgumentException.class, () -> new PhoneProfile(wrong));
    }
    @Test public void oldHostReceivesKnownFpsWhileLocalSavedProjectionAndItsAckStayEnhanced() {
        VrSettings local = enhanced(); HostSessionGate legacy = new HostSessionGate();
        legacy.receive(HostSessionGateTest.legacyHello()); assertFalse(legacy.supportsEnhancedFirstPerson());
        Map<String, Object> wire = SettingsValues.encodeForHost(local, false, false);
        assertEquals("fps", wire.get("mode")); assertEquals(10, wire.size());
        assertEquals("fps_enhanced", local.mode);
        SettingsSync sync = new SettingsSync(); sync.edited(); long sequence = sync.nextSequence(); sync.sent(sequence, local);
        VrSettings echo = SettingsValues.decodeFromHost(wire, local, false);
        assertEquals("fps_enhanced", echo.mode); assertEquals(.4f, echo.stabilization, 0);
        assertTrue(sync.accept(echo, 9L, sequence));
        PhoneProfile saved = new PhoneProfile(SettingsValues.encode(echo));
        assertEquals("fps_enhanced", saved.snapshot().mode);
        Map<String, Object> geometry = new LinkedHashMap<>(); geometry.put("scale", .73);
        assertEquals("fps_enhanced", SettingsValues.decodeFromHost(geometry, echo, false).mode);
    }
    @Test public void currentHostGetsEnhancedOnTheFirstProfileSendAndMayExplicitlyChangeTheMode() {
        HostSessionGate current = new HostSessionGate(); assertTrue(current.receive(enhancedHello(true)));
        assertTrue(current.supportsEnhancedFirstPerson()); assertFalse(current.waitsForEnhancedSnapshot());
        VrSettings local = enhanced();
        assertEquals("fps_enhanced", SettingsValues.encodeForHost(local, true, true).get("mode"));
        Map<String, Object> ordinary = new LinkedHashMap<>(); ordinary.put("mode", "fps");
        assertEquals("fps", SettingsValues.decodeFromHost(ordinary, local, true).mode);
        ordinary.put("mode", "full");
        assertEquals("full", SettingsValues.decodeFromHost(ordinary, local, false).mode);
    }
    @Test public void usbRelayInitialFallbackWaitsForTheExplicitNegotiatedSettingsMarker() {
        HostSessionGate gate = new HostSessionGate(); gate.receive(enhancedHello(false));
        PhoneProfile fresh = new PhoneProfile(null); PhoneProfile saved = new PhoneProfile(SettingsValues.encode(enhanced()));
        assertTrue(gate.supportsEnhancedFirstPerson()); assertTrue(gate.waitsForEnhancedSnapshot());
        assertTrue(fresh.waitForEnhancedSnapshot(gate.waitsForEnhancedSnapshot()));
        assertFalse(saved.waitForEnhancedSnapshot(gate.waitsForEnhancedSnapshot()));
        Map<String, Object> queued = HostSessionGateTest.message("settings");
        queued.put("settings", SettingsValues.encode(new VrSettings())); queued.put("enhancedFirstPerson", false);
        gate.receive(queued); assertTrue(gate.waitsForEnhancedSnapshot());
        queued.remove("enhancedFirstPerson"); gate.receive(queued); assertTrue(gate.waitsForEnhancedSnapshot());
        queued.put("enhancedFirstPerson", true); queued.put("settings", SettingsValues.encode(enhanced()));
        gate.receive(queued); assertFalse(gate.waitsForEnhancedSnapshot());
        assertFalse(fresh.waitForEnhancedSnapshot(gate.waitsForEnhancedSnapshot()));
    }
    @Test public void queryNegotiatedHelloDoesNotWaitForeverAndLegacyHostNeverWaits() {
        HostSessionGate query = new HostSessionGate(); query.receive(enhancedHello(true));
        assertFalse(query.waitsForEnhancedSnapshot());
        HostSessionGate legacy = new HostSessionGate(); legacy.receive(HostSessionGateTest.legacyHello());
        assertFalse(legacy.waitsForEnhancedSnapshot());
    }
    @Test public void enhancedModeMustBeAdvertisedAsAnExactCapability() {
        for (Object capabilities : new Object[]{Arrays.asList("enhanced-first-person-extra"), "enhanced-first-person",
            Arrays.asList("enhanced-first-person", 1)}) {
            HostSessionGate gate = new HostSessionGate(); Map<String, Object> hello = enhancedHello(true);
            hello.put("settings", SettingsValues.encode(enhanced())); hello.put("capabilities", capabilities);
            assertThrows(IllegalArgumentException.class, () -> gate.receive(hello));
            assertFalse(gate.isEstablished()); assertFalse(gate.supportsEnhancedFirstPerson());
        }
        HostSessionGate valid = new HostSessionGate(); Map<String, Object> hello = enhancedHello(true);
        hello.put("settings", SettingsValues.encode(enhanced()));
        assertTrue(valid.receive(hello)); assertTrue(valid.supportsEnhancedFirstPerson());
    }
    @Test public void unadvertisedEnhancedUpdatesAndMalformedNegotiationPoisonTheSession() {
        HostSessionGate legacy = new HostSessionGate(); legacy.receive(HostSessionGateTest.legacyHello());
        Map<String, Object> wrong = HostSessionGateTest.message("settings"); wrong.put("settings", SettingsValues.encode(enhanced()));
        assertThrows(IllegalArgumentException.class, () -> legacy.receive(wrong)); assertFalse(legacy.isEstablished());
        assertThrows(IllegalArgumentException.class,
            () -> SettingsValues.decodeFromHost(SettingsValues.encode(enhanced()), new VrSettings(), false));
        for (Object marker : new Object[]{"true", 1, null}) {
            HostSessionGate gate = new HostSessionGate(); Map<String, Object> hello = enhancedHello(false);
            hello.put("enhancedFirstPerson", marker);
            assertThrows(IllegalArgumentException.class, () -> gate.receive(hello)); assertFalse(gate.supportsEnhancedFirstPerson());
        }
        HostSessionGate gate = new HostSessionGate(); gate.receive(enhancedHello(false));
        wrong.put("enhancedFirstPerson", 1);
        assertThrows(IllegalArgumentException.class, () -> gate.receive(wrong)); assertFalse(gate.waitsForEnhancedSnapshot());
    }
    @Test public void failedSessionCannotAdvertiseSupportAndNewConnectionDoesNotInheritIt() {
        HostSessionGate previous = new HostSessionGate(); previous.receive(enhancedHello(true));
        assertTrue(previous.supportsEnhancedFirstPerson()); previous.fail(); assertFalse(previous.supportsEnhancedFirstPerson());
        HostSessionGate newLegacy = new HostSessionGate(); newLegacy.receive(HostSessionGateTest.legacyHello());
        assertFalse(newLegacy.supportsEnhancedFirstPerson());
    }
}
