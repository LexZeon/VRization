"""Original Windows GDI capture: scale before copying pixels into Python.

System API reference, no copied implementation or additional library:
https://learn.microsoft.com/windows/win32/api/wingdi/nf-wingdi-stretchblt
https://learn.microsoft.com/windows/win32/api/wingdi/nf-wingdi-createdibsection
https://learn.microsoft.com/windows/win32/api/wingdi/nf-wingdi-gdiflush

All resources and reads belong to the same capture thread. Failure raises;
the caller may use MSS for the exact same validated source rectangle.
"""
import ctypes
from ctypes import wintypes


class CaptureLayoutChanged(ValueError):
    """Fail closed rather than capturing another screen at stale coordinates."""


class MonitorInfo(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                ("work", wintypes.RECT), ("flags", wintypes.DWORD),
                ("device", wintypes.WCHAR * 32)]


class WindowsDisplayLayout:
    """Read-only layout guard, also used before the Windows MSS fallback."""
    def __init__(self, loader=None):
        self.user = (loader or ctypes.WinDLL)("user32", use_last_error=True)
        self.callback_type = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)(
            wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
            ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
        self.user.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                                                  self.callback_type, wintypes.LPARAM]
        self.user.EnumDisplayMonitors.restype = wintypes.BOOL
        self.user.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MonitorInfo)]
        self.user.GetMonitorInfoW.restype = wintypes.BOOL
        self._signature = None

    def validate(self, expected_monitors):
        current, failed = [], []

        @self.callback_type
        def visit(handle, dc, rectangle, parameter):
            info = MonitorInfo()
            info.size = ctypes.sizeof(info)
            if not self.user.GetMonitorInfoW(handle, ctypes.byref(info)):
                failed.append(True)
                return False
            r = info.monitor
            current.append((info.device, r.left, r.top, r.right - r.left, r.bottom - r.top))
            return True

        if not self.user.EnumDisplayMonitors(None, None, visit, 0) or failed or not current:
            raise OSError("Cannot verify the Windows display layout; capture paused")
        signature = tuple(sorted(current))
        expected = sorted(tuple(item[key] for key in ("left", "top", "width", "height"))
                          for item in expected_monitors[1:])
        if (sorted(item[1:] for item in current) != expected
                or self._signature is not None and signature != self._signature):
            raise CaptureLayoutChanged("Display layout changed; stop streaming, reselect the display/region and start again")
        self._signature = signature


class BitmapInfoHeader(ctypes.Structure):
    _fields_ = [("size", ctypes.c_uint32), ("width", ctypes.c_int32),
                ("height", ctypes.c_int32), ("planes", ctypes.c_uint16),
                ("bit_count", ctypes.c_uint16), ("compression", ctypes.c_uint32),
                ("image_size", ctypes.c_uint32), ("x_pixels_per_meter", ctypes.c_int32),
                ("y_pixels_per_meter", ctypes.c_int32), ("colors_used", ctypes.c_uint32),
                ("colors_important", ctypes.c_uint32)]


class BitmapInfo(ctypes.Structure):
    _fields_ = [("header", BitmapInfoHeader), ("colors", ctypes.c_uint32 * 1)]


