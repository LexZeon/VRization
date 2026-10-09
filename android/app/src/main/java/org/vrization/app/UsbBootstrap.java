package org.vrization.app;

import java.util.Map;

/** Validate discovery without letting an HTTP response redirect the phone off loopback. */
final class UsbBootstrap {
    static final String HOST = "127.0.0.1";
    static final int FORWARDED_PORT = 18765;
    static final String ENDPOINT = "http://127.0.0.1:18765/usb-bootstrap";
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
