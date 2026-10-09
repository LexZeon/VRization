"""Fake system APIs: exact rectangles, owned resources and safe fallback only."""
import ctypes
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from vrization_host.capture import CaptureConfig, MssCaptureSource, capture_rectangle
from vrization_host.windows_capture import CaptureLayoutChanged, WindowsDisplayLayout, WindowsGdiCapture


class FakeGdi:
    def __init__(self, failure=None):
        self.failure, self.calls, self.buffers, self.headers = failure, [], [], []
        self.user = SimpleNamespace(GetDC=self.function("GetDC", 10),
                                    ReleaseDC=self.function("ReleaseDC", 1))
        self.gdi = SimpleNamespace(**{name: self.function(name, result) for name, result in (
            ("CreateCompatibleDC", 20), ("DeleteDC", 1), ("CreateDIBSection", 30),
            ("SelectObject", 40), ("DeleteObject", 1), ("SetStretchBltMode", 3),
            ("SetBrushOrgEx", 1), ("StretchBlt", 1), ("GdiFlush", 1))})

    def function(self, name, result):
        def run(*args):
            self.calls.append((name, args))
            if name == self.failure:
                return 0
            if name == "CreateDIBSection":
                header = args[1]._obj.header
                self.headers.append((header.size, header.width, header.height, header.bit_count, header.compression))
                buffer = ctypes.create_string_buffer(header.width * -header.height * 4)
                self.buffers.append(buffer)
                args[3]._obj.value = ctypes.addressof(buffer)
            return result
        return Mock(side_effect=run)

    def load(self, name, **kwargs):
        return self.user if name == "user32" else self.gdi


class NativeCaptureTests(unittest.TestCase):
    def test_top_down_bgrx_preserves_negative_coordinates_and_reuses_dib(self):
        fake = FakeGdi()
        backend = WindowsGdiCapture(fake.load)
        rectangle = {"left": -2160, "top": -100, "width": 2160, "height": 3840}
        for _ in range(2):
            self.assertEqual(len(backend.grab(rectangle, (540, 960))), 540 * 960 * 4)
        self.assertEqual(fake.headers, [(40, 540, -960, 32, 0)])
        self.assertEqual(fake.gdi.CreateDIBSection.call_count, 1)
        for call in fake.gdi.StretchBlt.call_args_list:
            self.assertEqual(call.args, (20, 0, 0, 540, 960, 10, -2160, -100, 2160, 3840, 0x40CC0020))
        names = [name for name, _ in fake.calls]
        self.assertLess(names.index("SetStretchBltMode"), names.index("SetBrushOrgEx"))
        self.assertLess(names.index("StretchBlt"), names.index("GdiFlush"))
        backend.close(); backend.close()
        fake.gdi.SelectObject.assert_called_with(20, 40)
        fake.gdi.DeleteDC.assert_called_once_with(20)
        fake.gdi.DeleteObject.assert_called_once_with(30)
        fake.user.ReleaseDC.assert_called_once_with(None, 10)

    def test_size_change_releases_old_resources_before_reallocation(self):
        fake = FakeGdi(); backend = WindowsGdiCapture(fake.load)
        rectangle = {"left": 3840, "top": 0, "width": 2160, "height": 3840}
        backend.grab(rectangle, (540, 960)); backend.grab(rectangle, (720, 1280)); backend.close()
        self.assertEqual([header[1:3] for header in fake.headers], [(540, -960), (720, -1280)])
        self.assertEqual(fake.user.ReleaseDC.call_count, 2)
        self.assertEqual(fake.gdi.DeleteObject.call_count, 2)

    def test_partial_allocation_failure_closes_every_created_handle(self):
        for failure, bitmap_count in (("CreateCompatibleDC", 0), ("CreateDIBSection", 0),
                                      ("SelectObject", 1), ("SetStretchBltMode", 1), ("SetBrushOrgEx", 1)):
            fake = FakeGdi(failure); backend = WindowsGdiCapture(fake.load)
            with self.assertRaises(OSError):
                backend.grab({"left": 0, "top": 0, "width": 16, "height": 16}, (16, 16))
            backend.close()
            fake.user.ReleaseDC.assert_called_once_with(None, 10)
            self.assertEqual(fake.gdi.DeleteObject.call_count, bitmap_count)
            self.assertEqual(fake.gdi.DeleteDC.call_count, int(failure != "CreateCompatibleDC"))

    def test_failed_blit_or_flush_never_returns_stale_pixels(self):
        for failure in ("StretchBlt", "GdiFlush"):
            fake = FakeGdi(failure); backend = WindowsGdiCapture(fake.load)
            with patch("vrization_host.windows_capture.ctypes.string_at") as copy:
                with self.assertRaises(OSError):
                    backend.grab({"left": 0, "top": 0, "width": 16, "height": 16}, (16, 16))
                copy.assert_not_called()
            backend.close()
            fake.gdi.DeleteObject.assert_called_once()


