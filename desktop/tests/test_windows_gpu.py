"""System-only GPU capture regressions using fake COM and owned CPU buffers.

No GPU, display capture, shader compiler, or third-party package is used.
The fake slots independently follow Microsoft's C vtable declarations.
"""
import ctypes
from collections import Counter
from contextlib import ExitStack
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid
import math

from vrization_host import windows_gpu as gpu


class FakeGpu:
    def __init__(self, *, failure=None):
        self.failure = failure
        self.objects, self.references = {}, Counter()
        self.releases, self.calls, self.buffers = Counter(), [], []
        self.next_id = 100
        self.layout = (("PRIMARY", 1, (0, 0, 32, 32), 1),
                       ("ASUS", 2, (-24, -8, 0, 24), 0))
        self.outputs = [dict(name="PRIMARY", monitor=1, rect=(0, 0, 32, 32), rotation=0),
                        dict(name="ASUS", monitor=2, rect=(-24, -8, 0, 24), rotation=90)]
        self.acquire_status = []
        self.protected = False
        self.held = False
        self.frames = 0
        self.padding = 8
        self.force_bad_pitch = False
        self.change_layout_on_map = False
        self.shaders = []
        self.user = SimpleNamespace(SetThreadDpiAwarenessContext=Mock(return_value=123),
                                    GetMonitorInfoW=Mock(), EnumDisplayMonitors=Mock(),
                                    EnumDisplayDevicesW=Mock())
        self.dxgi = SimpleNamespace(CreateDXGIFactory1=Mock(side_effect=self.create_factory))
        self.d3d = SimpleNamespace(D3D11CreateDevice=Mock(side_effect=self.create_device))

    @staticmethod
    def hr(value):
        return ctypes.c_int32(value).value

    @staticmethod
    def ptr(value):
        return ctypes.cast(value, ctypes.c_void_p).value or 0

    @staticmethod
    def put(out, value):
        ctypes.cast(out, ctypes.POINTER(ctypes.c_void_p)).contents.value = value

    def new(self, kind, **attributes):
        self.next_id += 1
        self.objects[self.next_id] = dict(kind=kind, **attributes)
        self.references[self.next_id] += 1
        return self.next_id

    def load(self, name):
        if name == "user32.dll": return self.user
        if name == "dxgi.dll": return self.dxgi
        if name == "d3d11.dll": return self.d3d
        raise AssertionError("Unexpected system DLL: " + name)

    def create_factory(self, iid, out):
        self.put(out, self.new("factory"))
        return self.hr(0x80004005) if self.failure == "factory" else 0

    def create_device(self, adapter, driver, software, flags, levels, count, sdk, device, level, context):
        self.assert_adapter = self.objects[self.ptr(adapter)]["kind"]
        self.put(device, self.new("device"))
        self.put(context, self.new("context"))
        ctypes.cast(level, ctypes.POINTER(ctypes.c_uint32)).contents.value = 0xb000
        return self.hr(0x80004005) if self.failure == "device" else 0

    def compile(self, text, entry, profile):
        self.shaders.append((text, profile))
        return b"fake-original-shader"

    def display_identity(self, desc):
        return "MONITOR\\" + ("AUS2768" if desc.DeviceName == "ASUS" else "OTHER") + "\\TEST"

    def output_desc(self, obj, target):
        output = self.outputs[obj["index"]]
        target.DeviceName = output["name"]
        target.Monitor = output["monitor"]
        target.AttachedToDesktop = 1
        target.Rotation = {0: 1, 90: 2, 180: 3, 270: 4}[output["rotation"]]
        r = target.DesktopCoordinates
        r.left, r.top, r.right, r.bottom = output["rect"]

    def invoke(self, pointer, slot, result, args, *values):
        handle = self.ptr(pointer)
        obj = self.objects[handle]
        kind = obj["kind"]
        if self.references[handle] <= 0:
            raise AssertionError("COM interface used after its final Release")
        self.calls.append((kind, slot, handle, values))
        if slot == 1:
            self.references[handle] += 1
            return self.references[handle]
        if slot == 2:
            self.references[handle] -= 1
            self.releases[handle] += 1
            if self.references[handle] < 0:
                raise AssertionError("COM resource released too many times")
            return self.references[handle]
        if slot == 0:
            iid = str(uuid.UUID(bytes_le=ctypes.string_at(values[0], 16)))
            if iid == "00cddea8-939b-4b83-a340-a685226666cc":
                acquired = self.new("output1", index=obj["index"])
            elif iid == "6f15aaf2-d208-4e89-9ab4-489535d34f9c":
                acquired = self.new("source_texture")
            else:
                raise AssertionError("Unexpected queried interface " + iid)
            self.put(values[1], acquired)
            return 0
        if kind == "factory" and slot == 12:
            if int(values[0]) > 0: return self.hr(0x887a0002)
            self.put(values[1], self.new("adapter")); return 0
        if kind == "adapter" and slot == 7:
            index = int(values[0])
            if index >= len(self.outputs): return self.hr(0x887a0002)
            self.put(values[1], self.new("output", index=index)); return 0
        if kind in ("output", "output1") and slot == 7:
            self.output_desc(obj, ctypes.cast(values[0], ctypes.POINTER(gpu.OutputDesc)).contents)
            return 0
        if kind == "output1" and slot == 22:
            self.put(values[1], self.new("duplicator", index=obj["index"]))
            if self.failure == "unsupported_duplication": return self.hr(0x887a0004)
            return self.hr(0x80004005) if self.failure == "duplication" else 0
        if kind == "duplicator" and slot == 8:
            if self.held: raise AssertionError("Acquire while previous frame remains held")
            status = self.acquire_status.pop(0) if self.acquire_status else 0
            if status: return self.hr(status)
            self.held = True; self.frames += 1
            info = ctypes.cast(values[1], ctypes.POINTER(gpu.DuplicationFrameInfo)).contents
            info.LastPresentTime = self.frames
            info.AccumulatedFrames = 1
            info.ProtectedContentMaskedOut = int(self.protected)
            self.put(values[2], self.new("desktop_resource"))
            return 0
        if kind == "duplicator" and slot == 14:
            if not self.held: raise AssertionError("ReleaseFrame without an acquisition")
            self.held = False
            return self.hr(0x80004005) if self.failure == "release_frame" else 0
        if kind in ("source_texture", "texture") and slot == 10:
            desc = ctypes.cast(values[0], ctypes.POINTER(gpu.TextureDesc)).contents
            source = self.outputs[1]
            l, t, r, b = source["rect"]
            logical = (r - l, b - t)
            dimensions = logical[::-1] if source["rotation"] in (90, 270) else logical
            desc.Width, desc.Height = (obj["width"], obj["height"]) if kind == "texture" else dimensions
            desc.MipLevels = desc.ArraySize = desc.SampleDesc.Count = 1
            desc.Format = 87
            return None
        if kind == "device" and slot in (5, 7, 9, 12, 15, 22, 23):
            label = {5: "texture", 7: "shader_view", 9: "render_view", 12: "vertex_shader",
                     15: "pixel_shader", 22: "rasterizer", 23: "sampler"}[slot]
            attributes = {}
            if slot == 5:
                desc = ctypes.cast(values[0], ctypes.POINTER(gpu.TextureDesc)).contents
                attributes = dict(width=int(desc.Width), height=int(desc.Height), usage=int(desc.Usage))
            self.put(values[-1], self.new(label, **attributes))
            return self.hr(0x80004005) if self.failure == label else 0
        if kind == "device" and slot == 37: return 0xb000
        if kind == "context" and slot == 14:
            if self.references[self.ptr(values[0])] <= 0:
                raise AssertionError("Map of a released texture")
            texture = self.objects[self.ptr(values[0])]
            width, height = texture["width"], texture["height"]
            stride = width * 4; pitch = stride + self.padding
            rows = [bytes(((self.frames + row + column) % 256 for column in range(stride)))
                    + bytes([255]) * self.padding for row in range(height)]
            if self.protected:
                # Simulate the already-masked DXGI surface: black left half,
                # ordinary pixels on the right. Capture must preserve this.
                black = bytes((0, 0, 0, 255)) * (width // 2)
                rows = [black + row[len(black):] for row in rows]
            buffer = ctypes.create_string_buffer(b"".join(rows))
            self.buffers.append(buffer)
            mapped = ctypes.cast(values[-1], ctypes.POINTER(gpu.MappedResource)).contents
            mapped.pData = ctypes.addressof(buffer)
            mapped.RowPitch = stride - 1 if self.force_bad_pitch else pitch
            if self.change_layout_on_map:
                self.layout = (self.layout[0], ("ASUS", 2, (-100, -8, -76, 24), 0))
            return self.hr(0x80004005) if self.failure == "map" else 0
        if kind == "context" and slot == 47:
            if any(self.references[self.ptr(value)] <= 0 for value in values):
                raise AssertionError("GPU copy of a released texture")
            return None
        if kind == "context" and slot == 15 and self.failure == "unmap":
            raise OSError("Fake unmap failure")
        if kind == "context" and slot in (8, 9, 10, 11, 13, 15, 17, 24, 33, 43, 44, 47, 110, 111):
            return None
        raise AssertionError((kind, slot, values))


class WindowsGpuTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeGpu()
        self.stack = ExitStack()
        self.stack.enter_context(patch.object(gpu, "invoke", side_effect=self.fake.invoke))
        self.stack.enter_context(patch.object(gpu, "system_library", side_effect=self.fake.load))
        self.stack.enter_context(patch.object(gpu, "compile_hlsl", side_effect=self.fake.compile))
        self.stack.enter_context(patch.object(gpu.ct, "WINFUNCTYPE", getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE), create=True))
        self.stack.enter_context(patch.object(gpu.WindowsGpuCapture, "_monitor_layout", lambda owner: self.fake.layout))
        self.stack.enter_context(patch.object(gpu.WindowsGpuCapture, "_display_identity", lambda owner, desc: self.fake.display_identity(desc)))
        self.capture = gpu.WindowsGpuCapture()
        self.rect = dict(left=-24, top=-8, width=24, height=32)

    def tearDown(self):
        try:
            self.capture.close()
        finally:
            self.stack.close()

    def test_single_output_identity_negative_origin_and_owned_rowpitch(self):
        result = self.capture.grab(self.rect, (12, 16))
        self.assertEqual(len(result), 12 * 16 * 4)
        expected = b"".join(bytes((1 + row + column) % 256 for column in range(48)) for row in range(16))
        self.assertEqual(result, expected)
        ctypes.memset(ctypes.addressof(self.fake.buffers[-1]), 0, ctypes.sizeof(self.fake.buffers[-1]))
        self.assertEqual(result, expected)
        duplicator_calls = [call for call in self.fake.calls if call[0] == "output1" and call[1] == 22]
        self.assertEqual(len(duplicator_calls), 1)
        self.assertEqual(self.fake.objects[duplicator_calls[0][2]]["index"], 1)
        self.assertFalse(self.fake.held)

    def test_none_and_force_latest_after_size_and_region_change(self):
        self.capture.grab(self.rect, (12, 16))
        self.fake.acquire_status = [0x887a0027, 0x887a0027]
        self.assertIsNone(self.capture.grab(self.rect, (12, 16)))
        region = dict(left=-20, top=-4, width=16, height=24)
        result = self.capture.grab(region, (8, 12), force_latest=True)
        self.assertEqual(len(result), 8 * 12 * 4)
        self.assertEqual(self.fake.frames, 1)
        self.assertFalse(self.fake.held)
        self.capture.close()
        self.assertTrue(all(count == 0 for count in self.fake.references.values()))

    def test_access_loss_does_not_recover_or_choose_another_display(self):
        self.capture.grab(self.rect, (12, 16))
        self.fake.acquire_status = [0x887a0026]
        with self.assertRaises(OSError):
            self.capture.grab(self.rect, (12, 16))
        self.assertEqual(self.fake.d3d.D3D11CreateDevice.call_count, 1)
        self.assertFalse(self.fake.held)
        with self.assertRaises(OSError):
            self.capture.grab(self.rect, (12, 16))
        self.capture.close()
        self.assertTrue(all(count == 0 for count in self.fake.references.values()))

    def test_layout_change_is_fatal_before_any_new_acquisition(self):
        self.capture.grab(self.rect, (12, 16))
        self.fake.layout = (("PRIMARY", 1, (0, 0, 32, 32), 1),
                            ("ASUS", 2, (-100, -8, -76, 24), 0))
        with self.assertRaises(gpu.CaptureLayoutChanged):
            self.capture.grab(self.rect, (12, 16))
        self.assertEqual(self.fake.frames, 1)

    def test_cross_output_is_only_unsupported_not_a_primary_capture(self):
        with self.assertRaises(gpu.UnsupportedGpuCapture):
            self.capture.grab(dict(left=-8, top=0, width=16, height=16), (8, 8))
        self.fake.d3d.D3D11CreateDevice.assert_not_called()
        self.assertEqual(self.fake.frames, 0)

    def test_os_masked_desktop_is_read_back_unchanged_and_released(self):
        self.fake.protected = True
        pixels = self.capture.grab(self.rect, (12, 16))
        expected = b"".join(bytes((0, 0, 0, 255)) * 6
                            + bytes((1 + row + column) % 256 for column in range(24, 48))
                            for row in range(16))
        self.assertEqual(pixels, expected)
        self.assertTrue(self.capture.protected_content_masked)
        self.assertFalse(self.fake.held)
        self.assertEqual(len(self.fake.buffers), 1)
        self.assertEqual(sum(kind == "duplicator" and slot == 14
                             for kind, slot, *_ in self.fake.calls), 1)
        self.fake.acquire_status = [0x887a0027]
        self.assertIs(self.capture.grab(self.rect, (12, 16), force_latest=True), pixels)
        self.assertTrue(self.capture.protected_content_masked)
        self.fake.protected = False
        self.assertIsNot(self.capture.grab(self.rect, (12, 16)), pixels)
        self.assertFalse(self.capture.protected_content_masked)
        self.capture.close()
        self.assertIsNone(self.capture._last_frame)
        self.assertTrue(all(count == 0 for count in self.fake.references.values()))

    def test_masked_frame_release_failure_is_fatal_and_invalidates_cache(self):
        self.capture.grab(self.rect, (12, 16))
        self.fake.protected = True
        self.fake.failure = "release_frame"
        with self.assertRaisesRegex(OSError, "ReleaseFrame"):
            self.capture.grab(self.rect, (12, 16))
        self.assertFalse(self.fake.held)
        self.assertTrue(self.capture.closed)
        self.assertIsNone(self.capture._last_frame)
        self.assertFalse(self.capture.protected_content_masked)
        self.assertTrue(all(count == 0 for count in self.fake.references.values()))
        with self.assertRaisesRegex(OSError, "closed"):
            self.capture.grab(self.rect, (12, 16), force_latest=True)

    def test_invalid_pitch_unmaps_and_releases_frame_before_error(self):
        self.fake.force_bad_pitch = True
        with self.assertRaises(OSError):
            self.capture.grab(self.rect, (12, 16))
        self.assertTrue(any(c[0] == "context" and c[1] == 15 for c in self.fake.calls))
        self.assertFalse(self.fake.held)
        self.assertTrue(self.capture.closed)
        self.assertTrue(all(count == 0 for count in self.fake.references.values()))

    def test_partial_com_creation_failure_cleans_every_output_reference(self):
        for operation in ("factory", "device", "duplication", "texture", "shader_view", "pixel_shader", "sampler"):
            with self.subTest(operation=operation):
                self.capture.close()
                self.fake.failure = operation
                self.capture = gpu.WindowsGpuCapture()
                with self.assertRaises(OSError):
                    self.capture.grab(self.rect, (12, 16))
                self.capture.close()
                self.assertTrue(all(count == 0 for count in self.fake.references.values()), self.fake.references)

    def test_thread_ownership_and_idempotent_close(self):
        self.capture.grab(self.rect, (12, 16))
        errors = []

        def other_thread():
            for operation in (lambda: self.capture.grab(self.rect, (12, 16)), self.capture.close):
                try: operation()
                except OSError: errors.append(True)

        thread = threading.Thread(target=other_thread)
        thread.start(); thread.join()
        self.assertEqual(errors, [True, True])
        self.capture.close(); self.capture.close()
        self.assertTrue(all(count == 0 for count in self.fake.references.values()))

    def test_cached_layout_and_explicit_output_identity_are_checked_before_device_creation(self):
        self.capture.close()
        expected = [dict(left=-24, top=-8, width=56, height=40),
                    dict(left=0, top=0, width=32, height=32),
                    dict(left=-25, top=-8, width=24, height=32)]
        self.capture = gpu.WindowsGpuCapture(expected_monitors=expected)
        with self.assertRaises(gpu.CaptureLayoutChanged):
            self.capture.grab(self.rect, (12, 16))
        self.fake.d3d.D3D11CreateDevice.assert_not_called()
        self.capture.close()
        self.capture = gpu.WindowsGpuCapture(expected_output=dict(device_name="PRIMARY", hmonitor=1))
        with self.assertRaises(gpu.CaptureLayoutChanged):
            self.capture.grab(self.rect, (12, 16))
        self.fake.d3d.D3D11CreateDevice.assert_not_called()
        self.assertEqual(self.fake.frames, 0)

    def test_dxgi_hmonitor_and_windows_monitor_must_agree(self):
        self.fake.layout = (self.fake.layout[0], ("ASUS", 99, (-24, -8, 0, 24), 0))
        with self.assertRaises(gpu.CaptureLayoutChanged):
            self.capture.grab(self.rect, (12, 16))
        self.fake.d3d.D3D11CreateDevice.assert_not_called()
        self.assertEqual(self.fake.frames, 0)

    def test_layout_changes_during_gpu_readback_never_publish_a_completed_frame(self):
        self.fake.change_layout_on_map = True
        with self.assertRaises(gpu.CaptureLayoutChanged):
            self.capture.grab(self.rect, (12, 16), force_latest=True)
        self.assertEqual(self.fake.frames, 1)
        self.assertEqual(len(self.fake.buffers), 1)
        self.assertFalse(self.fake.held)
        self.assertTrue(self.capture.closed)
        self.assertTrue(all(count == 0 for count in self.fake.references.values()))

    def test_map_failure_does_not_unmap_and_unmap_failure_still_releases_frame(self):
        for operation in ("map", "unmap"):
            with self.subTest(operation=operation):
                self.capture.close()
                self.fake.failure = operation
                self.capture = gpu.WindowsGpuCapture()
                before = sum(c[0] == "context" and c[1] == 15 for c in self.fake.calls)
                with self.assertRaises(OSError):
                    self.capture.grab(self.rect, (12, 16))
                after = sum(c[0] == "context" and c[1] == 15 for c in self.fake.calls)
                self.assertEqual(after - before, int(operation == "unmap"))
                self.assertFalse(self.fake.held)
                self.assertTrue(all(count == 0 for count in self.fake.references.values()))

    def test_initial_unsupported_driver_is_distinct_from_runtime_access_loss(self):
        self.fake.failure = "unsupported_duplication"
        with self.assertRaises(gpu.UnsupportedGpuCapture):
            self.capture.grab(self.rect, (12, 16))
        self.assertEqual(self.fake.frames, 0)
        self.assertTrue(all(count == 0 for count in self.fake.references.values()))

    def test_invalid_request_allocates_no_device_or_screen_resource(self):
        for rectangle, size in [(dict(self.rect, left=True), (12, 16)),
                                (dict(self.rect, width=0), (12, 16)),
                                (self.rect, (25, 16)), (self.rect, (12.0, 16))]:
            with self.assertRaises(ValueError):
                self.capture.grab(rectangle, size)
        self.fake.dxgi.CreateDXGIFactory1.assert_not_called()
        self.assertEqual(self.fake.objects, {})


