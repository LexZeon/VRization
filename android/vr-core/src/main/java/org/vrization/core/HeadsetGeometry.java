package org.vrization.core;

/** Platform-independent headset editing in per-eye [-1,1] coordinates, with y pointing up. */
public final class HeadsetGeometry {
    private HeadsetGeometry() { }
    private static void finite(float value) {
        if (Float.isNaN(value) || Float.isInfinite(value)) throw new IllegalArgumentException("Nonfinite geometry");
    }
    public static float[] fit(float imageAspect, float eyeAspect) {
        finite(imageAspect); finite(eyeAspect);
        if (imageAspect <= 0 || eyeAspect <= 0) throw new IllegalArgumentException("Invalid aspect ratio");
        return new float[]{Math.min(1, imageAspect / eyeAspect), Math.min(1, eyeAspect / imageAspect)};
    }
    /** Center x/y and half width/height. Left eye is -1, right eye is +1. */
    public static float[] bounds(VrSettings settings, float imageAspect, float eyeAspect, int eyeSign) {
        if (eyeSign != -1 && eyeSign != 1) throw new IllegalArgumentException("Invalid eye");
        float[] fit = fit(imageAspect, eyeAspect);
        return new float[]{settings.offsetX + eyeSign * settings.eyeSeparation, settings.offsetY,
            fit[0] * settings.scale, fit[1] * settings.scale};
    }
    public static VrSettings pan(VrSettings start, float deltaX, float deltaY) {
        finite(deltaX); finite(deltaY);
        VrSettings value = start.copy();
        value.offsetX = Math.max(-.3f, Math.min(.3f, start.offsetX + deltaX));
        value.offsetY = Math.max(-.3f, Math.min(.3f, start.offsetY + deltaY));
        return value;
    }
    /** Interior dragging adjusts the two eye centers symmetrically around offsetX. */
    public static VrSettings mirroredPan(VrSettings start, int eyeSign, float deltaX, float deltaY) {
        finite(deltaX); finite(deltaY);
        if (eyeSign != -1 && eyeSign != 1) throw new IllegalArgumentException("Invalid eye");
        VrSettings value = start.copy();
        value.eyeSeparation = Math.max(0, Math.min(.2f, start.eyeSeparation + eyeSign * deltaX));
        value.offsetY = Math.max(-.3f, Math.min(.3f, start.offsetY + deltaY));
        return value;
    }
    /** Proportional corner scaling keeps the center fixed; deltas are from gesture start. */
    public static VrSettings resize(VrSettings start, float imageAspect, float eyeAspect,
                                    int signX, int signY, float deltaX, float deltaY) {
        finite(deltaX); finite(deltaY);
        if ((signX != -1 && signX != 1) || (signY != -1 && signY != 1))
            throw new IllegalArgumentException("Invalid corner");
        float[] fit = fit(imageAspect, eyeAspect);
        float delta = (signX * deltaX * fit[0] + signY * deltaY * fit[1])
            / (fit[0] * fit[0] + fit[1] * fit[1]);
        VrSettings value = start.copy();
        value.scale = Math.max(.5f, Math.min(1f, start.scale + delta));
        return value;
    }
}
