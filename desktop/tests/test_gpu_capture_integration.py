"""Mock capture backends; exercise real JPEG/cache and fail-closed integration.

No Windows API, desktop pixels, mouse input or connected device is used.
"""
from dataclasses import replace
from io import BytesIO
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image

from vrization_host.capture import CaptureConfig, MssCaptureSource
from vrization_host.windows_capture import CaptureLayoutChanged
from vrization_host.windows_gpu import UnsupportedGpuCapture


_PATTERN = b"".join(bytes((n, n * 3 % 256, n * 5 % 256, 255)) for n in range(256))


def pixels(size):
    """Synthetic BGRX, independent of the user's displays."""
    length = size[0] * size[1] * 4
    return (_PATTERN * ((length + len(_PATTERN) - 1) // len(_PATTERN)))[:length]


class GpuCaptureIntegrationTests(unittest.TestCase):
    monitors = [dict(left=-200, top=-50, width=1120, height=800),
                dict(left=-200, top=-50, width=640, height=480),
                dict(left=440, top=-50, width=480, height=800)]

    def setUp(self):
        self.screen = Mock(monitors=self.monitors)
        self.screen.grab.side_effect = lambda rectangle: SimpleNamespace(
            size=(rectangle["width"], rectangle["height"]),
            bgra=pixels((rectangle["width"], rectangle["height"])))
        self.layout = Mock()
        self.gpu = self.make_gpu()
        self.gdi = Mock()
        self.gdi.grab.side_effect = lambda rectangle, size: pixels(size)
        self.mss_factory = self.start_patch("mss.MSS", return_value=self.screen)
        self.layout_factory = self.start_patch(
            "vrization_host.windows_capture.WindowsDisplayLayout", return_value=self.layout)
        self.gpu_factory = self.start_patch(
            "vrization_host.windows_gpu.WindowsGpuCapture", return_value=self.gpu)
        self.gdi_factory = self.start_patch(
            "vrization_host.windows_capture.WindowsGdiCapture", return_value=self.gdi)
        self.clock = self.start_patch("vrization_host.capture.time.monotonic", side_effect=range(100, 1000))
        self.start_patch("vrization_host.capture.os.name", "nt")
        self.source = MssCaptureSource()
        self.addCleanup(self.source.close)
        self.config = CaptureConfig(monitor=2)

    def start_patch(self, target, *args, **kwargs):
        patcher = patch(target, *args, **kwargs)
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    @staticmethod
    def make_gpu():
        gpu = Mock(protected_content_masked=False)
        gpu.grab.side_effect = lambda rectangle, size, **kwargs: pixels(size)
        return gpu

    def assert_no_cpu_capture(self):
        self.gdi_factory.assert_not_called()
        self.screen.grab.assert_not_called()

    def assert_frame(self, frame, size):
        self.assertEqual((frame.width, frame.height), size)
        with Image.open(BytesIO(frame.jpeg)) as decoded:
            self.assertEqual(decoded.format, "JPEG")
            self.assertEqual(decoded.size, size)

    def test_default_gpu_selection_preserves_negative_coordinates_and_portrait_size(self):
        negative = self.source.read(replace(self.config, monitor=1))
        self.assert_frame(negative, (640, 480))
        self.gpu.grab.assert_called_once_with(self.monitors[1], (640, 480), force_latest=True)
        self.gpu_factory.assert_called_once_with(expected_monitors=self.monitors)
        self.assertEqual([call.args for call in self.layout.validate.call_args_list], [(self.monitors,)] * 2)
        self.assert_no_cpu_capture()

        portrait = self.source.read(self.config)
        self.assert_frame(portrait, (384, 640))
        self.gpu.grab.assert_called_with(self.monitors[2], (384, 640), force_latest=True)

    def test_no_initial_gpu_update_waits_without_falling_back(self):
        self.gpu.grab.side_effect = None
        self.gpu.grab.return_value = None
        self.assertIsNone(self.source.read(self.config))
        self.assertIsNone(self.source.read(self.config))
        self.gpu_factory.assert_called_once()
        self.assertEqual(self.gpu.grab.call_count, 2)
        for call in self.gpu.grab.call_args_list:
            self.assertEqual(call.kwargs, {"force_latest": True})
        self.clock.assert_not_called()
        self.assert_no_cpu_capture()

    def test_masked_pixels_stay_black_and_cached_without_cpu_fallback(self):
        size = (384, 640)
        row = bytes((0, 0, 0, 255)) * 192 + bytes((20, 140, 220, 255)) * 192
        self.gpu.protected_content_masked = True
        self.gpu.grab.side_effect = [row * 640, None, None]
        first = self.source.read(self.config)
        self.assertTrue(first.protected_content_masked)
        with Image.open(BytesIO(first.jpeg)) as decoded:
            self.assertEqual(decoded.getpixel((40, 40)), (0, 0, 0))
            self.assertGreater(decoded.getpixel((300, 40))[0], 200)
        self.assertIs(self.source.read(self.config), first)
        reencoded = self.source.read(replace(self.config, quality=90))
        self.assertTrue(reencoded.protected_content_masked)
        self.assert_frame(reencoded, size)
        self.gpu_factory.assert_called_once()
        self.assert_no_cpu_capture()

    def test_static_desktop_reuses_jpeg_and_original_capture_timestamp(self):
        self.gpu.grab.side_effect = [pixels((384, 640)), None, None]
        save = Image.Image.save
        with patch.object(Image.Image, "save", autospec=True, side_effect=save) as encoder:
            first = self.source.read(self.config)
            self.assertIs(self.source.read(self.config), first)
            self.assertIs(self.source.read(replace(self.config, fps=30)), first)
            encoder.assert_called_once()
        self.assertEqual(first.captured_at, 100)
        self.clock.assert_called_once()
        self.assertEqual([call.kwargs["force_latest"] for call in self.gpu.grab.call_args_list],
                         [True, False, False])
        self.assert_no_cpu_capture()

    def test_new_gpu_pixels_replace_the_frame_and_capture_timestamp(self):
        self.gpu.grab.side_effect = [pixels((384, 640)), bytes(384 * 640 * 4)]
        first = self.source.read(self.config)
        second = self.source.read(self.config)
        self.assertIsNot(second, first)
        self.assertNotEqual(second.jpeg, first.jpeg)
        self.assertEqual((first.captured_at, second.captured_at), (100, 101))
        self.assert_frame(second, (384, 640))

    def test_quality_change_reencodes_cached_owned_pixels_without_a_new_capture(self):
        self.gpu.grab.side_effect = [pixels((384, 640)), None, None]
        low = self.source.read(replace(self.config, quality=30))
        high = self.source.read(replace(self.config, quality=90))
        self.assertIsNot(high, low)
        self.assertNotEqual(low.jpeg, high.jpeg)
        self.assertEqual(low.captured_at, high.captured_at)
        self.assert_frame(high, (384, 640))
        self.assertIs(self.source.read(replace(self.config, quality=90)), high)
        self.clock.assert_called_once()
        self.assertEqual([call.kwargs["force_latest"] for call in self.gpu.grab.call_args_list],
                         [True, False, False])
        self.assert_no_cpu_capture()

    def test_size_change_forces_latest_on_same_gpu_and_publishes_correct_dimensions(self):
        first = self.source.read(self.config)
        resized = self.source.read(replace(self.config, width=480))
        self.assert_frame(first, (384, 640))
        self.assert_frame(resized, (288, 480))
        self.gpu_factory.assert_called_once()
        self.gpu.close.assert_not_called()
        self.gpu.grab.assert_called_with(self.monitors[2], (288, 480), force_latest=True)
        self.assert_no_cpu_capture()

    def test_explicit_region_change_closes_previous_gpu_and_discards_old_jpeg(self):
        events = []
        second_gpu = self.make_gpu()
        self.gpu.close.side_effect = lambda: events.append("old closed")
        self.gpu_factory.side_effect = lambda **kwargs: (
            events.append("created") or (self.gpu if len(events) == 1 else second_gpu))
        first = self.source.read(self.config)
        region = (-160, -20, 400, 240)
        cropped = self.source.read(replace(self.config, region=region))
        self.assertEqual(events, ["created", "old closed", "created"])
        self.assertEqual(self.gpu_factory.call_count, 2)
        second_gpu.grab.assert_called_once_with(
            dict(zip(("left", "top", "width", "height"), region)),
            (400, 240), force_latest=True)
        self.assert_frame(cropped, (400, 240))
        self.assertIsNot(first, cropped)
        self.assert_no_cpu_capture()

    def test_initial_unsupported_gpu_falls_back_to_exact_same_gdi_rectangle_once(self):
        self.gpu.grab.side_effect = UnsupportedGpuCapture("initial unsupported API")
        config = replace(self.config, region=(-160, -20, 400, 240))
        rectangle = dict(left=-160, top=-20, width=400, height=240)
        for _ in range(2):
            self.assert_frame(self.source.read(config), (400, 240))
        self.gpu_factory.assert_called_once()
        self.gpu.close.assert_called_once()
        self.gdi_factory.assert_called_once()
        self.assertEqual([call.args for call in self.gdi.grab.call_args_list],
                         [(rectangle, (400, 240))] * 2)
        self.screen.grab.assert_not_called()

    def test_gpu_and_gdi_initial_unsupported_use_the_same_exact_mss_region(self):
        self.gpu.grab.side_effect = UnsupportedGpuCapture("initial unsupported API")
        self.gdi.grab.side_effect = OSError("GDI unavailable")
        config = replace(self.config, region=(-160, -20, 400, 240))
        rectangle = dict(left=-160, top=-20, width=400, height=240)
        for _ in range(2):
            self.assert_frame(self.source.read(config), (400, 240))
        self.gpu.grab.assert_called_once_with(rectangle, (400, 240), force_latest=True)
        self.gdi.grab.assert_called_once_with(rectangle, (400, 240))
        self.gdi.close.assert_called_once()
        self.assertEqual([call.args[0] for call in self.screen.grab.call_args_list],
                         [rectangle, rectangle])

    def test_runtime_error_poison_blocks_new_selections_until_explicit_close(self):
        self.gpu.grab.side_effect = [pixels((384, 640)), OSError("access lost")]
        self.source.read(self.config)
        with self.assertRaisesRegex(OSError, "access lost"):
            self.source.read(self.config)
        with self.assertRaisesRegex(OSError, "access lost"):
            self.source.read(replace(self.config, monitor=1))
        self.assertEqual(self.gpu.grab.call_count, 2)
        self.gpu.close.assert_called_once()
        self.assert_no_cpu_capture()

        replacement_gpu = self.make_gpu()
        self.gpu_factory.return_value = replacement_gpu
        self.source.close()
        self.assert_frame(self.source.read(self.config), (384, 640))
        replacement_gpu.grab.assert_called_once_with(self.monitors[2], (384, 640), force_latest=True)
        self.assertEqual(self.mss_factory.call_count, 2)

    def test_unsupported_after_initial_empty_update_is_fatal_without_cpu_fallback(self):
        self.gpu.grab.side_effect = [None, UnsupportedGpuCapture("later unsupported")]
        self.assertIsNone(self.source.read(self.config))
        with self.assertRaisesRegex(UnsupportedGpuCapture, "later unsupported"):
            self.source.read(self.config)
        with self.assertRaisesRegex(OSError, "later unsupported"):
            self.source.read(self.config)
        self.assertEqual(self.gpu.grab.call_count, 2)
        self.gpu.close.assert_called_once()
        self.assert_no_cpu_capture()

    def test_layout_change_blocks_cached_frame_and_poison_cannot_resume_automatically(self):
        self.source.read(self.config)
        self.layout.validate.side_effect = [CaptureLayoutChanged("display moved"), None]
        with self.assertRaisesRegex(CaptureLayoutChanged, "display moved"):
            self.source.read(self.config)
        with self.assertRaisesRegex(OSError, "display moved"):
            self.source.read(self.config)
        self.gpu.grab.assert_called_once()
        self.gpu.close.assert_called_once()
        self.assertEqual(self.layout.validate.call_count, 3)
        self.assert_no_cpu_capture()

    def assert_poison_until_close(self):
        """A physically restored layout must not revive the rejected session."""
        self.layout.validate.side_effect = None
        counts = (self.gpu.grab.call_count, self.gdi.grab.call_count, self.screen.grab.call_count,
                  self.layout.validate.call_count)
        with self.assertRaisesRegex(OSError, "layout changed during capture"):
            self.source.read(self.config)
        self.assertEqual(counts, (self.gpu.grab.call_count, self.gdi.grab.call_count,
                                  self.screen.grab.call_count, self.layout.validate.call_count))
        self.source.close()
        replacement = self.make_gpu()
        self.gpu_factory.return_value = replacement
        self.assert_frame(self.source.read(self.config), (384, 640))
        replacement.grab.assert_called_once_with(self.monitors[2], (384, 640), force_latest=True)

    def test_gdi_layout_change_during_read_rejects_frame_and_poison_persists(self):
        changed = [False]
        def validate(monitors):
            if changed[0]: raise CaptureLayoutChanged("layout changed during capture")
        def blit(rectangle, size):
            changed[0] = True
            return pixels(size)
        self.layout.validate.side_effect = validate
        self.gpu.grab.side_effect = UnsupportedGpuCapture("initial unsupported API")
        self.gdi.grab.side_effect = blit
        with self.assertRaisesRegex(CaptureLayoutChanged, "layout changed during capture"):
            self.source.read(self.config)
        self.gdi.grab.assert_called_once_with(self.monitors[2], (384, 640))
        self.screen.grab.assert_not_called()
        self.assertEqual(self.layout.validate.call_count, 2)
        self.assert_poison_until_close()
        self.gdi.close.assert_called_once()

    def test_mss_layout_change_during_read_rejects_frame_without_another_fallback(self):
        changed = [False]
        def validate(monitors):
            if changed[0]: raise CaptureLayoutChanged("layout changed during capture")
        def screenshot(rectangle):
            changed[0] = True
            size = rectangle["width"], rectangle["height"]
            return SimpleNamespace(size=size, bgra=pixels(size))
        self.layout.validate.side_effect = validate
        self.gpu.grab.side_effect = UnsupportedGpuCapture("initial unsupported API")
        self.gdi.grab.side_effect = OSError("GDI unavailable")
        self.screen.grab.side_effect = screenshot
        with self.assertRaisesRegex(CaptureLayoutChanged, "layout changed during capture"):
            self.source.read(self.config)
        self.screen.grab.assert_called_once_with(self.monitors[2])
        self.gdi.close.assert_called_once()
        self.assertEqual(self.layout.validate.call_count, 2)
        self.assert_poison_until_close()

    def test_gpu_layout_change_during_jpeg_encoding_rejects_completed_frame_and_cache(self):
        changed = [False]
        def validate(monitors):
            if changed[0]: raise CaptureLayoutChanged("layout changed during capture")
        encode = Image.Image.save
        def encode_then_move(image, *args, **kwargs):
            encode(image, *args, **kwargs)
            changed[0] = True
        self.layout.validate.side_effect = validate
        with patch.object(Image.Image, "save", autospec=True, side_effect=encode_then_move):
            with self.assertRaisesRegex(CaptureLayoutChanged, "layout changed during capture"):
                self.source.read(self.config)
        self.gpu.grab.assert_called_once_with(self.monitors[2], (384, 640), force_latest=True)
        self.gpu.close.assert_called_once()
        self.assertEqual(self.layout.validate.call_count, 2)
        self.assert_no_cpu_capture()
        self.assert_poison_until_close()

    def test_initial_layout_failure_does_not_create_any_capture_backend(self):
        self.layout.validate.side_effect = OSError("cannot verify layout")
        for _ in range(2):
            with self.assertRaisesRegex(OSError, "cannot verify layout"):
                self.source.read(self.config)
        self.layout.validate.assert_called_once()
        self.gpu_factory.assert_not_called()
        self.assert_no_cpu_capture()

    def test_invalid_monitor_and_region_do_not_create_or_read_backends(self):
        for config in (replace(self.config, monitor=3),
                       replace(self.config, region=(-201, -20, 30, 30)),
                       replace(self.config, region=(900, -20, 30, 30))):
            with self.assertRaises(ValueError):
                self.source.read(config)
        self.gpu_factory.assert_not_called()
        self.assert_no_cpu_capture()

    def test_non_windows_does_not_initialize_windows_gpu_or_gdi(self):
        with patch("vrization_host.capture.os.name", "posix"):
            self.assert_frame(self.source.read(self.config), (384, 640))
        self.layout_factory.assert_not_called()
        self.gpu_factory.assert_not_called()
        self.gdi_factory.assert_not_called()
        self.screen.grab.assert_called_once_with(self.monitors[2])

    def test_close_attempts_every_resource_after_an_error_and_allows_a_new_session(self):
        self.source.read(self.config)
        self.source._native = self.gdi  # Both optional backends may own handles after prior selections.
        self.gpu.close.side_effect = OSError("GPU release failed")
        self.gdi.close.side_effect = OSError("GDI release failed")
        with self.assertRaisesRegex(OSError, "GPU release failed"):
            self.source.close()
        self.gpu.close.assert_called_once()
        self.gdi.close.assert_called_once()
        self.screen.close.assert_called_once()
        self.source.close()
        self.assertEqual(self.screen.close.call_count, 1)
        self.gpu_factory.return_value = self.make_gpu()
        self.assert_frame(self.source.read(self.config), (384, 640))
        self.assertEqual(self.mss_factory.call_count, 2)


if __name__ == "__main__":
    unittest.main()
