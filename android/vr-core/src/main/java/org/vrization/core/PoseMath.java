package org.vrization.core;

/** Platform-independent angle math, reusable by other Java renderers and tracking adapters. */
public final class PoseMath {
    private PoseMath() { }

    /** Maps radians into [-pi, pi]. Nonfinite input is rejected rather than contaminating rendering. */
    public static float wrap(float radians) {
        if (Float.isNaN(radians) || Float.isInfinite(radians)) throw new IllegalArgumentException("Angle must be finite");
        double result = radians % (2.0 * Math.PI);
        if (result > Math.PI) result -= 2.0 * Math.PI;
        if (result < -Math.PI) result += 2.0 * Math.PI;
        return (float) result;
    }

    public static float relative(float current, float origin) { return wrap(current - origin); }

    /** Recenter takes effect on the next sample, so the first delivered pose is always neutral. */
    public static final class Center {
        private boolean initialized;
        private float yaw, pitch, roll;
        public void recenter() { initialized = false; }
        public float[] sample(float currentYaw, float currentPitch, float currentRoll) {
            // Validate before storing origin.
            wrap(currentYaw); wrap(currentPitch); wrap(currentRoll);
            if (!initialized) {
                yaw = currentYaw; pitch = currentPitch; roll = currentRoll; initialized = true;
            }
            return new float[]{relative(currentYaw, yaw), relative(currentPitch, pitch), relative(currentRoll, roll)};
        }
    }

    /**
     * Exact recentering in screen coordinates, including an initially tilted phone.
     * Input is row-major screen-to-world rotation after display-orientation remapping.
     * Output matches the renderer: yaw right, pitch up, roll clockwise, all radians.
     */
    public static final class RotationCenter {
        private final float[] origin = new float[9];
        private final float[] relative = new float[9];
        private boolean initialized;

        public void recenter() { initialized = false; }

        public float[] sample(float[] screenToWorld) {
            if (screenToWorld == null || screenToWorld.length != 9) throw new IllegalArgumentException("Expected 3x3 rotation");
            for (float value : screenToWorld) {
                if (Float.isNaN(value) || Float.isInfinite(value)) throw new IllegalArgumentException("Rotation must be finite");
            }
            if (!initialized) {
                System.arraycopy(screenToWorld, 0, origin, 0, 9);
                initialized = true;
                return new float[]{0, 0, 0};
            }
            // Orthogonal rotation inverse is transpose. R0^T R maps current screen
            // coordinates into the screen basis captured when the user recentered.
            for (int row = 0; row < 3; row++) {
                for (int col = 0; col < 3; col++) {
                    relative[row * 3 + col] = origin[row] * screenToWorld[col]
                        + origin[3 + row] * screenToWorld[3 + col]
                        + origin[6 + row] * screenToWorld[6 + col];
                }
            }
            float yaw = (float) Math.atan2(-relative[2], relative[8]);
            float pitch = (float) Math.asin(Math.max(-1f, Math.min(1f, -relative[5])));
            float roll = (float) Math.atan2(-relative[3], relative[4]);
            return new float[]{yaw, pitch, roll};
        }
    }
}
