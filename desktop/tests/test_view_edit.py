"""Cross-platform geometry contract; no GUI, capture or operating-system input."""

from dataclasses import replace
import unittest

from vrization_host.protocol import Settings
from vrization_host.view_edit import EditTransaction, dragged, eye_bounds, fit_size


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
        self.assertEqual(bounds, (-0.5, -1, 1.5, 1))

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


if __name__ == "__main__":
    unittest.main()
