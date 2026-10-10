package org.vrization.app;

import org.vrization.core.TransportEndpoints;

import java.util.Map;

/** Validate discovery without letting an HTTP response redirect the phone off loopback. */
final class UsbBootstrap {
    static final String HOST = TransportEndpoints.USB_HOST;
    static final int FORWARDED_PORT = ClientVariant.VIDEO_PORT;
    static final String ENDPOINT = ClientVariant.USB_BOOTSTRAP;
    final int computerPort;
    final String token;
    private UsbBootstrap(int computerPort, String token) { this.computerPort = computerPort; this.token = token; }
    static UsbBootstrap parse(Map<String, Object> fields) {
        Object version = fields.get("v"), port = fields.get("port"), token = fields.get("token");
        if (!integer(version) || ((Number) version).longValue() != 1 || !"VRization".equals(fields.get("name"))
            || !(fields.get("version") instanceof String) || !integer(port)
            || ((Number) port).longValue() < 1 || ((Number) port).longValue() > 65535
            || !(token instanceof String) || !((String) token).matches("[0-9]{6}")) {
            throw new IllegalArgumentException("Invalid USB discovery response");
        }
        return new UsbBootstrap(((Number) port).intValue(), (String) token);
    }
    private static boolean integer(Object value) { return value instanceof Integer || value instanceof Long; }
}
