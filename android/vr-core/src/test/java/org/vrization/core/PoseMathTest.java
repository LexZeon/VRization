package org.vrization.core;

import org.junit.Test;
import static org.junit.Assert.*;

public final class PoseMathTest {
    private static float radians(float degrees) { return (float) Math.toRadians(degrees); }
    @Test public void wraparoundDoesNotTurnAnEdgeCrossingIntoAFullRotation() {
        assertEquals(radians(2), PoseMath.relative(radians(-179), radians(179)), .0001f);
        assertEquals(radians(-2), PoseMath.relative(radians(179), radians(-179)), .0001f);
        assertEquals(radians(30), PoseMath.wrap(radians(750)), .0001f);
    }
    @Test public void recenterUsesNextSampleAndClearsAllAxes() {
        PoseMath.Center center = new PoseMath.Center();
        assertArrayEquals(new float[]{0,0,0}, center.sample(1f, .2f, -.1f), .0001f);
        assertArrayEquals(new float[]{.3f,-.1f,.2f}, center.sample(1.3f, .1f, .1f), .0001f);
        center.recenter();
        assertArrayEquals(new float[]{0,0,0}, center.sample(-2f, .7f, .2f), .0001f);
    }
    @Test(expected = IllegalArgumentException.class) public void invalidSensorValueIsRejected() { PoseMath.wrap(Float.NaN); }
    @Test public void remoteSettingsCannotEscapeUserFacingLimits() {
        VrSettings settings = new VrSettings();
        settings.mode = "unsafe"; settings.scale = Float.NaN; settings.offsetX = -100f;
        settings.offsetY = 100f; settings.eyeSeparation = 99f; settings.fov = 500f;
        settings.distance = -10f; settings.distortion = Float.POSITIVE_INFINITY; settings.sensitivity = 99999f;
        settings.normalize();
        assertEquals("full", settings.mode); assertEquals(.5f, settings.scale, 0f);
        assertEquals(-.3f, settings.offsetX, 0f); assertEquals(.3f, settings.offsetY, 0f);
        assertEquals(.2f, settings.eyeSeparation, 0f); assertEquals(110f, settings.fov, 0f);
        assertEquals(1f, settings.distance, 0f); assertEquals(0f, settings.distortion, 0f);
        assertEquals(3000f, settings.sensitivity, 0f);
    }
    @Test public void stabilizationDefaultsOffAndCopiesWithoutSharingMutableSettings() {
        VrSettings defaults = new VrSettings(); assertEquals(0, defaults.stabilization, 0);
        defaults.stabilization = .64f; VrSettings copy = defaults.copy();
        defaults.stabilization = .12f; assertEquals(.64f, copy.stabilization, 0);
        assertEquals(.12f, defaults.stabilization, 0);
    }
    @Test public void stabilizationNormalizationPreservesValidValuesAndClampsInvalidInput() {
        for (float value : new float[]{0, .4f, 1}) {
            VrSettings settings = new VrSettings(); settings.stabilization = value; settings.normalize();
            assertEquals(value, settings.stabilization, 0);
        }
        for (float value : new float[]{-1, Float.NaN, Float.POSITIVE_INFINITY, Float.NEGATIVE_INFINITY}) {
            VrSettings settings = new VrSettings(); settings.stabilization = value; settings.normalize();
            assertEquals(0, settings.stabilization, 0);
        }
        VrSettings settings = new VrSettings(); settings.stabilization = 10; settings.normalize();
        assertEquals(1, settings.stabilization, 0);
    }

    @Test public void rotationCenterNeutralAndIndependentAxesMatchViewerSigns() {
        float[] identity = rotation(0, 0, 0);
        PoseMath.RotationCenter center = new PoseMath.RotationCenter();
        assertArrayEquals(new float[]{0,0,0}, center.sample(identity), .0001f);
        assertArrayEquals(new float[]{.25f,0,0}, center.sample(rotation(.25f,0,0)), .0001f);
        assertArrayEquals(new float[]{0,.3f,0}, center.sample(rotation(0,.3f,0)), .0001f);
        assertArrayEquals(new float[]{0,0,.35f}, center.sample(rotation(0,0,.35f)), .0001f);
    }

    @Test public void tiltedRecenterPreservesAllLocalAxesWithoutCrossCoupling() {
        PoseMath.RotationCenter center = new PoseMath.RotationCenter();
        // An arbitrary initial screen-to-world frame: strongly tilted on every axis.
        float[] tilted = rotation(1.1f, .7f, -.8f);
        assertArrayEquals(new float[]{0,0,0}, center.sample(tilted), .0001f);
        assertArrayEquals(new float[]{.3f,0,0}, center.sample(multiply(tilted, rotation(.3f,0,0))), .0001f);
        assertArrayEquals(new float[]{0,-.25f,0}, center.sample(multiply(tilted, rotation(0,-.25f,0))), .0001f);
        assertArrayEquals(new float[]{0,0,.4f}, center.sample(multiply(tilted, rotation(0,0,.4f))), .0001f);
        assertArrayEquals(new float[]{.3f,-.25f,.4f}, center.sample(multiply(tilted, rotation(.3f,-.25f,.4f))), .0001f);
        center.recenter();
        float[] newOrigin = rotation(-1.4f, -.5f, .6f);
        assertArrayEquals(new float[]{0,0,0}, center.sample(newOrigin), .0001f);
        assertArrayEquals(new float[]{-.2f,.15f,-.3f}, center.sample(multiply(newOrigin, rotation(-.2f,.15f,-.3f))), .0001f);
    }

    /** Compose viewer yaw-right / pitch-up / roll-clockwise via independent axis matrices. */
    private static float[] rotation(float yaw, float pitch, float roll) {
        float cy = (float) Math.cos(yaw), sy = (float) Math.sin(yaw);
        float cp = (float) Math.cos(pitch), sp = (float) Math.sin(pitch);
        float cr = (float) Math.cos(roll), sr = (float) Math.sin(roll);
        float[] y = {cy,0,-sy, 0,1,0, sy,0,cy};
        float[] p = {1,0,0, 0,cp,-sp, 0,sp,cp};
        float[] r = {cr,sr,0, -sr,cr,0, 0,0,1};
        return multiply(multiply(y,p),r);
    }
    private static float[] multiply(float[] a, float[] b) {
        float[] result = new float[9];
        for (int row=0; row<3; row++) for (int col=0; col<3; col++)
            for (int inner=0; inner<3; inner++) result[row*3+col] += a[row*3+inner] * b[inner*3+col];
        return result;
    }
}
