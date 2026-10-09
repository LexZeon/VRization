"""Cross-platform geometry contract; no GUI, capture or operating-system input."""

from dataclasses import replace
import unittest

from vrization_host.protocol import Settings
from vrization_host.view_edit import (EditTransaction, dragged, eye_bounds,
                                     fit_size, resolved_fit)


class FitGeometryTests(unittest.TestCase):
    def test_landscape_portrait_and_equal_aspect_fit(self):
        self.assertEqual(fit_size(2, 1), (1, 0.5))
        self.assertEqual(fit_size(0.5, 1), (0.5, 1))
        self.assertEqual(fit_size(1.2, 1.2), (1, 1))

    def test_eyes_share_size_and_vertical_center_with_symmetric_spacing(self):
        settings = Settings(scale=0.8, offsetX=0.1, offsetY=-0.1,
                            eyeSeparation=0.04)
        left = eye_bounds(settings, 0, 2, 1)
        right = eye_bounds(settings, 1, 2, 1)
        for bounds, center_x in ((left, 0.06), (right, 0.14)):
            self.assertAlmostEqual((bounds[0] + bounds[2]) / 2, center_x)
            self.assertAlmostEqual((bounds[1] + bounds[3]) / 2, -0.1)
            self.assertAlmostEqual(bounds[2] - bounds[0], 1.6)
            self.assertAlmostEqual(bounds[3] - bounds[1], 0.8)

    def test_valid_bounds_are_not_silently_clipped(self):
        bounds = eye_bounds(Settings(scale=1, offsetX=0.3, eyeSeparation=0.2),
                            1, 1, 1)
        # Shared X resolves to .2 to keep both inner edges inside their eyes;
        # the outer edge still extends past the viewport and is not clipped.
        for value, expected in zip(bounds, (-0.6, -1, 1.4, 1)):
            self.assertAlmostEqual(value, expected)

    def test_nonpositive_nonfinite_and_boolean_aspects_rejected(self):
        for invalid in (0, -1, float("nan"), float("inf"), True, "2", 10**1000):
            with self.subTest(value=str(invalid)[:24]):
                with self.assertRaises(ValueError):
                    fit_size(invalid, 1)
                with self.assertRaises(ValueError):
                    fit_size(1, invalid)
        for eye in (-1, 2, True, "0"):
            with self.assertRaises(ValueError):
                eye_bounds(Settings(), eye, 1, 1)