class WindowsGdiCapture:
    """One reusable top-down BGRX DIB, bounded to the requested output size."""

    def __init__(self, loader=None):
        load = loader or ctypes.WinDLL
        self.user = load("user32", use_last_error=True)
        self.gdi = load("gdi32", use_last_error=True)
        signatures = [
            (self.user.GetDC, [wintypes.HWND], wintypes.HDC),
            (self.user.ReleaseDC, [wintypes.HWND, wintypes.HDC], ctypes.c_int),
            (self.gdi.CreateCompatibleDC, [wintypes.HDC], wintypes.HDC),
            (self.gdi.DeleteDC, [wintypes.HDC], wintypes.BOOL),
            (self.gdi.CreateDIBSection, [wintypes.HDC, ctypes.POINTER(BitmapInfo), wintypes.UINT,
                                       ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD], wintypes.HBITMAP),
            (self.gdi.SelectObject, [wintypes.HDC, wintypes.HGDIOBJ], wintypes.HGDIOBJ),
            (self.gdi.DeleteObject, [wintypes.HGDIOBJ], wintypes.BOOL),
            (self.gdi.SetStretchBltMode, [wintypes.HDC, ctypes.c_int], ctypes.c_int),
            (self.gdi.SetBrushOrgEx, [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_void_p], wintypes.BOOL),
            (self.gdi.StretchBlt, [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                  wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                  wintypes.DWORD], wintypes.BOOL),
            (self.gdi.GdiFlush, [], wintypes.BOOL),
        ]
        for function, args, result in signatures:
            function.argtypes, function.restype = args, result
        self._screen = self._memory = self._bitmap = self._previous = None
        self._bits = ctypes.c_void_p()
        self._size = None

    @staticmethod
    def _error(operation):
        code = getattr(ctypes, "get_last_error", lambda: 0)()
        return OSError(f"Windows capture {operation} failed (code {code})")

    def _prepare(self, width, height):
        if self._size == (width, height):
            return
        self.close()
        try:
            self._screen = self.user.GetDC(None)
            if not self._screen:
                raise self._error("GetDC")
            self._memory = self.gdi.CreateCompatibleDC(self._screen)
            if not self._memory:
                raise self._error("CreateCompatibleDC")
            info = BitmapInfo()
            info.header.size = ctypes.sizeof(BitmapInfoHeader)
            info.header.width, info.header.height = width, -height
            info.header.planes, info.header.bit_count = 1, 32
            self._bitmap = self.gdi.CreateDIBSection(self._screen, ctypes.byref(info), 0,
                                                   ctypes.byref(self._bits), None, 0)
            if not self._bitmap or not self._bits.value:
                raise self._error("CreateDIBSection")
            self._previous = self.gdi.SelectObject(self._memory, self._bitmap)
            if not self._previous or self._previous == ctypes.c_void_p(-1).value:
                self._previous = None
                raise self._error("SelectObject")
            # HALFTONE averages source pixels rather than discarding fine text.
            # Microsoft requires resetting the brush origin after this mode.
            if not self.gdi.SetStretchBltMode(self._memory, 4):
                raise self._error("SetStretchBltMode")
            if not self.gdi.SetBrushOrgEx(self._memory, 0, 0, None):
                raise self._error("SetBrushOrgEx")
            self._size = (width, height)
        except BaseException:
            self.close()
            raise

    def grab(self, rectangle, size):
        """Return copied BGRX bytes; source coordinates are never changed on error."""
        left, top = rectangle["left"], rectangle["top"]
        source_width, source_height = rectangle["width"], rectangle["height"]
        width, height = size
        if (any(type(value) is not int for value in (left, top, source_width, source_height, width, height))
                or not 1 <= width <= source_width or not 1 <= height <= source_height
                or max(width, height) > 3840):
            raise ValueError("Invalid Windows capture rectangle or output size")
        self._prepare(width, height)
        # The memory DC is compatible with this same desktop DC, including
        # negative virtual-desktop coordinates. CAPTUREBLT includes layered UI.
        if not self.gdi.StretchBlt(self._memory, 0, 0, width, height, self._screen,
                                   left, top, source_width, source_height, 0x40CC0020):
            raise self._error("StretchBlt")
        # Complete GDI writes before reading the DIB pointer; never return stale
        # pixels after a failed operation. The returned bytes own their memory.
        if not self.gdi.GdiFlush():
            raise self._error("GdiFlush")
        return ctypes.string_at(self._bits.value, width * height * 4)

    def close(self):
        # Deselect before deleting; destroying the memory DC also releases a
        # selection if restoration fails. ReleaseDC pairs only with GetDC.
        if self._memory:
            if self._previous:
                self.gdi.SelectObject(self._memory, self._previous)
            self.gdi.DeleteDC(self._memory)
        if self._bitmap:
            self.gdi.DeleteObject(self._bitmap)
        if self._screen:
            self.user.ReleaseDC(None, self._screen)
        self._screen = self._memory = self._bitmap = self._previous = None
        self._bits = ctypes.c_void_p()
        self._size = None
