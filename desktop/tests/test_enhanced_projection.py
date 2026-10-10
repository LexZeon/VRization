import math
import unittest

from PIL import Image

from vrization_host.enhanced_projection import source_point, texture_uv
from vrization_host.protocol import Settings
from vrization_host.view_edit import dragged, eye_bounds, resolved_fit
from vrization_host.view_editor import enhanced_preview


class EnhancedFitTests(unittest.TestCase):
    def test_source_aspect_cannot_change_physical_square(self):
        settings = Settings(mode="fps_enhanced", scale=.75, offsetY=.12)
        for image in (.5, 1, 16 / 9, 32 / 9):
            for eye_aspect in (.7, 1, 10 / 9, 2):
                for eye in (0, 1):
                    with self.subTest(image=image, aspect=eye_aspect, eye=eye):
                        left, bottom, right, top = eye_bounds(settings, eye, image, eye_aspect)
                        self.assertAlmostEqual((right - left) * eye_aspect, top - bottom)
                        self.assertAlmostEqual((top + bottom) / 2, .12)

    def test_corner_resize_preserves_square_and_mode_for_all_corners(self):
        start = Settings(mode="fps_enhanced", scale=.6, eyeSeparation=.1)
        for signs in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            result = dragged(start, "resize", signs[0] * .12, signs[1] * .12,
                             16 / 9, 1.2, signs)
            self.assertGreater(result.scale, start.scale)
            self.assertEqual(result.mode, start.mode)
            left, bottom, right, top = eye_bounds(result, 0, 16 / 9, 1.2)
            self.assertAlmostEqual((right - left) * 1.2, top - bottom)

    def test_small_squares_can_meet_seam_and_move_apart_symmetrically(self):
        start = Settings(mode="fps_enhanced", scale=.5, eyeSeparation=-1, offsetX=.3)
        fitted = resolved_fit(start, 16 / 9, 1.2)
        left = eye_bounds(fitted, 0, 16 / 9, 1.2)
        right = eye_bounds(fitted, 1, 16 / 9, 1.2)
        self.assertAlmostEqual(left[2], 1)
        self.assertAlmostEqual(right[0], -1)
        self.assertAlmostEqual(fitted.offsetX, 0)
        moved = dragged(fitted, "eye_pan", -.1, .08, 16 / 9, 1.2, eye=0)
        for eye, sign in ((0, -1), (1, 1)):
            old = eye_bounds(fitted, eye, 16 / 9, 1.2)
            new = eye_bounds(moved, eye, 16 / 9, 1.2)
            self.assertAlmostEqual(new[0] - old[0], sign * .1)
            self.assertAlmostEqual(new[1] - old[1], .08)

    def test_other_modes_keep_original_image_aspect(self):
        for mode in ("full", "cinema", "fps"):
            bounds = eye_bounds(Settings(mode=mode), 0, 16 / 9, 1.2)
            self.assertAlmostEqual((bounds[2] - bounds[0]) * 1.2 / (bounds[3] - bounds[1]), 16 / 9)


class AngularProjectionTests(unittest.TestCase):
    def test_center_axis_boundaries_orientation_and_black_corners(self):
        for fov in (50, 80, 110):
            self.assertEqual(texture_uv(0, 0, fov), (.5, .5))
            self.assertEqual(texture_uv(1, 0, fov), (1, .5))
            self.assertEqual(texture_uv(0, 1, fov), (.5, 0))
            self.assertIsNone(texture_uv(1, 1, fov))
            self.assertIsNone(texture_uv(1.01, 0, fov))
            self.assertLess(texture_uv(-.3, .4, fov)[0], .5)
            self.assertLess(texture_uv(-.3, .4, fov)[1], .5)

    def test_inverse_recovers_angular_radius_and_is_finite_monotonic(self):
        for fov in (50, 80, 110):
            half_angle = math.radians(fov) / 2
            previous = 0
            for step in range(1, 101):
                radius = step / 100
                sx, sy = source_point(radius, 0, fov)
                # Forward angular projection is independent of inverse sampling.
                recovered = math.atan(math.hypot(sx, sy) * math.tan(half_angle)) / half_angle
                self.assertAlmostEqual(recovered, radius)
                self.assertGreater(sx, previous)
                self.assertTrue(math.isfinite(sx))
                previous = sx
            for x in range(-10, 11):
                for y in range(-10, 11):
                    point = source_point(x / 10, y / 10, fov)
                    opposite = source_point(-x / 10, -y / 10, fov)
                    self.assertTrue(all(math.isfinite(value) for value in point))
                    self.assertEqual(point, tuple(-value for value in opposite))

    def test_more_warp_enlarges_center_without_changing_axis_edges(self):
        weak = source_point(.5, 0, 50)[0]
        strong = source_point(.5, 0, 110)[0]
        self.assertLess(strong, weak)
        self.assertLess(weak, .5)

    def test_invalid_inputs_fail_instead_of_nan_or_pole(self):
        for value in (True, "80", None, float("nan"), float("inf"), 10**1000):
            with self.subTest(value=str(value)[:30]):
                with self.assertRaises(ValueError):
                    source_point(value, 0)
                with self.assertRaises(ValueError):
                    source_point(0, 0, value)
        for fov in (49, 111, 180, -80):
            with self.assertRaises(ValueError):
                source_point(1, 1, fov)

    def test_local_editor_preview_has_square_shape_and_real_warp(self):
        source = Image.new("RGB", (320, 180))
        pixels = source.load()
        for x in range(320):
            for y in range(180):
                pixels[x, y] = (round(x / 319 * 255), round(y / 179 * 255), 100)
        result = enhanced_preview(source, (200, 200), 110)
        self.assertEqual(result.size, (200, 200))
        self.assertEqual(result.getpixel((0, 0)), (0, 0, 0))
        self.assertLess(abs(result.getpixel((100, 100))[0] - 128), 3)
        self.assertLess(abs(result.getpixel((100, 100))[1] - 128), 3)
        # Warp enlarges the middle: x=.5 samples inside the flat x=.5 source.
        self.assertLess(result.getpixel((150, 100))[0], 185)


if __name__ == "__main__":
    unittest.main()
