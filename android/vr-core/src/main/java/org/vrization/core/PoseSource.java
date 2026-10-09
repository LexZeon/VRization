package org.vrization.core;

/** Replaceable tracking interface for embedding VRization into another Android app/game. */
public interface PoseSource {
    interface Listener {
        /** Relative radians: positive yaw right, pitch up, roll clockwise. */
        void onPose(float yaw, float pitch, float roll, long timestampNanos);
    }
    boolean isAvailable();
    void start(Listener listener);
    void stop();
    void recenter();
}
