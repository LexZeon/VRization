package org.vrization.app;

import org.junit.Test;
import org.vrization.core.HeadsetGeometry;
import org.vrization.core.VrSettings;
import static org.junit.Assert.*;

public final class HeadsetTouchTest {
    @Test public void eitherEyeOutwardDragWidensAndInwardDragNarrowsWhileVerticalMovesTogether() {
        VrSettings entry = new VrSettings(); entry.offsetX = .04f; entry.offsetY = -.02f; entry.eyeSeparation = .1f;
        for (int eye : new int[]{-1, 1}) {
            VrSettings outward = HeadsetTouch.pan(entry, eye, eye * .04f, .08f);
            assertEquals(.14f, outward.eyeSeparation, .00001f); assertEquals(.06f, outward.offsetY, .00001f);
            VrSettings inward = HeadsetTouch.pan(entry, eye, -eye * .04f, -.08f);
            assertEquals(.06f, inward.eyeSeparation, .00001f); assertEquals(-.1f, inward.offsetY, .00001f);
            assertEquals(.04f, outward.offsetX, 0); assertEquals(.04f, inward.offsetX, 0);
        }
        assertEquals(.1f, entry.eyeSeparation, 0); assertEquals(-.02f, entry.offsetY, 0);
    }
    @Test public void touchClampsSpacingWithoutChangingEngineOffsetPan() {
        VrSettings entry = new VrSettings();
        assertEquals(.2f, HeadsetTouch.pan(entry, -1, -2, 0).eyeSeparation, 0);
        assertEquals(0, HeadsetTouch.pan(entry, 1, -2, 0).eyeSeparation, 0);
        assertEquals(.3f, HeadsetTouch.pan(entry, 1, 0, 2).offsetY, 0);
        assertEquals(.1f, HeadsetGeometry.pan(entry, .1f, 0).offsetX, 0);
    }
    @Test public void everyCornerRetainsPhysicalOutwardResizeAndFixedCenter() {
        VrSettings entry = new VrSettings(); entry.scale = .7f; entry.offsetX = .12f; entry.offsetY = -.09f;
        float[] fit = HeadsetGeometry.fit(16f / 9f, 1);
        for (int signX : new int[]{-1, 1}) for (int signY : new int[]{-1, 1}) {
            VrSettings expanded = HeadsetTouch.resize(entry, 16f / 9f, 1, signX, signY,
                signX * fit[0] * .1f, signY * fit[1] * .1f);
            assertEquals(.8f, expanded.scale, .00001f);
            assertEquals(entry.offsetX, expanded.offsetX, 0); assertEquals(entry.offsetY, expanded.offsetY, 0);
            VrSettings shrunk = HeadsetTouch.resize(entry, 16f / 9f, 1, signX, signY,
                -signX * fit[0] * .1f, -signY * fit[1] * .1f);
            assertEquals(.6f, shrunk.scale, .00001f);
        }
    }
}
