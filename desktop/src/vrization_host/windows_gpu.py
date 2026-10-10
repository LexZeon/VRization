"""Original system-only DXGI capture with GPU crop, rotation and linear resize.

Runtime dependencies: Python ctypes and Windows system DLLs only. No DXcam,
NumPy, comtypes or third-party native capture binary is imported or bundled.
Bindings, lifecycle and shaders below are original VRization MIT code.

Research acknowledgements (ideas/API requirements, no copied application code):
* DXcam 0.3.0, Rain, MIT, informed adapter/output binding, rotation and staging
  readback investigation. https://github.com/ra1nty/DXcam/tree/de356cb5a39f50645d495c522fabb03e984728e7
* Win32CaptureSample, Robert Mikhayelyan, MIT, informed the comparison of Win32
  capture approaches. https://github.com/robmikh/Win32CaptureSample/tree/49fefe79fd9b11025f0b5eb91783a98888516070
* Microsoft Windows-classic-samples, MIT, and official API documentation informed
  DXGI lifecycle/rotation and D3D texture ownership requirements.
  https://github.com/microsoft/Windows-classic-samples/tree/434f6002bdf9cf9829406c3ff2b33387982d6168/Samples/DXGIDesktopDuplication
  https://learn.microsoft.com/windows/win32/direct3ddxgi/desktop-dup-api
  https://learn.microsoft.com/windows/win32/api/d3d11/nf-d3d11-d3d11createdevice
  https://learn.microsoft.com/windows/win32/api/d3dcompiler/nf-d3dcompiler-d3dcompile
  https://learn.microsoft.com/windows/win32/api/dxgi1_2/nf-dxgi1_2-idxgioutputduplication-acquirenextframe

Import performs no Windows calls. All acquired resources belong to one capture
thread. Only UnsupportedGpuCapture permits a caller's same-region fallback;
layout/access/identity/other resource errors fail closed without recovery.
"""
from __future__ import annotations

import ctypes as ct
from ctypes import wintypes as wt
from pathlib import Path
import threading
import uuid

from .windows_capture import CaptureLayoutChanged


class UnsupportedGpuCapture(OSError):
    """A verified initial selection/API cannot use GPU capture; same-rect fallback is allowed."""


UINT = ct.c_uint32
INT = ct.c_int32
FLOAT = ct.c_float
PTR = ct.c_void_p
HRESULT = ct.c_int32
SIZE_T = ct.c_size_t


class SampleDesc(ct.Structure):
    _fields_ = [("Count", UINT), ("Quality", UINT)]


class TextureDesc(ct.Structure):
    _fields_ = [
        ("Width", UINT), ("Height", UINT), ("MipLevels", UINT),
        ("ArraySize", UINT), ("Format", UINT), ("SampleDesc", SampleDesc),
        ("Usage", UINT), ("BindFlags", UINT), ("CPUAccessFlags", UINT),
        ("MiscFlags", UINT),
    ]


class SamplerDesc(ct.Structure):
    _fields_ = [
        ("Filter", UINT), ("AddressU", UINT), ("AddressV", UINT),
        ("AddressW", UINT), ("MipLODBias", FLOAT), ("MaxAnisotropy", UINT),
        ("ComparisonFunc", UINT), ("BorderColor", FLOAT * 4),
        ("MinLOD", FLOAT), ("MaxLOD", FLOAT),
    ]


class RasterizerDesc(ct.Structure):
    _fields_ = [
        ("FillMode", UINT), ("CullMode", UINT),
        ("FrontCounterClockwise", INT), ("DepthBias", INT),
        ("DepthBiasClamp", FLOAT), ("SlopeScaledDepthBias", FLOAT),
        ("DepthClipEnable", INT), ("ScissorEnable", INT),
        ("MultisampleEnable", INT), ("AntialiasedLineEnable", INT),
    ]


class Viewport(ct.Structure):
    _fields_ = [(name, FLOAT) for name in
                ("TopLeftX", "TopLeftY", "Width", "Height", "MinDepth", "MaxDepth")]


class MappedResource(ct.Structure):
    _fields_ = [("pData", PTR), ("RowPitch", UINT), ("DepthPitch", UINT)]


class Guid(ct.Structure):
    _fields_ = [("Data1", UINT), ("Data2", ct.c_uint16),
                ("Data3", ct.c_uint16), ("Data4", ct.c_ubyte * 8)]

    @classmethod
    def from_text(cls, text):
        return cls.from_buffer_copy(uuid.UUID(text).bytes_le)


class OutputDesc(ct.Structure):
    _fields_ = [("DeviceName", wt.WCHAR * 32), ("DesktopCoordinates", wt.RECT),
                ("AttachedToDesktop", INT), ("Rotation", UINT), ("Monitor", PTR)]


class PointerPosition(ct.Structure):
    _fields_ = [("Position", wt.POINT), ("Visible", INT)]


