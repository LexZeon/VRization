package org.vrization.app;

import java.util.Map;
import java.util.List;
import java.util.Arrays;
import java.util.HashSet;

/** Immutable video/input pairing, never part of persistent VR settings. */
final class StreamSession {
    final long epoch;
    final boolean accepted, stereo, hmd, explicit;
    private StreamSession(long epoch, boolean accepted, boolean stereo, boolean hmd, boolean explicit) {
        this.epoch = epoch; this.accepted = accepted;
        this.stereo = stereo; this.hmd = hmd; this.explicit = explicit;
    }
    static StreamSession legacy() { return new StreamSession(0, true, false, false, false); }
    static StreamSession parse(Object raw, List<?> caps) {
        if (raw == null) return legacy();
        if (!(raw instanceof Map)) throw new IllegalArgumentException("Invalid stream session");
        Map<?, ?> fields = (Map<?, ?>) raw;
        if (!fields.keySet().equals(new HashSet<>(Arrays.asList("v", "epoch", "accepted", "streamLayout", "inputTarget"))))
            throw new IllegalArgumentException("Incomplete stream session");
        HostSessionGate.integer(fields.get("v"), 1, 1);
        long epoch = HostSessionGate.integer(fields.get("epoch"), 1, 9007199254740991L);
        if (!(fields.get("accepted") instanceof Boolean)) throw new IllegalArgumentException("Invalid session acceptance");
        boolean stereo = "sbs".equals(fields.get("streamLayout")), hmd = "virtual-hmd".equals(fields.get("inputTarget"));
        if ((!stereo && !"mono".equals(fields.get("streamLayout")))
            || (!hmd && !"mouse".equals(fields.get("inputTarget"))) || stereo != hmd)
            throw new IllegalArgumentException("Invalid video/input pairing");
        if (stereo && (!ClientVariant.EXPERIMENTAL || !caps.contains("stereo-sbs") || !caps.contains("hmd-orientation")))
            throw new IllegalArgumentException("Unsupported stereo HMD session");
        return new StreamSession(epoch, (Boolean) fields.get("accepted"), stereo, hmd, true);
    }
    StreamSession update(StreamSession next) {
        if (explicit != next.explicit || epoch != next.epoch || stereo != next.stereo
            || hmd != next.hmd || (accepted && !next.accepted))
            throw new IllegalArgumentException("Stream session changed; reconnect required");
        return next;
    }
}
