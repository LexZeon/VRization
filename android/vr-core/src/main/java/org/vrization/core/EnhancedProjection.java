package org.vrization.core;

/** Pure inverse equidistant projection, matching the GLES fragment shader.
 * Coordinates are centered and y points up. Null denotes a black sample.
 * This remaps the existing 2D image; it does not reconstruct stereo scene depth.
 */
public final class EnhancedProjection {
    private EnhancedProjection() { }
    private static boolean finite(float value) { return !Float.isNaN(value) && !Float.isInfinite(value); }
    public static float[] source(float x, float y, float fov) {
        if (!finite(x) || !finite(y) || !finite(fov) || fov < 50 || fov > 110)
            throw new IllegalArgumentException("Invalid enhanced projection input");
        if (Math.abs(x) > 1 || Math.abs(y) > 1) return null;
        double r = Math.hypot(x, y);
        if (r < 1e-6) return new float[]{0, 0};
        double a = Math.toRadians(fov) * .5;
        double factor = Math.tan(r * a) / (r * Math.tan(a));
        double sourceX = x * factor, sourceY = y * factor;
        if (Math.abs(sourceX) > 1 || Math.abs(sourceY) > 1) return null;
        return new float[]{(float)sourceX, (float)sourceY};
    }
}