class DragTests(unittest.TestCase):
    def setUp(self):
        self.entry = Settings(mode="fps", scale=0.75, offsetX=0.05, offsetY=-0.05,
                              eyeSeparation=0.1, fov=95, distance=5,
                              distortion=0.2, sensitivity=1700, invertY=True)

    def test_pan_uses_y_up_and_moves_both_eyes_without_changing_optics(self):
        result = dragged(self.entry, "pan", 0.1, 0.15, 2, 1)
        self.assertAlmostEqual(result.offsetX, 0.15)
        self.assertAlmostEqual(result.offsetY, 0.1)
        self.assertEqual(replace(result, offsetX=self.entry.offsetX,
                                 offsetY=self.entry.offsetY), self.entry)
        for eye in (0, 1):
            before = eye_bounds(self.entry, eye, 2, 1)
            after = eye_bounds(result, eye, 2, 1)
            for a, b, delta in zip(after, before, (0.1, 0.15, 0.1, 0.15)):
                self.assertAlmostEqual(a - b, delta)

    def test_pan_clamps_wire_limits_at_all_edges(self):
        result = dragged(self.entry, "pan", 10, -10, 2, 1)
        self.assertEqual((result.offsetX, result.offsetY), (0.3, -0.3))
        result = dragged(self.entry, "pan", -10, 10, 2, 1)
        self.assertEqual((result.offsetX, result.offsetY), (-0.3, 0.3))

    def test_all_corners_resize_proportionally_with_center_fixed(self):
        for signs in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            with self.subTest(signs=signs):
                result = dragged(self.entry, "resize", signs[0] * 0.1,
                                 signs[1] * 0.05, 2, 1, signs)
                self.assertAlmostEqual(result.scale, 0.85)
                self.assertEqual(replace(result, scale=self.entry.scale), self.entry)
                for eye in (0, 1):
                    before = eye_bounds(self.entry, eye, 2, 1)
                    after = eye_bounds(result, eye, 2, 1)
                    self.assertAlmostEqual(after[0] + after[2], before[0] + before[2])
                    self.assertAlmostEqual(after[1] + after[3], before[1] + before[3])

    def test_orthogonal_corner_motion_does_not_distort_image(self):
        # Fit=(1,.5): (.1,-.2) is orthogonal to the allowed growth vector.
        result = dragged(self.entry, "resize", 0.1, -0.2, 2, 1)
        self.assertEqual(result.scale, self.entry.scale)

    def test_resize_clamps_without_moving_center(self):
        for delta, expected in ((10, 1), (-10, 0.5)):
            result = dragged(self.entry, "resize", delta, delta, 2, 1)
            self.assertEqual(result, replace(self.entry, scale=expected))

    def test_total_gesture_delta_never_accumulates_previous_events(self):
        first = dragged(self.entry, "pan", 0.05, 0.05, 2, 1)
        second = dragged(self.entry, "pan", 0.1, 0.1, 2, 1)
        self.assertAlmostEqual(first.offsetX, 0.1)
        self.assertAlmostEqual(second.offsetX, 0.15)
        self.assertAlmostEqual(second.offsetY, 0.05)

    def test_invalid_inputs_cannot_create_an_invalid_draft(self):
        for invalid in (True, float("nan"), float("inf"), "1", 10**1000):
            with self.assertRaises(ValueError):
                dragged(self.entry, "pan", invalid, 0, 2, 1)
        with self.assertRaises(ValueError):
            dragged(self.entry, "move", 0, 0, 2, 1)
        for signs in ((0, 1), (1,), (True, 1), (1, 2), None):
            with self.assertRaises(ValueError):
                dragged(self.entry, "resize", 0, 0, 2, 1, signs)
        with self.assertRaises(ValueError):
            dragged(replace(self.entry, scale=2), "pan", 0, 0, 2, 1)


class TransactionTests(unittest.TestCase):
    def test_discard_restores_entire_entry_after_multiple_gestures(self):
        entry = Settings(mode="cinema", distortion=0.25)
        edit = EditTransaction(entry)
        edit.preview("pan", 0.1, -0.1, 2, 1)
        gesture_start = edit.draft
        edit.preview("resize", 0.1, 0.05, 2, 1, gesture_start=gesture_start)
        self.assertEqual(edit.entry, entry)
        self.assertNotEqual(edit.draft, entry)
        self.assertIs(edit.discard(), entry)
        self.assertIs(edit.draft, entry)
        self.assertFalse(edit.active)

    def test_commit_returns_draft_once_and_cannot_be_reused(self):
        edit = EditTransaction(Settings())
        preview = edit.preview("pan", 0.1, 0, 2, 1)
        self.assertIs(edit.commit(), preview)
        self.assertFalse(edit.active)
        for operation in (edit.commit, edit.discard,
                          lambda: edit.preview("pan", 0, 0, 2, 1)):
            with self.assertRaises(RuntimeError):
                operation()

    def test_invalid_preview_keeps_previous_draft_and_transaction_open(self):
        edit = EditTransaction(Settings())
        previous = edit.preview("pan", 0.1, 0, 2, 1)
        with self.assertRaises(ValueError):
            edit.preview("resize", float("nan"), 0, 2, 1)
        self.assertIs(edit.draft, previous)
        self.assertTrue(edit.active)