class DuplicationFrameInfo(ct.Structure):
    _fields_ = [("LastPresentTime", ct.c_int64), ("LastMouseUpdateTime", ct.c_int64),
                ("AccumulatedFrames", UINT), ("RectsCoalesced", INT),
                ("ProtectedContentMaskedOut", INT), ("PointerPosition", PointerPosition),
                ("TotalMetadataBufferSize", UINT), ("PointerShapeBufferSize", UINT)]


# Zero-based ABI vtable indices, including IUnknown/ID3D11DeviceChild slots.
# Cross-checked against Microsoft's d3d11.h C interface declarations.
DEVICE_SLOTS = {
    "CreateTexture2D": 5, "CreateShaderResourceView": 7,
    "CreateRenderTargetView": 9, "CreateVertexShader": 12,
    "CreatePixelShader": 15, "CreateRasterizerState": 22,
    "CreateSamplerState": 23, "GetFeatureLevel": 37,
    "GetDeviceRemovedReason": 39,
}
CONTEXT_SLOTS = {
    "PSSetShaderResources": 8, "PSSetShader": 9, "PSSetSamplers": 10,
    "VSSetShader": 11, "Draw": 13, "Map": 14, "Unmap": 15,
    "IASetInputLayout": 17, "IASetPrimitiveTopology": 24,
    "OMSetRenderTargets": 33, "RSSetState": 43, "RSSetViewports": 44,
    "CopyResource": 47, "ClearState": 110, "Flush": 111,
}


def pointer(obj) -> PTR:
    return PTR(ct.cast(obj, PTR).value)


def invoke(obj, slot: int, result, args, *values):
    address = pointer(obj)
    if not address.value:
        raise OSError("Null COM interface")
    table = ct.cast(address, ct.POINTER(ct.POINTER(PTR))).contents
    method = ct.WINFUNCTYPE(result, PTR, *args)(table[slot])
    return method(address, *values)


def check(hr: int, operation: str) -> None:
    if hr < 0:
        raise OSError(f"{operation} failed: HRESULT 0x{hr & 0xffffffff:08x}")


def release(obj) -> None:
    if pointer(obj).value:
        invoke(obj, 2, UINT, ())


def system_compiler():
    # An absolute system path avoids DLL lookup through the working directory.
    kernel = ct.WinDLL("kernel32", use_last_error=True)
    kernel.GetSystemDirectoryW.argtypes = [wt.LPWSTR, UINT]
    kernel.GetSystemDirectoryW.restype = UINT
    directory = ct.create_unicode_buffer(32768)
    count = kernel.GetSystemDirectoryW(directory, len(directory))
    if not 0 < count < len(directory):
        raise OSError("GetSystemDirectoryW failed")
    library = ct.WinDLL(str(Path(directory.value) / "d3dcompiler_47.dll"))
    function = library.D3DCompile
    function.argtypes = [PTR, SIZE_T, ct.c_char_p, PTR, PTR, ct.c_char_p,
                         ct.c_char_p, UINT, UINT, ct.POINTER(PTR), ct.POINTER(PTR)]
    function.restype = HRESULT
    return library, function


def system_library(name):
    kernel = ct.WinDLL("kernel32", use_last_error=True)
    kernel.GetSystemDirectoryW.argtypes = [wt.LPWSTR, UINT]
    kernel.GetSystemDirectoryW.restype = UINT
    directory = ct.create_unicode_buffer(32768)
    length = kernel.GetSystemDirectoryW(directory, len(directory))
    if not 0 < length < len(directory):
        raise OSError("GetSystemDirectoryW failed")
    return ct.WinDLL(str(Path(directory.value) / name), use_last_error=True)


def compile_hlsl(text: str, entry: str, profile: str) -> bytes:
    library, function = system_compiler()
    source = text.encode("ascii")
    code, errors = PTR(), PTR()
    try:
        hr = function(source, len(source), b"VRization-original-resize", None,
                      None, entry.encode(), profile.encode(), 0x8800, 0,
                      ct.byref(code), ct.byref(errors))
        detail = ""
        if errors.value:
            begin = invoke(errors, 3, PTR, ())
            length = invoke(errors, 4, SIZE_T, ())
            detail = ct.string_at(begin, min(length, 4096)).decode("utf-8", "replace")
        if hr < 0:
            raise OSError(f"HLSL compile 0x{hr & 0xffffffff:08x}: {detail}")
        if not code.value:
            raise OSError("D3DCompile returned no bytecode")
        begin = invoke(code, 3, PTR, ())
        length = invoke(code, 4, SIZE_T, ())
        return ct.string_at(begin, length)
    finally:
        release(errors)
        release(code)
        # Keep the DLL loaded through the blob's final Release.
        del library


VERTEX_HLSL = """
struct VertexOutput { float4 position : SV_Position; float2 uv : TEXCOORD0; };
VertexOutput main(uint id : SV_VertexID) {
    VertexOutput output;
    float2 uv = float2((id << 1) & 2, id & 2);
    output.uv = uv;
    output.position = float4(uv.x * 2.0 - 1.0, 1.0 - uv.y * 2.0, 0.0, 1.0);
    return output;
}
"""