class SelectionAndFallbackTests(unittest.TestCase):
    monitors = [dict(left=-100, top=-200, width=1000, height=1000),
                dict(left=-100, top=-200, width=500, height=1000),
                dict(left=400, top=0, width=500, height=800)]

    def test_monitor_region_and_out_of_bounds_never_choose_a_different_screen(self):
        self.assertEqual(capture_rectangle(CaptureConfig(monitor=2), self.monitors), self.monitors[2])
        region = (-50, -100, 300, 400)
        self.assertEqual(capture_rectangle(CaptureConfig(monitor=2, region=region), self.monitors),
                         dict(zip(("left", "top", "width", "height"), region)))
        for config in (CaptureConfig(monitor=3), CaptureConfig(monitor=2, region=(-101, 0, 30, 30)),
                       CaptureConfig(monitor=2, region=(880, 0, 30, 30))):
            with self.assertRaises(ValueError): capture_rectangle(config, self.monitors)

    def test_native_error_falls_back_to_exact_same_selection_once(self):
        screen = Mock()
        screen.monitors = self.monitors
        screen.grab.return_value = SimpleNamespace(size=(500, 800), bgra=bytes(500 * 800 * 4))
        native = Mock(); native.grab.side_effect = OSError("unsupported")
        source = MssCaptureSource(); source._screen = screen
        with patch("vrization_host.capture.os.name", "nt"), \
                patch("vrization_host.windows_capture.WindowsDisplayLayout"), \
                patch("vrization_host.windows_capture.WindowsGdiCapture", return_value=native) as factory:
            for _ in range(2):
                frame = source.read(CaptureConfig(monitor=2, width=960))
                self.assertEqual((frame.width, frame.height), (500, 800))
            factory.assert_called_once()
            native.grab.assert_called_once_with(self.monitors[2], (500, 800))
            native.close.assert_called_once()
            self.assertEqual([call.args[0] for call in screen.grab.call_args_list], [self.monitors[2]] * 2)
        source.close(); screen.close.assert_called_once()

    def test_non_windows_path_does_not_initialize_native_apis(self):
        screen = Mock(); screen.monitors = self.monitors
        screen.grab.return_value = SimpleNamespace(size=(500, 800), bgra=bytes(500 * 800 * 4))
        source = MssCaptureSource(); source._screen = screen
        with patch("vrization_host.capture.os.name", "posix"), \
                patch("vrization_host.windows_capture.WindowsGdiCapture") as factory:
            source.read(CaptureConfig(monitor=2)); factory.assert_not_called()
        source.close()


class LayoutGuardTests(unittest.TestCase):
    def make_guard(self, layouts):
        def enumerate_monitors(dc, clip, callback, parameter):
            for index in range(len(layouts)):
                if not callback(index + 1, None, None, parameter): return 0
            return 1

        def monitor_info(handle, pointer):
            device, left, top, width, height = layouts[handle - 1]
            info = pointer._obj
            info.device = device
            info.monitor.left, info.monitor.top = left, top
            info.monitor.right, info.monitor.bottom = left + width, top + height
            return 1

        user = SimpleNamespace(EnumDisplayMonitors=Mock(side_effect=enumerate_monitors),
                               GetMonitorInfoW=Mock(side_effect=monitor_info))
        return WindowsDisplayLayout(lambda *args, **kwargs: user)

    def test_moved_or_replaced_display_rejects_stale_mss_coordinates(self):
        expected = [dict(left=0, top=0, width=6000, height=3840),
                    dict(left=0, top=0, width=3840, height=2160),
                    dict(left=3840, top=0, width=2160, height=3840)]
        for change in (("ASUS", 2560, 0, 2160, 3840), ("Other display", 3840, 0, 2160, 3840)):
            layouts = [("Primary", 0, 0, 3840, 2160), ("ASUS", 3840, 0, 2160, 3840)]
            guard = self.make_guard(layouts)
            guard.validate(expected)
            layouts[1] = change
            with self.assertRaises(CaptureLayoutChanged): guard.validate(expected)

        # A change between MSS enumeration and the very first native read fails too.
        guard = self.make_guard([("Primary", 0, 0, 2560, 1440), ("ASUS", 2560, 0, 2160, 3840)])
        with self.assertRaises(CaptureLayoutChanged): guard.validate(expected)

    def test_layout_failure_cannot_fall_back_or_read_any_pixels(self):
        source = MssCaptureSource()
        source._screen = Mock(monitors=SelectionAndFallbackTests.monitors)
        source._layout = Mock()
        source._layout.validate.side_effect = CaptureLayoutChanged("display moved")
        with patch("vrization_host.capture.os.name", "nt"), \
                patch("vrization_host.windows_capture.WindowsGdiCapture") as factory:
            with self.assertRaises(CaptureLayoutChanged): source.read(CaptureConfig(monitor=2))
            factory.assert_not_called()
        source._screen.grab.assert_not_called()
        source.close()


if __name__ == "__main__":
    unittest.main()
