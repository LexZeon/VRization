package org.vrization.core;

/** Native compositor pixels already contain each eye's perspective. No scene projection twice. */
public final class StereoProjection {
    private StereoProjection() { }
    public static VrSettings viewingSettings(VrSettings settings) {
        VrSettings copy = settings.copy(); copy.mode = "full"; return copy;
    }
    public static boolean validDimensions(int packedWidth, int height, int textureLimit) {
        return packedWidth >= 2 && packedWidth % 2 == 0 && height >= 1
            && packedWidth <= textureLimit && height <= textureLimit;
    }
    public static float eyeAspect(int packedWidth, int height) {
        if (!validDimensions(packedWidth, height, Integer.MAX_VALUE))
            throw new IllegalArgumentException("Invalid packed stereo dimensions");
        return packedWidth / (2f * height);
    }
    /** CPU reference for the shader, including half-texel filtering protection at the seam. */
    public static float sourceU(float normalizedX, int eye, int packedWidth) {
        if (Float.isNaN(normalizedX) || Float.isInfinite(normalizedX)
            || normalizedX < -1 || normalizedX > 1 || eye < 0 || eye > 1
            || packedWidth < 2 || packedWidth % 2 != 0)
            throw new IllegalArgumentException("Invalid stereo sample");
        float halfTexel = .5f / packedWidth;
        return Math.max(eye * .5f + halfTexel,
            Math.min((eye + 1) * .5f - halfTexel, (normalizedX * .5f + .5f + eye) * .5f));
    }
}
