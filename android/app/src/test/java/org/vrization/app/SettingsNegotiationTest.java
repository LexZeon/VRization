package org.vrization.app;

import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.Map;
import org.junit.Test;
import org.vrization.core.VrSettings;
import static org.junit.Assert.*;

public final class SettingsNegotiationTest {
    @Test public void oldHostEstablishesButReceivesOnlyLegacyFieldsWhileLocalProfileKeepsTheValue() {
        HostSessionGate gate = new HostSessionGate();
        assertFalse(gate.supportsStabilization()); assertTrue(gate.receive(HostSessionGateTest.legacyHello()));
        assertFalse(gate.supportsStabilization());
        VrSettings local = new VrSettings(); local.stabilization = .68f;
        Map<String, Object> wire = SettingsValues.encodeForHost(local, gate.supportsStabilization());
        assertEquals(10, wire.size()); assertFalse(wire.containsKey("stabilization"));
        PhoneProfile profile = new PhoneProfile(null); profile.commit(local);
        assertEquals(.68d, (Double) SettingsValues.encode(profile.snapshot()).get("stabilization"), 0);
    }
    @Test public void validElevenFieldHelloEnablesTheFirstSavedProfileSend() {
        HostSessionGate gate = new HostSessionGate(); assertTrue(gate.receive(HostSessionGateTest.hello()));
        assertTrue(gate.supportsStabilization());
        VrSettings local = new VrSettings(); local.stabilization = .87f;
        Map<String, Object> firstSend = SettingsValues.encodeForHost(local, gate.supportsStabilization());
        assertEquals(.87d, (Double) firstSend.get("stabilization"), 0); assertEquals(11, firstSend.size());
    }
    @Test public void legacyRelayHelloWithCapabilitiesEnablesTheFirstSendWithoutRequiringAnotherHello() {
        HostSessionGate gate = new HostSessionGate(); Map<String, Object> hello = HostSessionGateTest.legacyHello();
        hello.put("capabilities", Arrays.asList("future-feature", "stabilization"));
        assertTrue(gate.receive(hello)); assertTrue(gate.supportsStabilization());
        VrSettings local = new VrSettings(); local.stabilization = .6f;
        assertTrue(SettingsValues.encodeForHost(local, gate.supportsStabilization()).containsKey("stabilization"));
        Map<String, Object> upgraded = HostSessionGateTest.message("settings");
        upgraded.put("settings", SettingsValues.encode(local));
        assertFalse(gate.receive(upgraded)); assertTrue(gate.isEstablished());
    }
    @Test public void validCurrentSettingsCanUpgradeAnAlreadyEstablishedLegacySession() {
        HostSessionGate gate = new HostSessionGate(); gate.receive(HostSessionGateTest.legacyHello());
        Map<String, Object> update = HostSessionGateTest.message("settings");
        update.put("settings", SettingsValues.encode(new VrSettings()));
        assertFalse(gate.receive(update)); assertTrue(gate.supportsStabilization());
    }
    @Test public void invalidExtendedHelloCannotAdvertiseSupportOrRestoreAProfile() {
        HostSessionGate gate = new HostSessionGate(); Map<String, Object> hello = HostSessionGateTest.hello();
        Map<String, Object> fields = SettingsValues.encode(new VrSettings()); fields.put("stabilization", Double.NaN);
        hello.put("settings", fields); hello.put("capabilities", Arrays.asList("stabilization"));
        assertThrows(IllegalArgumentException.class, () -> gate.receive(hello));
        assertFalse(gate.isEstablished()); assertFalse(gate.supportsStabilization());
    }
    @Test public void capabilityMustBeAnExactArrayEntryAndANewSessionStartsUnsupported() {
        HostSessionGate gate = new HostSessionGate(); Map<String, Object> hello = HostSessionGateTest.legacyHello();
        hello.put("capabilities", Arrays.asList("stabilization-extra")); gate.receive(hello);
        assertFalse(gate.supportsStabilization());
        gate = new HostSessionGate(); gate.receive(HostSessionGateTest.hello()); assertTrue(gate.supportsStabilization());
        gate.fail(); assertFalse(gate.supportsStabilization());
        assertFalse(new HostSessionGate().supportsStabilization());
    }
    @Test public void nonArrayCapabilitiesCannotAdvertiseSupportOrEstablishTheSession() {
        HostSessionGate gate = new HostSessionGate(); Map<String, Object> hello = HostSessionGateTest.legacyHello();
        hello.put("capabilities", "stabilization");
        assertThrows(IllegalArgumentException.class, () -> gate.receive(hello));
        assertFalse(gate.isEstablished()); assertFalse(gate.supportsStabilization());
    }
    @Test public void mixedCapabilitiesCannotAdvertiseSupportOrEstablishTheSession() {
        HostSessionGate gate = new HostSessionGate(); Map<String, Object> hello = HostSessionGateTest.legacyHello();
        hello.put("capabilities", Arrays.asList("stabilization", 1));
        assertThrows(IllegalArgumentException.class, () -> gate.receive(hello));
        assertFalse(gate.isEstablished()); assertFalse(gate.supportsStabilization());
    }
    @Test public void queuedPreviousSocketCapabilityCannotEnableTheNewLegacyConnection() {
        ArrayDeque<Runnable> owner = new ArrayDeque<>(); SessionDispatcher sessions = new SessionDispatcher(owner::add);
        boolean[] supports = {false}; long old = sessions.invalidate();
        HostSessionGate previous = new HostSessionGate(); previous.receive(HostSessionGateTest.hello());
        sessions.dispatch(old, () -> supports[0] = previous.supportsStabilization());
        long current = sessions.invalidate(); HostSessionGate legacy = new HostSessionGate();
        legacy.receive(HostSessionGateTest.legacyHello());
        sessions.dispatch(current, () -> supports[0] = legacy.supportsStabilization());
        owner.remove().run(); assertFalse(supports[0]); owner.remove().run(); assertFalse(supports[0]);
    }
}
