package org.vrization.core;

import org.junit.Test;
import static org.junit.Assert.*;

public final class EnhancedProjectionTest {
    @Test public void centerAndCardinalEdgesStayCenteredAndBoundedAcrossFovRange() {
        for (float fov : new float[]{50, 80, 110}) {
            assertArrayEquals(new float[]{0, 0}, EnhancedProjection.source(0, 0, fov), 0);
            for (int sign : new int[]{-1, 1}) {
                assertArrayEquals(new float[]{sign, 0}, EnhancedProjection.source(sign, 0, fov), .000001f);
                assertArrayEquals(new float[]{0, sign}, EnhancedProjection.source(0, sign, fov), .000001f);
            }
        }
    }
    @Test public void sharedAngularMappingGoldenSamplesMatchInsteadOfAnIdentityStretch() {
        assertArrayEquals(new float[]{.4337628343f, 0}, EnhancedProjection.source(.5f, 0, 80), .000001f);
        assertArrayEquals(new float[]{.2192459516f, .4384919032f}, EnhancedProjection.source(.25f, .5f, 80), .000001f);
        assertArrayEquals(new float[]{.6779603378f, .1937029536f}, EnhancedProjection.source(.7f, .2f, 50), .000001f);
        assertArrayEquals(new float[]{.5657510742f, .1616431641f}, EnhancedProjection.source(.7f, .2f, 110), .000001f);
        assertArrayEquals(new float[]{.8502267004f, .8502267004f}, EnhancedProjection.source(.8f, .8f, 80), .000001f);
    }
    @Test public void roundedCornersAndOutOfBoundsSamplesAreBlack() {
        for (float fov : new float[]{50, 80, 110}) {
            for (int x : new int[]{-1, 1}) for (int y : new int[]{-1, 1})
                assertNull(EnhancedProjection.source(x, y, fov));
            assertNull(EnhancedProjection.source(1.001f, 0, fov));
            assertNull(EnhancedProjection.source(0, -1.001f, fov));
        }
    }
    @Test public void bothAxesHaveTheSameWarpAndMirrorSymmetry() {
        float[] positive = EnhancedProjection.source(.2f, .65f, 97);
        assertArrayEquals(new float[]{positive[1], positive[0]}, EnhancedProjection.source(.65f, .2f, 97), .000001f);
        assertArrayEquals(new float[]{-positive[0], positive[1]}, EnhancedProjection.source(-.2f, .65f, 97), .000001f);
        assertArrayEquals(new float[]{positive[0], -positive[1]}, EnhancedProjection.source(.2f, -.65f, 97), .000001f);
    }
    @Test public void tinyRadiusIsFiniteAndMaximumFovDoesNotCrossTheTangentSingularity() {
        assertArrayEquals(new float[]{0, 0}, EnhancedProjection.source(1e-8f, -1e-8f, 110), 0);
        for (int ix = -100; ix <= 100; ix++) for (int iy = -100; iy <= 100; iy++) {
            float[] q = EnhancedProjection.source(ix / 100f, iy / 100f, 110);
            if (q != null) {
                assertFalse(Float.isNaN(q[0])); assertFalse(Float.isNaN(q[1]));
                assertTrue(Math.abs(q[0]) <= 1); assertTrue(Math.abs(q[1]) <= 1);
            }
        }
    }
    @Test public void malformedInputsFailInsteadOfEnteringTheShaderMath() {
        for (float bad : new float[]{Float.NaN, Float.POSITIVE_INFINITY, Float.NEGATIVE_INFINITY}) {
            assertThrows(IllegalArgumentException.class, () -> EnhancedProjection.source(bad, 0, 80));
            assertThrows(IllegalArgumentException.class, () -> EnhancedProjection.source(0, bad, 80));
            assertThrows(IllegalArgumentException.class, () -> EnhancedProjection.source(0, 0, bad));
        }
        for (float fov : new float[]{49.99f, 110.01f})
            assertThrows(IllegalArgumentException.class, () -> EnhancedProjection.source(0, 0, fov));
    }
    @Test public void enhancedGeometryUsesPhysicalSquareForEverySourceAndOddEyeWidth() {
        VrSettings value = new VrSettings(); value.mode = VrSettings.ENHANCED_FIRST_PERSON;
        for (float source : new float[]{16f / 9, .5f, 1}) for (int eyeWidth : new int[]{600, 601, 1000}) {
            float[] b = HeadsetGeometry.bounds(value, source, eyeWidth / 700f, -1);
            assertEquals(b[2] * eyeWidth, b[3] * 700, .0001f);
            assertEquals(1, value.contentAspect(source), 0);
        }
    }
    @Test public void enhancedResizeAndSeamUseSquareAndPreserveSavedProjection() {
        VrSettings entry = new VrSettings(); entry.mode = VrSettings.ENHANCED_FIRST_PERSON;
        entry.scale = .5f; entry.offsetX = .2f; entry.fov = 105; entry.distortion = .2f;
        VrSettings seam = HeadsetGeometry.mirroredPan(entry, 16f / 9, 1.5f, -1, 10, 0);
        float[] left = HeadsetGeometry.bounds(seam, 16f / 9, 1.5f, -1);
        float[] right = HeadsetGeometry.bounds(seam, .5f, 1.5f, 1);
        assertEquals(1, left[0] + left[2], .000001f); assertEquals(-1, right[0] - right[2], .000001f);
        VrSettings grown = HeadsetGeometry.resize(seam, 16f / 9, 1.5f, 1, 1, .1f, .2f);
        assertEquals((.1f * (2f / 3) + .2f) / (4f / 9 + 1) + .5f, grown.scale, .000001f);
        HeadsetEdit editor = new HeadsetEdit(grown);
        assertEquals(VrSettings.ENHANCED_FIRST_PERSON, editor.preview().mode);
        assertEquals(105, editor.preview().fov, 0); assertEquals(.2f, editor.preview().distortion, 0);
        assertEquals(VrSettings.ENHANCED_FIRST_PERSON, editor.save().mode);
        HeadsetEdit discarded = new HeadsetEdit(entry);
        discarded.update(grown); assertEquals(.5f, discarded.discard().scale, 0);
    }
    @Test public void enhancedDisplayWithoutSensorDoesNotChangeExistingModesSensorPolicy() {
        assertTrue(VrSettings.isFirstPerson("fps")); assertTrue(VrSettings.isFirstPerson("fps_enhanced"));
        assertFalse(VrSettings.isFirstPerson("cinema"));
        assertTrue(VrSettings.requiresRotationSensor("cinema")); assertTrue(VrSettings.requiresRotationSensor("fps"));
        assertFalse(VrSettings.requiresRotationSensor("fps_enhanced")); assertFalse(VrSettings.requiresRotationSensor("full"));
        VrSettings enhanced = new VrSettings(); enhanced.mode = "fps_enhanced"; enhanced.normalize();
        assertEquals("fps_enhanced", enhanced.mode);
        enhanced.mode = "fps_enhanced_other"; enhanced.normalize(); assertEquals("full", enhanced.mode);
    }
}
