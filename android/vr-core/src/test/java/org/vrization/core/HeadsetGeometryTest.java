package org.vrization.core;

import org.junit.Test;
import static org.junit.Assert.*;

public final class HeadsetGeometryTest {
    @Test public void portraitAndLandscapeFitPreserveAspectWithoutFillingLetterbox() {
        assertArrayEquals(new float[]{1, .5625f}, HeadsetGeometry.fit(16f / 9, 1), .00001f);
        assertArrayEquals(new float[]{.5f, 1}, HeadsetGeometry.fit(.5f, 1), .00001f);
    }
    @Test public void bothEyesShareScaleAndOffsetsWithOnlySeparationSignDifferent() {
        VrSettings value = new VrSettings(); value.offsetX = .1f; value.offsetY = -.2f; value.scale = .8f;
        float[] left = HeadsetGeometry.bounds(value, 16f / 9, 1, -1);
        float[] right = HeadsetGeometry.bounds(value, 16f / 9, 1, 1);
        assertEquals(.07f, left[0], .00001f); assertEquals(.13f, right[0], .00001f);
        assertEquals(left[1], right[1], 0); assertEquals(left[2], right[2], 0); assertEquals(left[3], right[3], 0);
    }
    @Test public void panUsesTotalGestureDeltaAndClampsBothAxes() {
        VrSettings entry = new VrSettings(); entry.offsetX = .1f; entry.offsetY = -.1f;
        VrSettings first = HeadsetGeometry.pan(entry, .1f, .05f);
        VrSettings finalValue = HeadsetGeometry.pan(entry, .2f, .15f);
        assertEquals(.2f, first.offsetX, .00001f); assertEquals(.3f, finalValue.offsetX, .00001f);
        assertEquals(.05f, finalValue.offsetY, .00001f);
        assertEquals(-.3f, HeadsetGeometry.pan(entry, -10, 10).offsetX, 0);
        assertEquals(.3f, HeadsetGeometry.pan(entry, -10, 10).offsetY, 0);
        assertEquals(.1f, entry.offsetX, 0);
    }
    @Test public void everyCornerScalesProportionallyAndLeavesTheCenterFixed() {
        VrSettings start = new VrSettings(); start.scale = .6f; start.offsetX = .17f; start.offsetY = -.12f;
        for (int sx : new int[]{-1, 1}) for (int sy : new int[]{-1, 1}) {
            VrSettings value = HeadsetGeometry.resize(start, 16f / 9, 1, sx, sy, .1f * sx, .2f * sy);
            assertEquals(.6f + (.1f + .2f * .5625f) / (1 + .5625f * .5625f), value.scale, .00001f);
            assertEquals(start.offsetX, value.offsetX, 0); assertEquals(start.offsetY, value.offsetY, 0);
            assertEquals(.5625f, HeadsetGeometry.bounds(value, 16f / 9, 1, -1)[3]
                / HeadsetGeometry.bounds(value, 16f / 9, 1, -1)[2], .00001f);
        }
        assertEquals(1f, HeadsetGeometry.resize(start, 1, 1, 1, 1, 100, 100).scale, 0);
        assertEquals(.5f, HeadsetGeometry.resize(start, 1, 1, 1, 1, -100, -100).scale, 0);
    }
    @Test(expected = IllegalArgumentException.class) public void nonfiniteTouchCannotEscapeBounds() {
        HeadsetGeometry.pan(new VrSettings(), Float.NaN, 0);
    }
    @Test public void saveChangesOnlyFitAndPreservesOriginalModeAndOptics() {
        VrSettings entry = new VrSettings(); entry.mode = "fps"; entry.distortion = .4f; entry.fov = 103; entry.invertY = true;
        HeadsetEdit edit = new HeadsetEdit(entry);
        assertEquals("full", edit.preview().mode); assertEquals(0, edit.preview().distortion, 0);
        VrSettings geometry = HeadsetGeometry.pan(edit.draft(), .1f, .2f); geometry.scale = .7f;
        geometry.mode = "cinema"; geometry.distortion = .1f; edit.update(geometry);
        VrSettings saved = edit.save();
        assertEquals(.7f, saved.scale, 0); assertEquals(.1f, saved.offsetX, 0); assertEquals(.2f, saved.offsetY, 0);
        assertEquals("fps", saved.mode); assertEquals(.4f, saved.distortion, 0); assertEquals(103, saved.fov, 0); assertTrue(saved.invertY);
        assertEquals(.85f, entry.scale, 0); assertEquals(0, entry.offsetX, 0);
        try { edit.save(); fail("Cannot save the transaction twice"); } catch (IllegalStateException expected) { }
    }
    @Test public void discardRestoresIndependentEntrySnapshotAndHasNoCommitValue() {
        VrSettings entry = new VrSettings(); entry.mode = "cinema"; entry.distortion = .25f;
        HeadsetEdit edit = new HeadsetEdit(entry); entry.mode = "full";
        edit.update(HeadsetGeometry.pan(edit.draft(), .3f, -.3f));
        VrSettings discarded = edit.discard();
        assertEquals("cinema", discarded.mode); assertEquals(0, discarded.offsetX, 0);
        assertEquals(0, discarded.offsetY, 0); assertEquals(.25f, discarded.distortion, 0);
        try { edit.save(); fail("Discarded editor cannot commit"); } catch (IllegalStateException expected) { }
    }
}