def source_uv(u: float, v: float, rotation: int) -> tuple[float, float]:
    """Inverse of DXcam's logical clockwise orientation, for pure CPU tests."""
    if rotation == 0:
        return u, v
    if rotation == 90:
        return v, 1 - u
    if rotation == 180:
        return 1 - u, 1 - v
    if rotation == 270:
        return 1 - v, u
    raise ValueError("Unsupported DXGI rotation")


def region_uv(u: float, v: float, region, logical_size):
    """Map output coordinates to the selected logical-monitor crop."""
    left, top, width, height = region
    return ((left + u * width) / logical_size[0],
            (top + v * height) / logical_size[1])


def pixel_hlsl(rotation: int, region=None, logical_size=None) -> str:
    mapping = {0: "uv", 90: "float2(uv.y, 1.0 - uv.x)",
               180: "1.0 - uv", 270: "float2(1.0 - uv.y, uv.x)"}
    if rotation not in mapping:
        raise ValueError("Unsupported rotation")
    crop = ""
    if region is not None:
        left, top, width, height = region
        crop = (f"    uv = float2({left / logical_size[0]:.12f}, {top / logical_size[1]:.12f})"
                f" + uv * float2({width / logical_size[0]:.12f}, {height / logical_size[1]:.12f});\n")
    return ("Texture2D<float4> sourceImage : register(t0);\n"
            "SamplerState linearClamp : register(s0);\n"
            "float4 main(float4 position : SV_Position, float2 uv : TEXCOORD0) : SV_Target {\n"
            + crop +
            f"    return sourceImage.SampleLevel(linearClamp, {mapping[rotation]}, 0.0);\n"
            "}\n")


