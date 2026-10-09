package org.vrization.core;

/** Mutable settings value. Pass copies between UI, networking and rendering threads. */
public final class VrSettings {
    public String mode = "full";
    public float scale = .85f;
    public float offsetX = 0f;
    public float offsetY = 0f;
    public float eyeSeparation = .03f;
    public float fov = 80f;
    public float distance = 3f;
    public float distortion = 0f;
    public float sensitivity = 1000f;
    public boolean invertY = false;

    public VrSettings copy() {
        VrSettings result = new VrSettings();
        result.mode = mode; result.scale = scale; result.offsetX = offsetX;
        result.offsetY = offsetY; result.eyeSeparation = eyeSeparation;
        result.fov = fov; result.distance = distance; result.distortion = distortion;
        result.sensitivity = sensitivity; result.invertY = invertY;
        return result;
    }

    public void normalize() {
        if (!"full".equals(mode) && !"cinema".equals(mode) && !"fps".equals(mode)) mode = "full";
        scale = clamp(scale, .5f, 1f); offsetX = clamp(offsetX, -.3f, .3f);
        offsetY = clamp(offsetY, -.3f, .3f); eyeSeparation = clamp(eyeSeparation, -1f, .2f);
        fov = clamp(fov, 50f, 110f); distance = clamp(distance, 1f, 8f);
        distortion = clamp(distortion, 0f, .5f); sensitivity = clamp(sensitivity, 100f, 3000f);
    }

    private static float clamp(float value, float low, float high) {
        if (Float.isNaN(value) || Float.isInfinite(value)) return low;
        return Math.max(low, Math.min(high, value));
    }
}
