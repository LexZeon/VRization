package org.vrization.app;

import java.util.LinkedHashMap;
import java.util.Map;

/** Separate negotiated video control; its paused status never authorizes input Resume. */
final class VideoRefreshValues {
    static final String CAPABILITY = "video-refresh";
    static final long MAX_SAFE = 9007199254740991L;
    static final class Ack {
        final long epoch, requestId;
        final boolean paused;
        Ack(long epoch, long requestId, boolean paused) {
            this.epoch = epoch; this.requestId = requestId; this.paused = paused;
        }
    }
    static Map<String, Object> request(long epoch, long requestId) {
        HostSessionGate.integer(epoch, 1, MAX_SAFE); HostSessionGate.integer(requestId, 1, MAX_SAFE);
        Map<String, Object> value = new LinkedHashMap<>();
        value.put("v", 1); value.put("type", "refreshVideo");
        value.put("epoch", epoch); value.put("requestId", requestId); return value;
    }
    static Ack acknowledgement(Map<String, Object> value) {
        if (value == null) throw new IllegalArgumentException("Missing video acknowledgement");
        HostSessionGate.integer(value.get("v"), 1, 1);
        if (!"videoRefresh".equals(value.get("type")) || !(value.get("paused") instanceof Boolean))
            throw new IllegalArgumentException("Invalid video acknowledgement");
        return new Ack(HostSessionGate.integer(value.get("epoch"), 1, MAX_SAFE),
            HostSessionGate.integer(value.get("requestId"), 1, MAX_SAFE), (Boolean) value.get("paused"));
    }
}