class GpuScaler:
    """Borrowed private device/context, owned GPU crop/rotation/resize resources.

    The capture session keeps the device alive and dedicates its immediate
    context to this scaler. Source texture is borrowed only during render.
    Context state is cleared; this must not receive a game engine's context.
    A GPU-owned SRV texture is necessary because duplication textures are not
    guaranteed to have D3D11_BIND_SHADER_RESOURCE. Only the small staging texture
    is ever mapped. This extra full GPU copy remains a performance unknown.
    """
    def __init__(self, device, context, logical_size: tuple[int, int],
                 rotation: int, target_size: tuple[int, int], region=None):
        self._thread = threading.get_ident()
        self.device = pointer(device)
        self.context = pointer(context)
        self.logical_size = logical_size
        self.target_size = target_size
        self.rotation = rotation
        self.region = region if region is not None else (0, 0, *logical_size)
        self._resources: list[PTR] = []
        self._source_desc_key = None
        self.source_texture = PTR()
        self.source_view = PTR()
        self.closed = False
        self._validate_dimensions(logical_size, target_size, rotation, self.region)
        try:
            level = invoke(self.device, DEVICE_SLOTS["GetFeatureLevel"], UINT, ())
            if level < 0xa000:
                raise OSError("Shader model 4 requires D3D feature level 10+")
            vertex = compile_hlsl(VERTEX_HLSL, "main", "vs_4_0")
            pixel = compile_hlsl(pixel_hlsl(rotation, self.region, logical_size), "main", "ps_4_0")
            self.vertex_shader = self._shader("CreateVertexShader", vertex)
            self.pixel_shader = self._shader("CreatePixelShader", pixel)
            self.render_texture = self._texture(self._desc(target_size, 0, 0x20, 0))
            self.render_view = self._view("CreateRenderTargetView", self.render_texture)
            self.staging_texture = self._texture(self._desc(target_size, 3, 0, 0x20000))
            sampler = SamplerDesc(0x15, 3, 3, 3, 0.0, 1, 1,
                                  (FLOAT * 4)(0, 0, 0, 0), 0.0, 3.402823466e38)
            self.sampler = self._created("CreateSamplerState", [PTR], ct.byref(sampler))
            raster = RasterizerDesc(3, 1, 0, 0, 0, 0, 1, 0, 0, 0)
            self.raster = self._created("CreateRasterizerState", [PTR], ct.byref(raster))
            self.viewport = Viewport(0, 0, *target_size, 0, 1)
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _validate_dimensions(logical, target, rotation, region=None):
        if rotation not in (0, 90, 180, 270):
            raise ValueError("Invalid rotation")
        if any(type(n) is not int or not 1 <= n <= 16384 for n in (*logical, *target)):
            raise ValueError("Invalid dimensions")
        crop = region if region is not None else (0, 0, *logical)
        if (len(crop) != 4 or any(type(n) is not int for n in crop)
                or crop[0] < 0 or crop[1] < 0 or crop[2] <= 0 or crop[3] <= 0
                or crop[0] + crop[2] > logical[0] or crop[1] + crop[3] > logical[1]):
            raise ValueError("Crop must remain inside the logical output")
        if (target[0] > crop[2] or target[1] > crop[3]
                or max(target) > 3840):
            raise ValueError("GPU capture only performs bounded downsizing")

    def _assert_thread(self):
        if threading.get_ident() != self._thread:
            raise OSError("GPU resource used from a different thread")
        if self.closed:
            raise OSError("GPU scaler is closed")

    @staticmethod
    def _desc(size, usage, bind, access):
        return TextureDesc(*size, 1, 1, 87, SampleDesc(1, 0), usage, bind, access, 0)

    def _created(self, name, args, *values):
        resource = PTR()
        hr = invoke(self.device, DEVICE_SLOTS[name], HRESULT,
                    [*args, ct.POINTER(PTR)], *values, ct.byref(resource))
        if resource.value:
            self._resources.append(resource)
        check(hr, name)
        if not resource.value:
            raise OSError(f"{name} returned a null resource")
        return resource

    def _texture(self, desc):
        return self._created("CreateTexture2D", [PTR, PTR], ct.byref(desc), None)

    def _view(self, name, texture):
        return self._created(name, [PTR, PTR], texture, None)

    def _shader(self, name, bytecode):
        buffer = ct.create_string_buffer(bytecode)
        return self._created(name, [PTR, SIZE_T, PTR], buffer, len(bytecode), None)

    def _ensure_source(self, source):
        desc = TextureDesc()
        invoke(source, 10, None, [PTR], ct.byref(desc))
        logical = self.logical_size
        expected = logical[::-1] if self.rotation in (90, 270) else logical
        if (desc.Width, desc.Height) != expected:
            raise CaptureLayoutChanged("Acquired source dimensions changed; restart streaming")
        if (desc.Format, desc.MipLevels, desc.ArraySize,
                desc.SampleDesc.Count, desc.SampleDesc.Quality) != (87, 1, 1, 1, 0):
            raise OSError("Unsupported source format/array/MSAA; no resize")
        key = (desc.Width, desc.Height, desc.Format)
        if self._source_desc_key is None:
            self.source_texture = self._texture(self._desc(expected, 0, 0x8, 0))
            self.source_view = self._view("CreateShaderResourceView", self.source_texture)
            self._source_desc_key = key
        elif key != self._source_desc_key:
            raise CaptureLayoutChanged("Source descriptor changed; restart streaming")

    def render(self, acquired_texture) -> bytes:
        self._assert_thread()
        try:
            return self._render(acquired_texture)
        except BaseException:
            # Resource construction/Map/Unmap errors are fatal. Do not retain a
            # half-prepared scaler for repeated reads or retry source creation.
            try:
                self.close()
            except BaseException:
                pass
            raise

    def _render(self, acquired_texture) -> bytes:
        self._assert_thread()
        self._ensure_source(acquired_texture)
        context = self.context
        invoke(context, CONTEXT_SLOTS["ClearState"], None, ())
        invoke(context, CONTEXT_SLOTS["CopyResource"], None, [PTR, PTR],
               self.source_texture, pointer(acquired_texture))
        invoke(context, CONTEXT_SLOTS["IASetInputLayout"], None, [PTR], None)
        invoke(context, CONTEXT_SLOTS["IASetPrimitiveTopology"], None, [UINT], 4)
        invoke(context, CONTEXT_SLOTS["VSSetShader"], None, [PTR, PTR, UINT],
               self.vertex_shader, None, 0)
        invoke(context, CONTEXT_SLOTS["PSSetShader"], None, [PTR, PTR, UINT],
               self.pixel_shader, None, 0)
        srvs = (PTR * 1)(self.source_view.value)
        samplers = (PTR * 1)(self.sampler.value)
        targets = (PTR * 1)(self.render_view.value)
        invoke(context, CONTEXT_SLOTS["PSSetShaderResources"], None,
               [UINT, UINT, PTR], 0, 1, srvs)
        invoke(context, CONTEXT_SLOTS["PSSetSamplers"], None,
               [UINT, UINT, PTR], 0, 1, samplers)
        invoke(context, CONTEXT_SLOTS["OMSetRenderTargets"], None,
               [UINT, PTR, PTR], 1, targets, None)
        invoke(context, CONTEXT_SLOTS["RSSetState"], None, [PTR], self.raster)
        invoke(context, CONTEXT_SLOTS["RSSetViewports"], None,
               [UINT, PTR], 1, ct.byref(self.viewport))
        invoke(context, CONTEXT_SLOTS["Draw"], None, [UINT, UINT], 3, 0)
        # Unbind the render target before copying, and the source SRV before
        # another frame can copy into it. This context is private to this capture session.
        invoke(context, CONTEXT_SLOTS["OMSetRenderTargets"], None,
               [UINT, PTR, PTR], 0, None, None)
        null_srv = (PTR * 1)(None)
        invoke(context, CONTEXT_SLOTS["PSSetShaderResources"], None,
               [UINT, UINT, PTR], 0, 1, null_srv)
        invoke(context, CONTEXT_SLOTS["CopyResource"], None, [PTR, PTR],
               self.staging_texture, self.render_texture)
        mapped = MappedResource()
        check(invoke(context, CONTEXT_SLOTS["Map"], HRESULT,
                     [PTR, UINT, UINT, UINT, PTR], self.staging_texture,
                     0, 1, 0, ct.byref(mapped)), "Map small staging texture")
        try:
            width, height = self.target_size
            stride = width * 4
            if not mapped.pData or not stride <= mapped.RowPitch <= stride + 65536:
                raise OSError("Invalid mapped pointer or row pitch")
            if mapped.RowPitch == stride:
                return ct.string_at(mapped.pData, stride * height)
            # Copy only active bytes. All return values own their memory before
            # Unmap; neither row pitch padding nor dangling GPU pointers escape.
            return b"".join(ct.string_at(mapped.pData + row * mapped.RowPitch, stride)
                            for row in range(height))
        finally:
            invoke(context, CONTEXT_SLOTS["Unmap"], None,
                   [PTR, UINT], self.staging_texture, 0)

    def close(self):
        if self.closed:
            return
        if threading.get_ident() != self._thread:
            raise OSError("GPU resource closed from a different thread")
        self.closed = True
        first_error = None
        # Context bindings carry COM references and must be cleared first.
        if self.context.value:
            try:
                invoke(self.context, CONTEXT_SLOTS["ClearState"], None, ())
            except BaseException as error:
                first_error = error
        for resource in reversed(self._resources):
            try:
                release(resource)
            except BaseException as error:
                if first_error is None:
                    first_error = error
        self._resources.clear()
        if first_error is not None:
            raise first_error