class RotationCropTests(unittest.TestCase):
    def test_all_four_rotations_restore_an_asymmetric_logical_image(self):
        raw = [["A", "B"], ["C", "D"], ["E", "F"]]
        expected = {0: [["A", "B"], ["C", "D"], ["E", "F"]],
                    90: [["E", "C", "A"], ["F", "D", "B"]],
                    180: [["F", "E"], ["D", "C"], ["B", "A"]],
                    270: [["B", "D", "F"], ["A", "C", "E"]]}
        for rotation, values in expected.items():
            height, width = len(values), len(values[0])
            actual = []
            for row in range(height):
                result = []
                for column in range(width):
                    u, v = gpu.source_uv((column + .5) / width, (row + .5) / height, rotation)
                    result.append(raw[math.floor(v * 3)][math.floor(u * 2)])
                actual.append(result)
            self.assertEqual(actual, values)

    def test_logical_crop_precedes_inverse_surface_rotation(self):
        local = (4, 4, 16, 24)
        logical = (24, 32)
        u, v = gpu.region_uv(.25, .5, local, logical)
        self.assertAlmostEqual(u, 1 / 3)
        self.assertAlmostEqual(v, .5)
        surface_x, surface_y = gpu.source_uv(u, v, 90)
        self.assertAlmostEqual(surface_x, .5)
        self.assertAlmostEqual(surface_y, 2 / 3)
        shader = gpu.pixel_hlsl(90, local, logical)
        self.assertLess(shader.index("uv = float2"), shader.index("SampleLevel"))
        self.assertIn("float2(uv.y, 1.0 - uv.x)", shader)

    def test_crop_cannot_escape_output_and_resize_cannot_upscale(self):
        for crop, target in [((-1, 0, 16, 24), (8, 12)),
                             ((8, 0, 24, 32), (12, 16)),
                             ((0, 0, 16, 24), (17, 12))]:
            with self.assertRaises(ValueError):
                gpu.GpuScaler._validate_dimensions((24, 32), target, 90, crop)


if __name__ == "__main__":
    unittest.main()