class MirroredEyePanTests(unittest.TestCase):
    def setUp(self):
        self.entry = Settings(mode="fps", scale=0.7, offsetX=0.12,
                              offsetY=-0.05, eyeSeparation=0.1,
                              distortion=0.2, fov=95, invertY=True)

    def test_all_four_selected_eye_directions_widen_or_narrow_the_gap(self):
        for eye, dx, expected in ((0, -0.04, 0.14), (0, 0.04, 0.06),
                                  (1, 0.04, 0.14), (1, -0.04, 0.06)):
            with self.subTest(eye=eye, dx=dx):
                result = dragged(self.entry, "eye_pan", dx, 0, 2, 1, eye=eye)
                self.assertAlmostEqual(result.eyeSeparation, expected)
                self.assertEqual(replace(result, eyeSeparation=self.entry.eyeSeparation),
                                 self.entry)
                left = eye_bounds(result, 0, 2, 1)
                right = eye_bounds(result, 1, 2, 1)
                left_center = (left[0] + left[2]) / 2
                right_center = (right[0] + right[2]) / 2
                self.assertAlmostEqual(right_center - left_center, 2 * expected)
                self.assertAlmostEqual((left_center + right_center) / 2,
                                       self.entry.offsetX)

    def test_spacing_and_shared_vertical_clamp_and_contact_recenters_x(self):
        for eye, dx, expected in ((0, -10, 0.2), (0, 10, -0.3),
                                  (1, 10, 0.2), (1, -10, -0.3)):
            for dy, expected_y in ((10, 0.3), (-10, -0.3)):
                with self.subTest(eye=eye, dx=dx, dy=dy):
                    result = dragged(self.entry, "eye_pan", dx, dy, 2, 1, eye=eye)
                    self.assertAlmostEqual(result.eyeSeparation, expected)
                    self.assertEqual(result.offsetY, expected_y)
                    expected_x = 0 if expected < 0 else self.entry.offsetX
                    self.assertAlmostEqual(result.offsetX, expected_x)

    def test_vertical_motion_is_direct_and_does_not_change_spacing(self):
        for eye in (0, 1):
            result = dragged(self.entry, "eye_pan", 0, 0.1, 2, 1, eye=eye)
            self.assertAlmostEqual(result.offsetY, 0.05)
            self.assertEqual(result.eyeSeparation, self.entry.eyeSeparation)
            self.assertEqual(result.offsetX, self.entry.offsetX)

    def test_selected_eye_is_required_and_strict(self):
        for invalid in (None, -1, 2, True, "0", 0.0):
            with self.assertRaises(ValueError):
                dragged(self.entry, "eye_pan", 0.1, 0, 2, 1, eye=invalid)

    def test_preview_forwards_eye_and_saves_spacing_from_gesture_start(self):
        edit = EditTransaction(self.entry)
        edit.preview("eye_pan", -0.02, 0.02, 2, 1, eye=0)
        edit.preview("eye_pan", -0.04, 0.04, 2, 1, eye=0)
        committed = edit.commit()
        self.assertAlmostEqual(committed.eyeSeparation, 0.14)
        self.assertAlmostEqual(committed.offsetY, -0.01)
        self.assertEqual(committed.offsetX, self.entry.offsetX)
        self.assertEqual(edit.entry, self.entry)

    def test_discard_restores_entry_spacing_and_all_other_fields(self):
        edit = EditTransaction(self.entry)
        edit.preview("eye_pan", 0.07, 0.1, 2, 1, eye=1)
        self.assertIs(edit.discard(), self.entry)
        self.assertIs(edit.draft, self.entry)