def validate_capture_request(rectangle, size):
    """Validate physical coordinates and bounded output without touching APIs."""
    try:
        left, top, width, height = (rectangle[key] for key in ("left", "top", "width", "height"))
        target_width, target_height = size
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Capture requires a rectangle and two output dimensions") from error
    values = left, top, width, height, target_width, target_height
    if any(type(value) is not int for value in values):
        raise ValueError("Capture coordinates and dimensions must be integers")
    if not -(1 << 30) <= left < (1 << 30) or not -(1 << 30) <= top < (1 << 30):
        raise ValueError("Capture coordinates exceed the supported range")
    if not 1 <= width <= 16384 or not 1 <= height <= 16384:
        raise ValueError("Invalid source dimensions")
    if not 1 <= target_width <= min(width, 3840) or not 1 <= target_height <= min(height, 3840):
        raise ValueError("GPU capture supports bounded downsizing only")
    return (left, top, width, height), (target_width, target_height)


def rect_contained(region, output_rect):
    """region is left/top/width/height; output_rect is physical left/top/right/bottom."""
    left, top, width, height = region
    return (output_rect[0] <= left and output_rect[1] <= top
            and left + width <= output_rect[2] and top + height <= output_rect[3])


class WindowsGpuCapture:
    """One explicitly selected single-output DXGI session, lazily initialized.

    expected_monitors optionally contains the cached MSS list (aggregate at 0).
    expected_output optionally has device_name, hmonitor, rect (LTRB), rotation
    (degrees), panel_identity. All provided fields are checked; none select a
    default display. Initial selection must be contained in exactly one active
    DXGI output cross-checked against GetMonitorInfoW under physical DPI context.

    grab(rectangle, size, force_latest=False) returns owned BGRX bytes, or None
    when DXGI has no new frame. force_latest permits an owned cached frame only
    for that identical rectangle/size after current metadata checks. Changing
    selection to a different output requires close() and a new instance.
    """
    def __init__(self, expected_monitors=None, expected_output=None):
        self._thread = threading.get_ident()
        self._owned = []
        self._dlls = []
        self._old_dpi = None
        self._user = None
        self._layout = None
        self._initial = None
        self._expected_monitors = (tuple(dict(item) for item in expected_monitors)
                                   if expected_monitors is not None else None)
        self._expected_output = dict(expected_output or {})
        allowed = {"device_name", "hmonitor", "rect", "rotation", "panel_identity"}
        if set(self._expected_output) - allowed:
            raise ValueError("Unknown expected output identity field")
        self.scaler = None
        self._configuration = None
        self._last_frame = None
        self.protected_content_masked = False
        self._fatal = False
        self.closed = False
        self.adapter = self.output = self.device = self.context = self.duplicator = PTR()

    def _assert_thread(self):
        if threading.get_ident() != self._thread:
            raise OSError("Windows GPU resources must remain on their capture thread")
        if self.closed or self._fatal:
            raise OSError("Windows GPU capture is closed; create a new session")

    def _configure_user(self):
        class MonitorInfo(ct.Structure):
            _fields_ = [("cbSize", UINT), ("rcMonitor", wt.RECT),
                        ("rcWork", wt.RECT), ("dwFlags", UINT),
                        ("szDevice", wt.WCHAR * 32)]
        class DisplayDevice(ct.Structure):
            _fields_ = [("cb", UINT), ("DeviceName", wt.WCHAR * 32),
                        ("DeviceString", wt.WCHAR * 128), ("StateFlags", UINT),
                        ("DeviceID", wt.WCHAR * 128), ("DeviceKey", wt.WCHAR * 128)]
        self._MonitorInfo, self._DisplayDevice = MonitorInfo, DisplayDevice
        self._monitor_callback = getattr(ct, "WINFUNCTYPE", ct.CFUNCTYPE)(
            INT, PTR, PTR, ct.POINTER(wt.RECT), ct.c_ssize_t)
        user = self._user
        user.SetThreadDpiAwarenessContext.argtypes = [PTR]
        user.SetThreadDpiAwarenessContext.restype = PTR
        user.GetMonitorInfoW.argtypes = [PTR, PTR]
        user.GetMonitorInfoW.restype = INT
        user.EnumDisplayMonitors.argtypes = [PTR, PTR, self._monitor_callback, ct.c_ssize_t]
        user.EnumDisplayMonitors.restype = INT
        user.EnumDisplayDevicesW.argtypes = [wt.LPCWSTR, UINT, PTR, UINT]
        user.EnumDisplayDevicesW.restype = INT

    def _keep(self, ptr):
        if ptr.value:
            self._owned.append(ptr)
        return ptr

    def _output_result(self, ptr, hr, name, *, unsupported=False):
        # Even a failing API's nonnull out pointer is owned and cleaned up.
        self._keep(ptr)
        if hr < 0 and unsupported and hr & 0xffffffff in (
                0x80004001, 0x80004002, 0x887a0004, 0x887a0022):
            raise UnsupportedGpuCapture(f"{name} unavailable (0x{hr & 0xffffffff:08x})")
        check(hr, name)
        if not ptr.value:
            raise OSError(f"{name} returned no COM interface")
        return ptr

    def _query(self, source, iid_text):
        iid = Guid.from_text(iid_text)
        result = PTR()
        hr = invoke(source, 0, HRESULT, [PTR, ct.POINTER(PTR)], ct.byref(iid), ct.byref(result))
        return self._output_result(result, hr, "QueryInterface Output1", unsupported=True)

    @staticmethod
    def _output_desc(output):
        desc = OutputDesc()
        check(invoke(output, 7, HRESULT, [PTR], ct.byref(desc)), "Output.GetDesc")
        return desc

    def _display_identity(self, desc):
        monitor = self._DisplayDevice()
        monitor.cb = ct.sizeof(monitor)
        if not self._user.EnumDisplayDevicesW(desc.DeviceName, 0, ct.byref(monitor), 0):
            raise OSError("Cannot verify attached display identity; capture stopped")
        return monitor.DeviceID

    @staticmethod
    def _signature(desc, identity):
        r = desc.DesktopCoordinates
        if (not desc.DeviceName or not desc.Monitor or not desc.AttachedToDesktop
                or not identity or r.right <= r.left or r.bottom <= r.top):
            raise CaptureLayoutChanged("DXGI source metadata is incomplete; capture stopped")
        if int(desc.Rotation) not in (1, 2, 3, 4):
            raise UnsupportedGpuCapture("DXGI display rotation is unsupported")
        return (desc.DeviceName, int(desc.Monitor or 0),
                (r.left, r.top, r.right, r.bottom), (0, 0, 90, 180, 270)[desc.Rotation],
                bool(desc.AttachedToDesktop), identity)

    def _monitor_layout(self):
        values, errors = [], []
        @self._monitor_callback
        def collect(handle, dc, rect, parameter):
            info = self._MonitorInfo()
            info.cbSize = ct.sizeof(info)
            if not self._user.GetMonitorInfoW(handle, ct.byref(info)):
                errors.append(True)
                return 0
            r = info.rcMonitor
            values.append((info.szDevice, int(handle or 0),
                           (r.left, r.top, r.right, r.bottom), int(info.dwFlags)))
            return 1
        if not self._user.EnumDisplayMonitors(None, None, collect, 0) or errors or not values:
            raise OSError("Cannot verify Windows display layout; capture stopped")
        return tuple(sorted(values))

    def _validate_expected(self, layout, output_signature=None):
        if self._expected_monitors is not None:
            try:
                expected = sorted((item["left"], item["top"], item["left"] + item["width"],
                                   item["top"] + item["height"]) for item in self._expected_monitors[1:])
            except (KeyError, TypeError) as error:
                raise ValueError("Invalid expected cached display layout") from error
            if sorted(item[2] for item in layout) != expected:
                raise CaptureLayoutChanged("Display layout differs from cached selection; restart streaming")
        if output_signature is not None:
            fields = dict(zip(("device_name", "hmonitor", "rect", "rotation", "attached", "panel_identity"),
                              output_signature))
            for name, expected in self._expected_output.items():
                actual = fields[name]
                if name in ("device_name", "panel_identity"):
                    matches = isinstance(expected, str) and actual.casefold() == expected.casefold()
                elif name == "rect":
                    matches = actual == tuple(expected)
                else:
                    matches = actual == expected
                if not matches:
                    raise CaptureLayoutChanged(f"Selected output {name} identity changed; restart streaming")

    def _initialize(self, region):
        try:
            self._user = system_library("user32.dll")
            self._configure_user()
        except (AttributeError, OSError) as error:
            raise UnsupportedGpuCapture("Required Windows physical DPI APIs are unavailable") from error
        self._old_dpi = self._user.SetThreadDpiAwarenessContext(PTR(-4))
        if not self._old_dpi:
            raise OSError("Cannot verify physical display coordinates; capture stopped")
        self._layout = self._monitor_layout()
        self._validate_expected(self._layout)
        try:
            dxgi, d3d = system_library("dxgi.dll"), system_library("d3d11.dll")
        except OSError as error:
            raise UnsupportedGpuCapture("DXGI/D3D11 system APIs are unavailable") from error
        self._dlls = [dxgi, d3d]
        create_factory = dxgi.CreateDXGIFactory1
        create_factory.argtypes = [ct.POINTER(Guid), ct.POINTER(PTR)]
        create_factory.restype = HRESULT
        factory = PTR()
        iid = Guid.from_text("770aae78-f26f-4dba-a829-253c83d1b387")
        self._output_result(factory, create_factory(ct.byref(iid), ct.byref(factory)),
                            "CreateDXGIFactory1", unsupported=True)
        candidates, intersecting = [], []
        for adapter_index in range(32):
            adapter = PTR()
            hr = invoke(factory, 12, HRESULT, [UINT, ct.POINTER(PTR)], adapter_index, ct.byref(adapter))
            if hr & 0xffffffff == 0x887a0002:
                self._keep(adapter)
                break
            self._output_result(adapter, hr, "EnumAdapters1")
            for output_index in range(32):
                output = PTR()
                hr = invoke(adapter, 7, HRESULT, [UINT, ct.POINTER(PTR)], output_index, ct.byref(output))
                if hr & 0xffffffff == 0x887a0002:
                    self._keep(output)
                    break
                self._output_result(output, hr, "EnumOutputs")
                desc = self._output_desc(output)
                if not desc.AttachedToDesktop:
                    continue
                r = desc.DesktopCoordinates
                rect = r.left, r.top, r.right, r.bottom
                left, top, width, height = region
                if max(left, rect[0]) < min(left + width, rect[2]) and max(top, rect[1]) < min(top + height, rect[3]):
                    intersecting.append(rect)
                if rect_contained(region, rect):
                    signature = self._signature(desc, self._display_identity(desc))
                    if not any(item[0] == signature[0] and item[1] == signature[1] and item[2] == signature[2]
                               for item in self._layout):
                        raise CaptureLayoutChanged("DXGI and physical monitor coordinates disagree; capture stopped")
                    self._validate_expected(self._layout, signature)
                    candidates.append((adapter, output, signature))
            else:
                raise OSError("Output enumeration exceeded the safe limit; capture stopped")
        else:
            raise OSError("Adapter enumeration exceeded the safe limit; capture stopped")
        if len(candidates) > 1:
            raise CaptureLayoutChanged("Selected region has ambiguous DXGI output identity; capture stopped")
        if not candidates:
            if len(intersecting) >= 2:
                raise UnsupportedGpuCapture("The explicit capture region spans multiple outputs")
            raise CaptureLayoutChanged("Selected region has no matching active output; capture stopped")
        self.adapter, base_output, self._initial = candidates[0]
        self.output = self._query(base_output, "00cddea8-939b-4b83-a340-a685226666cc")
        self._guard()
        create_device = d3d.D3D11CreateDevice
        create_device.argtypes = [PTR, UINT, PTR, UINT, PTR, UINT, UINT,
                                  ct.POINTER(PTR), ct.POINTER(UINT), ct.POINTER(PTR)]
        create_device.restype = HRESULT
        self.device, self.context = PTR(), PTR()
        level = UINT()
        levels = (UINT * 3)(0xb000, 0xa100, 0xa000)
        hr = create_device(self.adapter, 0, None, 0x20, levels, len(levels), 7,
                           ct.byref(self.device), ct.byref(level), ct.byref(self.context))
        self._keep(self.device)
        self._keep(self.context)
        if hr < 0 and hr & 0xffffffff in (0x80004001, 0x80004002, 0x887a0004, 0x887a0022):
            raise UnsupportedGpuCapture(f"Selected adapter cannot create D3D11 device (0x{hr & 0xffffffff:08x})")
        check(hr, "D3D11CreateDevice on selected adapter")
        if not self.device.value or not self.context.value or level.value < 0xa000:
            raise UnsupportedGpuCapture("Selected adapter requires D3D feature level 10+")
        self.duplicator = PTR()
        hr = invoke(self.output, 22, HRESULT, [PTR, ct.POINTER(PTR)], self.device, ct.byref(self.duplicator))
        self._keep(self.duplicator)
        if hr & 0xffffffff in (0x887a0004, 0x887a0022):
            raise UnsupportedGpuCapture(f"Desktop duplication is unavailable (0x{hr & 0xffffffff:08x})")
        check(hr, "DuplicateOutput on selected adapter")
        if not self.duplicator.value:
            raise OSError("DuplicateOutput returned no interface")

    def _guard(self):
        self._assert_thread()
        current_layout = self._monitor_layout()
        if current_layout != self._layout:
            raise CaptureLayoutChanged("Windows display layout changed; restart streaming")
        self._validate_expected(current_layout)
        desc = self._output_desc(self.output)
        try:
            signature = self._signature(desc, self._display_identity(desc))
        except UnsupportedGpuCapture as error:
            raise CaptureLayoutChanged("Selected output rotation changed; restart streaming") from error
        if signature != self._initial:
            raise CaptureLayoutChanged("Selected source identity changed; restart streaming")
        self._validate_expected(current_layout, signature)

    def _prepare(self, region, size):
        if self._configuration == (region, size):
            return
        if not rect_contained(region, self._initial[2]):
            raise CaptureLayoutChanged("Capture selection moved to another output; recreate the GPU session")
        rect = self._initial[2]
        logical = rect[2] - rect[0], rect[3] - rect[1]
        local = region[0] - rect[0], region[1] - rect[1], region[2], region[3]
        old = self.scaler
        prepared = None
        new = GpuScaler(self.device, self.context, logical, self._initial[3], size, local)
        try:
            if old is not None and self._last_frame is not None and old.source_texture.value:
                # Both textures are GPU-owned. Re-render the retained full source
                # into the new crop/size before releasing the previous scaler.
                # No already-Released duplication pointer is ever retained.
                prepared = new.render(old.source_texture)
            if old is not None:
                old.close()
        except BaseException:
            new.close()
            raise
        self.scaler = new
        self._last_frame = prepared
        self._configuration = region, size

    def grab(self, rectangle, size, *, force_latest=False):
        self._assert_thread()
        region, target = validate_capture_request(rectangle, size)
        if type(force_latest) is not bool:
            raise ValueError("force_latest must be a boolean")
        resource, texture = PTR(), PTR()
        acquired = False
        failure = None
        try:
            if self._initial is None:
                self._initialize(region)
            self._guard()
            self._prepare(region, target)
            frame = DuplicationFrameInfo()
            hr = invoke(self.duplicator, 8, HRESULT, [UINT, PTR, ct.POINTER(PTR)],
                        0, ct.byref(frame), ct.byref(resource))
            if hr & 0xffffffff == 0x887a0027:
                self._guard()
                return self._last_frame if force_latest else None
            check(hr, "AcquireNextFrame: output access lost or unavailable; no automatic recovery")
            acquired = True
            if not resource.value:
                raise OSError("AcquireNextFrame returned no image resource")
            self._guard()
            # DXGI already blacks out protected regions in this surface. Use
            # only that OS-provided image; this flag is diagnostic, not failure.
            # https://learn.microsoft.com/windows/win32/api/dxgi1_2/ns-dxgi1_2-dxgi_outdupl_frame_info
            iid = Guid.from_text("6f15aaf2-d208-4e89-9ab4-489535d34f9c")
            hr = invoke(resource, 0, HRESULT, [PTR, ct.POINTER(PTR)], ct.byref(iid), ct.byref(texture))
            check(hr, "QueryInterface acquired Texture2D")
            if not texture.value:
                raise OSError("Acquired Texture2D is unavailable")
            pixels = self.scaler.render(texture)
            # A layout change during GPU work invalidates even an otherwise valid
            # completed frame. Never publish it or return the previous cache.
            self._guard()
            self._last_frame = pixels
            self.protected_content_masked = bool(frame.ProtectedContentMaskedOut)
            return pixels
        except BaseException as error:
            failure = error
            raise
        finally:
            release_error = None
            for owned in (texture, resource):
                try:
                    release(owned)
                except BaseException as error:
                    if release_error is None:
                        release_error = error
            if acquired:
                try:
                    check(invoke(self.duplicator, 14, HRESULT, ()), "ReleaseFrame")
                except BaseException as error:
                    if release_error is None:
                        release_error = error
            if failure is not None or release_error is not None:
                self._fatal = True
                try:
                    self.close()
                except BaseException:
                    # Preserve the triggering failure; cleanup still attempts all
                    # owned references and the thread DPI restoration below.
                    pass
            if failure is None and release_error is not None:
                raise release_error

    def close(self):
        if self.closed:
            return
        if threading.get_ident() != self._thread:
            raise OSError("Windows GPU resources must close on their capture thread")
        self.closed = True
        self._last_frame = None
        self.protected_content_masked = False
        self._configuration = None
        first_error = None
        try:
            if self.scaler is not None:
                try:
                    self.scaler.close()
                except BaseException as error:
                    first_error = error
                self.scaler = None
            for owned in reversed(self._owned):
                try:
                    release(owned)
                except BaseException as error:
                    if first_error is None:
                        first_error = error
            self._owned.clear()
        finally:
            if self._old_dpi and self._user is not None:
                self._user.SetThreadDpiAwarenessContext(self._old_dpi)
                self._old_dpi = None
            self._dlls.clear()
        if first_error is not None:
            raise first_error
