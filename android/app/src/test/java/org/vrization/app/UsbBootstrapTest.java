package org.vrization.app;

import java.util.HashMap;
import java.util.Map;
import org.junit.Test;
import static org.junit.Assert.*;

public final class UsbBootstrapTest {
    private static Map<String, Object> response() {
        Map<String, Object> fields = new HashMap<>();
        fields.put("v", 1); fields.put("name", "VRization"); fields.put("version", "0.2.0");
        fields.put("port", 8765); fields.put("token", "001234");
        return fields;
    }
    @Test public void discoveryPreservesLeadingZeroCodeAndNeverChangesPhoneDestination() {
        Map<String, Object> fields = response();
        fields.put("port", 19345); fields.put("host", "evil.example"); fields.put("url", "http://evil.example");
        UsbBootstrap value = UsbBootstrap.parse(fields);
        assertEquals("001234", value.token); assertEquals(19345, value.computerPort);
        assertEquals("127.0.0.1", UsbBootstrap.HOST); assertEquals(18765, UsbBootstrap.FORWARDED_PORT);
        assertEquals("http://127.0.0.1:18765/usb-bootstrap", UsbBootstrap.ENDPOINT);
    }
    @Test public void malformedPairingMaterialIsRejectedWithoutCoercion() {
        for (Object token : new Object[]{123456, "12345", "1234567", "１２３４５６", "123&45", null}) {
            Map<String, Object> fields = response(); fields.put("token", token);
            assertThrows(IllegalArgumentException.class, () -> UsbBootstrap.parse(fields));
        }
    }
    @Test public void bootstrapVersionIdentityAndPortAreStrict() {
        for (Object version : new Object[]{true, 1.0, "1", 2, null}) {
            Map<String, Object> fields = response(); fields.put("v", version);
            assertThrows(IllegalArgumentException.class, () -> UsbBootstrap.parse(fields));
        }
        for (Object port : new Object[]{true, "8765", 8765.0, 0, 65536, null}) {
            Map<String, Object> fields = response(); fields.put("port", port);
            assertThrows(IllegalArgumentException.class, () -> UsbBootstrap.parse(fields));
        }
        Map<String, Object> fields = response(); fields.put("name", "Another app");
        assertThrows(IllegalArgumentException.class, () -> UsbBootstrap.parse(fields));
    }
}