class SeamFitTests(unittest.TestCase):
    @staticmethod
    def global_inner_edges(settings, image_aspect, eye_aspect):
        left = eye_bounds(settings, 0, image_aspect, eye_aspect)
        right = eye_bounds(settings, 1, image_aspect, eye_aspect)
        return -1 + left[2], 1 + right[0]

    def test_small_portrait_image_can_close_the_seam_with_either_eye(self):
        entry = Settings(scale=0.5, offsetX=0.2)
        for eye, inward in ((0, 10), (1, -10)):
            with self.subTest(eye=eye):
                result = dragged(entry, "eye_pan", inward, 0, 0.5, 1, eye=eye)
                self.assertEqual(result.eyeSeparation, -0.75)
                self.assertEqual(result.offsetX, 0)
                self.assertEqual(self.global_inner_edges(result, 0.5, 1), (0, 0))

    def test_contact_resolves_both_signs_of_global_offset_to_zero(self):
        for offset in (-0.3, 0.3):
            entry = Settings(scale=0.5, offsetX=offset, eyeSeparation=-1,
                             mode="cinema", distortion=0.4, fov=100)
            resolved = resolved_fit(entry, 0.5, 1)
            self.assertEqual((resolved.eyeSeparation, resolved.offsetX), (-0.75, 0))
            self.assertEqual(self.global_inner_edges(resolved, 0.5, 1), (0, 0))
            self.assertEqual(replace(resolved, offsetX=entry.offsetX,
                                     eyeSeparation=entry.eyeSeparation), entry)

    def test_midway_drag_preserves_x_until_gap_requires_a_smaller_offset(self):
        entry = Settings(scale=0.5, offsetX=0.2, eyeSeparation=0)
        roomy = dragged(entry, "eye_pan", 0.1, 0, 1, 1, eye=0)
        tight = dragged(entry, "eye_pan", 0.4, 0, 1, 1, eye=0)
        self.assertEqual(roomy.offsetX, entry.offsetX)
        self.assertAlmostEqual(tight.offsetX, 0.1)
        left, right = self.global_inner_edges(tight, 1, 1)
        self.assertLessEqual(left, 0)
        self.assertGreaterEqual(right, 0)
        self.assertLessEqual(left, right)

    def test_negative_saved_fit_adapts_to_new_aspect_without_mutating_profile(self):
        saved = Settings(scale=0.5, eyeSeparation=-0.75, offsetX=0.2)
        narrow = resolved_fit(saved, 0.5, 1)
        wide = resolved_fit(saved, 2, 1)
        self.assertEqual(narrow.eyeSeparation, -0.75)
        self.assertEqual(wide.eyeSeparation, -0.5)
        self.assertEqual((saved.eyeSeparation, saved.offsetX), (-0.75, 0.2))
        self.assertEqual(resolved_fit(wide, 2, 1), wide)
        self.assertEqual(self.global_inner_edges(wide, 2, 1), (0, 0))

    def test_resize_enlargement_at_contact_moves_centers_to_preserve_seam(self):
        entry = Settings(scale=0.5, eyeSeparation=-0.75, offsetX=0)
        result = dragged(entry, "resize", 0.25, 0.5, 0.5, 1)
        self.assertEqual(result.scale, 1)
        self.assertEqual(result.eyeSeparation, -0.5)
        self.assertEqual(self.global_inner_edges(result, 0.5, 1), (0, 0))
        self.assertEqual(replace(result, scale=entry.scale,
                                 eyeSeparation=entry.eyeSeparation), entry)

    def test_shrink_keeps_centers_and_then_allows_further_inward_motion(self):
        entry = Settings(scale=1, eyeSeparation=0)
        shrunk = dragged(entry, "resize", -0.5, -0.5, 1, 1)
        self.assertEqual((shrunk.scale, shrunk.eyeSeparation), (0.5, 0))
        self.assertEqual(self.global_inner_edges(shrunk, 1, 1), (-0.5, 0.5))
        closed = dragged(shrunk, "eye_pan", -0.5, 0, 1, 1, eye=1)
        self.assertEqual(self.global_inner_edges(closed, 1, 1), (0, 0))

    def test_resolved_invalid_settings_and_aspects_are_rejected(self):
        for entry in (Settings(eyeSeparation=-1.01), Settings(offsetX=0.31),
                      Settings(scale=float("nan"))):
            with self.assertRaises(ValueError):
                resolved_fit(entry, 1, 1)
        for aspect in (0, True, float("inf")):
            with self.assertRaises(ValueError):
                resolved_fit(Settings(), aspect, 1)

    def test_negative_spacing_commit_and_discard_keep_transaction_boundaries(self):
        entry = Settings(scale=0.5, eyeSeparation=-0.4, offsetY=0.1)
        saved_edit = EditTransaction(entry)
        saved = saved_edit.preview("eye_pan", 0.3, 0.1, 0.5, 1, eye=0)
        self.assertAlmostEqual(saved.eyeSeparation, -0.7)
        self.assertEqual(saved_edit.commit(), saved)
        discarded_edit = EditTransaction(entry)
        discarded_edit.preview("eye_pan", 10, -0.1, 0.5, 1, eye=0)
        self.assertIs(discarded_edit.discard(), entry)


if __name__ == "__main__":
    unittest.main()
