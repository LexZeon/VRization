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
    @Test public void mirroredPanMovesEyeCentersOppositelyWithoutMovingSharedHorizontalCenter() {
        VrSettings entry = new VrSettings(); entry.offsetX = .17f; entry.offsetY = -.1f; entry.eyeSeparation = .1f;
        for (int eye : new int[]{-1, 1}) for (int direction : new int[]{-1, 1}) {
            VrSettings value = HeadsetGeometry.mirroredPan(entry, 16f / 9, 1, eye, direction * .04f, .05f);
            float separation = .1f + eye * direction * .04f;
            assertEquals(separation, value.eyeSeparation, .00001f);
            assertEquals(.17f, value.offsetX, 0); assertEquals(-.05f, value.offsetY, .00001f);
            float[] left = HeadsetGeometry.bounds(value, 16f / 9, 1, -1);
            float[] right = HeadsetGeometry.bounds(value, 16f / 9, 1, 1);
            assertEquals(.17f, (left[0] + right[0]) / 2, .00001f);
            assertEquals(2 * separation, right[0] - left[0], .00001f);
        }
        assertEquals(.1f, entry.eyeSeparation, 0); assertEquals(-.1f, entry.offsetY, 0);
    }
    @Test public void mirroredPanClampsSpacingAndVerticalWhileRejectingInvalidEyeOrDelta() {
        VrSettings entry = new VrSettings(); entry.offsetX = -.19f;
        assertEquals(.2f, HeadsetGeometry.mirroredPan(entry, 16f / 9, 1, -1, -20, 10).eyeSeparation, 0);
        assertEquals(.3f, HeadsetGeometry.mirroredPan(entry, 16f / 9, 1, -1, -20, 10).offsetY, 0);
        assertEquals(-.15f, HeadsetGeometry.mirroredPan(entry, 16f / 9, 1, -1, 20, -10).eyeSeparation, .00001f);
        assertEquals(-.3f, HeadsetGeometry.mirroredPan(entry, 16f / 9, 1, -1, 20, -10).offsetY, 0);
        assertEquals(-.18f, HeadsetGeometry.mirroredPan(entry, 16f / 9, 1, 1, 20, 0).offsetX, .00001f);
        try { HeadsetGeometry.mirroredPan(entry, 1, 1, 0, .1f, 0); fail(); } catch (IllegalArgumentException expected) { }
        try { HeadsetGeometry.mirroredPan(entry, 1, 1, 1, Float.NaN, 0); fail(); } catch (IllegalArgumentException expected) { }
    }
    @Test public void smallPortraitImagesCanTouchAtTheMidlineWithoutClippingOrOverlap() {
        VrSettings entry = new VrSettings(); entry.scale = .5f; entry.offsetX = .23f;
        VrSettings contact = HeadsetGeometry.mirroredPan(entry, .5f, 1, -1, 2, 0);
        assertEquals(-.75f, contact.eyeSeparation, 0); assertEquals(0, contact.offsetX, 0);
        float[] left = HeadsetGeometry.bounds(contact, .5f, 1, -1);
        float[] right = HeadsetGeometry.bounds(contact, .5f, 1, 1);
        assertEquals(1, left[0] + left[2], 0); assertEquals(-1, right[0] - right[2], 0);
        assertTrue(left[0] - left[2] >= -1); assertTrue(right[0] + right[2] <= 1);
    }
    @Test public void resolveFitReducesOffsetOnlyWhenTheRemainingGapRequiresIt() {
        VrSettings entry = new VrSettings(); entry.scale = .5f; entry.offsetX = .23f; entry.offsetY = -.17f;
        entry.eyeSeparation = -.7f;
        VrSettings near = HeadsetGeometry.resolveFit(entry, .5f, 1);
        assertEquals(.05f, near.offsetX, .00001f); assertEquals(-.7f, near.eyeSeparation, 0);
        assertEquals(-.17f, near.offsetY, 0); assertEquals(.23f, entry.offsetX, 0);
        entry.eyeSeparation = -1;
        VrSettings contact = HeadsetGeometry.resolveFit(entry, .5f, 1);
        assertEquals(-.75f, contact.eyeSeparation, 0); assertEquals(0, contact.offsetX, 0);
        entry.eyeSeparation = .03f;
        assertEquals(.23f, HeadsetGeometry.resolveFit(entry, .5f, 1).offsetX, 0);
    }
    @Test public void resizingContactMovesSpacingOutwardAndKeepsBothInnerEdgesAtTheSeam() {
        VrSettings entry = new VrSettings(); entry.scale = .5f; entry.eyeSeparation = -.75f;
        VrSettings larger = HeadsetGeometry.resize(entry, .5f, 1, 1, 1, .1f, .2f);
        assertEquals(.7f, larger.scale, .00001f); assertEquals(-.65f, larger.eyeSeparation, .00001f);
        float[] left = HeadsetGeometry.bounds(larger, .5f, 1, -1);
        float[] right = HeadsetGeometry.bounds(larger, .5f, 1, 1);
        assertEquals(1, left[0] + left[2], .00001f); assertEquals(-1, right[0] - right[2], .00001f);
        assertEquals(0, larger.offsetX, 0); assertEquals(0, larger.offsetY, 0);
    }
    @Test public void viewportAspectChangesResolveStoredNegativeSpacingWithoutMutatingTheProfile() {
        VrSettings profile = new VrSettings(); profile.scale = .5f; profile.eyeSeparation = -.75f;
        profile.mode = "fps"; profile.distortion = .3f; profile.invertY = true;
        VrSettings wide = HeadsetGeometry.resolveFit(profile, 16f / 9, 1);
        assertEquals(-.5f, wide.eyeSeparation, 0); assertEquals(-.75f, profile.eyeSeparation, 0);
        assertEquals("fps", wide.mode); assertEquals(.3f, wide.distortion, 0); assertTrue(wide.invertY);
        profile.normalize(); assertEquals(-.75f, profile.eyeSeparation, 0);
    }
    @Test public void saveChangesOnlyFitAndPreservesOriginalModeAndOptics() {
        VrSettings entry = new VrSettings(); entry.mode = "fps"; entry.distortion = .4f; entry.fov = 103; entry.invertY = true;
        HeadsetEdit edit = new HeadsetEdit(entry);
        assertEquals("full", edit.preview().mode); assertEquals(0, edit.preview().distortion, 0);
        VrSettings geometry = HeadsetGeometry.pan(edit.draft(), .1f, .2f); geometry.scale = .7f;
        geometry.eyeSeparation = .16f; geometry.mode = "cinema"; geometry.distortion = .1f; edit.update(geometry);
        VrSettings saved = edit.save();
        assertEquals(.7f, saved.scale, 0); assertEquals(.1f, saved.offsetX, 0); assertEquals(.2f, saved.offsetY, 0);
        assertEquals(.16f, saved.eyeSeparation, 0);
        assertEquals("fps", saved.mode); assertEquals(.4f, saved.distortion, 0); assertEquals(103, saved.fov, 0); assertTrue(saved.invertY);
        assertEquals(.85f, entry.scale, 0); assertEquals(0, entry.offsetX, 0);
        try { edit.save(); fail("Cannot save the transaction twice"); } catch (IllegalStateException expected) { }
    }
    @Test public void discardRestoresIndependentEntrySnapshotAndHasNoCommitValue() {
        VrSettings entry = new VrSettings(); entry.mode = "cinema"; entry.distortion = .25f;
        HeadsetEdit edit = new HeadsetEdit(entry); entry.mode = "full";
        edit.update(HeadsetGeometry.mirroredPan(edit.draft(), 1, 1, -1, -.1f, -.3f));
        VrSettings discarded = edit.discard();
        assertEquals("cinema", discarded.mode); assertEquals(0, discarded.offsetX, 0);
        assertEquals(0, discarded.offsetY, 0); assertEquals(.25f, discarded.distortion, 0);
        assertEquals(.03f, discarded.eyeSeparation, 0);
        try { edit.save(); fail("Discarded editor cannot commit"); } catch (IllegalStateException expected) { }
    }
}
