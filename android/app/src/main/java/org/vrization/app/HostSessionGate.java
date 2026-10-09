package org.vrization.app;

import java.util.Map;
import org.vrization.core.VrSettings;

/** A transport opening is not an established protocol session. Fail closed until reconnect. */
final class HostSessionGate {
    private boolean established, failed;
    boolean isEstablished() { return established && !failed; }
    void fail() { failed = true; }
    @SuppressWarnings("unchecked")
    private static Map<String, Object> object(Object value) {
        if (!(value instanceof Map)) throw new IllegalArgumentException("Expected object");
        return (Map<String, Object>) value;
    }
    static long integer(Object value, long min, long max) {
        if (!(value instanceof Integer) && !(value instanceof Long)) throw new IllegalArgumentException("Expected integer");
        long number = ((Number) value).longValue();
        if (number < min || number > max) throw new IllegalArgumentException("Integer outside bounds");
        return number;
    }
    static Long sequence(Map<String, Object> message, String key) {
        return message.containsKey(key) ? integer(message.get(key), 0, 9007199254740991L) : null;
    }
    /** Returns true exactly once, when a complete valid host hello establishes the session. */
    boolean receive(Map<String, Object> message) {
        try {
            if (failed || message == null) throw new IllegalArgumentException("Protocol session unavailable");
            integer(message.get("v"), 1, 1);
            Object type = message.get("type");
            if (!(type instanceof String)) throw new IllegalArgumentException("Expected message type");
            sequence(message, "revision"); sequence(message, "clientSeq");
            if (!established) {
                if (!"hello".equals(type) || !(message.get("name") instanceof String)
                    || ((String) message.get("name")).isEmpty() || !(message.get("version") instanceof String)
                    || ((String) message.get("version")).isEmpty()) throw new IllegalArgumentException("Expected host hello");
                SettingsValues.decode(object(message.get("settings")), new VrSettings(), true);
                Map<String, Object> stream = object(message.get("stream"));
                if (!"jpeg".equals(stream.get("codec"))) throw new IllegalArgumentException("Unsupported codec");
                integer(stream.get("fps"), 5, 60); integer(stream.get("maxWidth"), 320, 3840);
                if (!(message.get("mouseArmed") instanceof Boolean)) throw new IllegalArgumentException("Invalid input state");
                established = true; return true;
            }
            if ("settings".equals(type)) SettingsValues.decode(object(message.get("settings")), new VrSettings(), false);
            else if ("error".equals(type)) {
                if (!(message.get("message") instanceof String)) throw new IllegalArgumentException("Invalid host error");
            } else if (!"pong".equals(type)) throw new IllegalArgumentException("Unexpected host message");
            return false;
        } catch (IllegalArgumentException error) { failed = true; throw error; }
    }
    void receiveJpeg(int size) {
        if (!isEstablished() || size < 4 || size > 8 * 1024 * 1024) {
            failed = true; throw new IllegalArgumentException("Unexpected video frame");
        }
    }
}
