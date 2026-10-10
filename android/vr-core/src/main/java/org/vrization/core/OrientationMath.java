package org.vrization.core;

/** Screen-basis recentered orientation, Hamilton quaternion xyzw, right-handed +X right/+Y up/-Z forward.
 * No Euler conversion, mouse gain, position prediction or fabricated tracking.
 */
public final class OrientationMath {
    private OrientationMath() { }
    private static boolean finite(float value) { return !Float.isNaN(value) && !Float.isInfinite(value); }

    public static void validateQuaternion(float[] quaternion) {
        if (quaternion == null || quaternion.length != 4)
            throw new IllegalArgumentException("Expected xyzw quaternion");
        double normSquared = 0;
        for (float value : quaternion) {
            if (!finite(value)) throw new IllegalArgumentException("Nonfinite quaternion");
            normSquared += value * value;
        }
        if (Math.abs(normSquared - 1) > .002) throw new IllegalArgumentException("Quaternion must be normalized");
    }

    /** Convert a finite, proper, orthonormal row-major 3x3 matrix without losing roll or crossing Euler poles. */
    public static float[] quaternion(float[] matrix) {
        if (matrix == null || matrix.length != 9) throw new IllegalArgumentException("Expected 3x3 rotation");
        for (float value : matrix) if (!finite(value)) throw new IllegalArgumentException("Nonfinite rotation");
        for (int row = 0; row < 3; row++) for (int other = 0; other < 3; other++) {
            double dot = 0;
            for (int axis = 0; axis < 3; axis++) dot += matrix[3 * row + axis] * matrix[3 * other + axis];
            if (Math.abs(dot - (row == other ? 1 : 0)) > .02)
                throw new IllegalArgumentException("Nonorthogonal rotation");
        }
        float[] m = matrix;
        double determinant = m[0] * (m[4] * m[8] - m[5] * m[7])
            - m[1] * (m[3] * m[8] - m[5] * m[6]) + m[2] * (m[3] * m[7] - m[4] * m[6]);
        if (Math.abs(determinant - 1) > .03) throw new IllegalArgumentException("Improper rotation");
        double x, y, z, w, trace = m[0] + m[4] + m[8];
        if (trace > 0) {
            double scale = Math.sqrt(trace + 1) * 2;
            w = scale / 4; x = (m[7] - m[5]) / scale; y = (m[2] - m[6]) / scale; z = (m[3] - m[1]) / scale;
        } else if (m[0] > m[4] && m[0] > m[8]) {
            double scale = Math.sqrt(1 + m[0] - m[4] - m[8]) * 2;
            w = (m[7] - m[5]) / scale; x = scale / 4; y = (m[1] + m[3]) / scale; z = (m[2] + m[6]) / scale;
        } else if (m[4] > m[8]) {
            double scale = Math.sqrt(1 + m[4] - m[0] - m[8]) * 2;
            w = (m[2] - m[6]) / scale; x = (m[1] + m[3]) / scale; y = scale / 4; z = (m[5] + m[7]) / scale;
        } else {
            double scale = Math.sqrt(1 + m[8] - m[0] - m[4]) * 2;
            w = (m[3] - m[1]) / scale; x = (m[2] + m[6]) / scale; y = (m[5] + m[7]) / scale; z = scale / 4;
        }
        double norm = Math.sqrt(x * x + y * y + z * z + w * w);
        float[] result = {(float) (x / norm), (float) (y / norm), (float) (z / norm), (float) (w / norm)};
        validateQuaternion(result);
        return result;
    }

    /** Session-local baseline. Caller applies the current display basis before supplying sensor fusion matrices. */
    public static final class Center {
        private float[] origin, previous;
        public void recenter() { origin = null; previous = null; }
        public float[] sample(float[] matrix) {
            quaternion(matrix); // Validate before capturing an origin; a bad sample is never identity tracking.
            if (origin == null) origin = matrix.clone();
            float[] relative = new float[9];
            // R_reference transpose times R_current: physical motion in the recentered screen coordinate basis.
            for (int row = 0; row < 3; row++) for (int column = 0; column < 3; column++) for (int k = 0; k < 3; k++)
                relative[row * 3 + column] += origin[k * 3 + row] * matrix[k * 3 + column];
            float[] result = quaternion(relative);
            // q and -q encode the same rotation. Keep their sign continuous over 180/360 degrees.
            if (previous != null) {
                float dot = 0;
                for (int k = 0; k < 4; k++) dot += result[k] * previous[k];
                if (dot < 0) for (int k = 0; k < 4; k++) result[k] = -result[k];
            }
            previous = result.clone();
            return result;
        }
    }
}
