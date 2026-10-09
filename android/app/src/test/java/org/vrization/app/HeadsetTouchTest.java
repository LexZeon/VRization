package org.vrization.app;

import org.junit.Test;
import org.vrization.core.HeadsetGeometry;
import org.vrization.core.VrSettings;
import static org.junit.Assert.*;

public final class HeadsetTouchTest {
    @Test public void horizontalFingerMovementIsInvertedButVerticalMovementIsPreserved() {
        VrSettings entry = new VrSettings(); entry.offsetX = .04f; entry.offsetY = -.02f;
        VrSettings right = HeadsetTouch.pan(entry, .1f, .08f);
        assertEquals(-.06f, right.offsetX, .00001f); assertEquals(.06f, right.offsetY, .00001f);
        VrSettings left = HeadsetTouch.pan(entry, -.1f, -.08f);
        assertEquals(.14f, left.offsetX, .00001f); assertEquals(-.1f, left.offsetY, .00001f);
        assertEquals(.04f, entry.offsetX, 0); assertEquals(-.02f, entry.offsetY, 0);
    }
    @Test public void invertedTouchPanClampsWhileEnginePanRetainsMathematicalDirection() {
        VrSettings entry = new VrSettings();
        assertEquals(-.3f, HeadsetTouch.pan(entry, 2, 0).offsetX, 0);
        assertEquals(.3f, HeadsetTouch.pan(entry, -2, 0).offsetX, 0);
        assertEquals(.3f, HeadsetTouch.pan(entry, 0, 2).offsetY, 0);
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
