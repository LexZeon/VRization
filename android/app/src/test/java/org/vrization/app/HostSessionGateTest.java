package org.vrization.app;

import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.Test;
import org.vrization.core.VrSettings;
import static org.junit.Assert.*;

public final class HostSessionGateTest {
    static Map<String, Object> message(String type) {
        Map<String, Object> result = new LinkedHashMap<>(); result.put("v", 1); result.put("type", type); return result;
    }
    static Map<String, Object> hello() {
        Map<String, Object> hello = message("hello"), stream = new LinkedHashMap<>();
        hello.put("name", "VRization"); hello.put("version", "0.3.0"); hello.put("settings", SettingsValues.encode(new VrSettings()));
        stream.put("codec", "jpeg"); stream.put("fps", 60); stream.put("maxWidth", 640);
        hello.put("stream", stream); hello.put("mouseArmed", false); hello.put("revision", 3); return hello;
    }
    @Test public void validHelloIsTheOnlyEstablishmentEventAndAllowsSettingsAndVideo() {
        HostSessionGate gate = new HostSessionGate(); assertFalse(gate.isEstablished());
        assertTrue(gate.receive(hello())); gate.receiveJpeg(1024);
        Map<String, Object> settings = message("settings"), fields = new LinkedHashMap<>(); fields.put("offsetX", .3);
        settings.put("settings", fields); settings.put("revision", 4); settings.put("clientSeq", 1);
        assertFalse(gate.receive(settings)); assertTrue(gate.isEstablished());
    }
    @Test public void preHelloMessagesOrVideoPoisonTheConnectionUntilRecreated() {
        HostSessionGate text = new HostSessionGate();
        try { text.receive(message("pong")); fail(); } catch (IllegalArgumentException expected) { }
        try { text.receive(hello()); fail(); } catch (IllegalArgumentException expected) { }
        HostSessionGate binary = new HostSessionGate();
        try { binary.receiveJpeg(4); fail(); } catch (IllegalArgumentException expected) { }
        try { binary.receive(hello()); fail(); } catch (IllegalArgumentException expected) { }
        assertTrue(new HostSessionGate().receive(hello()));
    }
    @Test public void malformedHelloDoesNotEstablishOrRestoreAPhoneProfile() {
        for (String field : new String[]{"v", "settings", "stream", "mouseArmed"}) {
            HostSessionGate gate = new HostSessionGate(); Map<String, Object> hello = hello();
            hello.put(field, field.equals("v") ? 1.0 : "invalid");
            try { gate.receive(hello); fail("Accepted bad " + field); } catch (IllegalArgumentException expected) { }
            assertFalse(gate.isEstablished());
        }
    }
    @Test public void repeatedHelloAndOversizedFrameEndTheExistingSession() {
        HostSessionGate gate = new HostSessionGate(); gate.receive(hello());
        try { gate.receive(hello()); fail(); } catch (IllegalArgumentException expected) { }
        assertFalse(gate.isEstablished());
        gate = new HostSessionGate(); gate.receive(hello());
        try { gate.receiveJpeg(8 * 1024 * 1024 + 1); fail(); } catch (IllegalArgumentException expected) { }
        assertFalse(gate.isEstablished());
    }
    @Test public void badSettingsSequenceCannotReachTheProfile() {
        HostSessionGate gate = new HostSessionGate(); gate.receive(hello());
        Map<String, Object> settings = message("settings"); settings.put("settings", SettingsValues.encode(new VrSettings()));
        settings.put("clientSeq", -1);
        try { gate.receive(settings); fail(); } catch (IllegalArgumentException expected) { }
        assertFalse(gate.isEstablished());
    }
}
