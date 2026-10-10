package org.vrization.app;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import org.vrization.core.OrientationMath;

/** Strict orientation packet encoder, separate from JSON and the mouse path. */
final class HmdPoseValues {
    private HmdPoseValues() { }
    static Map<String, Object> encode(StreamSession session, long sequence, long timeUs,
                                      float[] quaternion, boolean trackingValid) {
        if (!session.explicit || !session.accepted || !session.hmd)
            throw new IllegalArgumentException("HMD route is not negotiated");
        HostSessionGate.integer(sequence, 1, 9007199254740991L);
        HostSessionGate.integer(timeUs, 0, 9007199254740991L);
        Map<String, Object> packet = new LinkedHashMap<>();
        packet.put("v", 1); packet.put("type", "hmdPose"); packet.put("epoch", session.epoch);
        packet.put("seq", sequence); packet.put("timeUs", timeUs); packet.put("trackingValid", trackingValid);
        if (trackingValid) {
            OrientationMath.validateQuaternion(quaternion);
            ArrayList<Float> values = new ArrayList<>(4);
            for (float value : quaternion) values.add(value);
            packet.put("q", values);
        }
        return packet;
    }
}
