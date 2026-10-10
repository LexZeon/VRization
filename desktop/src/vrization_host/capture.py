"""Capture adapters and a bounded latest-frame handoff."""

import asyncio
from dataclasses import dataclass
from io import BytesIO
import os
import threading
import time
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class CaptureConfig:
    monitor: int = 1
    region: tuple[int, int, int, int] | None = None  # left, top, width, height (physical pixels)
    width: int = 640
    quality: int = 45
    fps: int = 60

    def __post_init__(self):
        if type(self.monitor) is not int or self.monitor < 0:
            raise ValueError("invalid monitor")
        if type(self.width) is not int or not 320 <= self.width <= 3840:
            raise ValueError("width must be 320..3840")
        if type(self.quality) is not int or not 30 <= self.quality <= 95:
            raise ValueError("quality must be 30..95")
        if type(self.fps) is not int or not 5 <= self.fps <= 60:
            raise ValueError("fps must be 5..60")
        if self.region is not None:
            if (len(self.region) != 4 or any(type(x) is not int for x in self.region)
                    or self.region[2] < 16 or self.region[3] < 16):
                raise ValueError("region needs left, top, width, height; size at least 16 pixels")


@dataclass(frozen=True)
class Frame:
    jpeg: bytes
    width: int
    height: int
    captured_at: float
    # Optional host-only diagnostics; never added to the protocol-v1 JPEG.
    capture_ms: float | None = None
    ready_at: float | None = None  # perf_counter(), shared only within the host
    protected_content_masked: bool = False


def output_size(width: int, height: int, max_edge: int) -> tuple[int, int]:
    """Bound the long edge without upscaling, including portrait monitors."""
    if max(width, height) <= max_edge:
        return width, height
    ratio = max_edge / max(width, height)
    return max(1, round(width * ratio)), max(1, round(height * ratio))


@runtime_checkable
class CaptureSource(Protocol):
    """Implement this adapter to supply frames from a game engine or another app.

    read() and close() are called on the same dedicated capture thread.
    """
    def read(self, config: CaptureConfig) -> Frame | None: ...
    def close(self) -> None: ...


def capture_rectangle(config: CaptureConfig, monitors: list[dict]) -> dict:
    """Resolve one explicit selection before choosing any capture backend."""
    if config.monitor >= len(monitors):
        raise ValueError("selected monitor is unavailable")
    monitor = {key: monitors[config.monitor][key] for key in ("left", "top", "width", "height")}
    if config.region:
        left, top, width, height = config.region
        desktop = monitors[0]
        if (left < desktop["left"] or top < desktop["top"]
                or left + width > desktop["left"] + desktop["width"]
                or top + height > desktop["top"] + desktop["height"]):
            raise ValueError("capture region falls outside the desktop")
        monitor = {"left": left, "top": top, "width": width, "height": height}
    if monitor["width"] <= 0 or monitor["height"] <= 0:
        raise ValueError("selected monitor is unavailable")
    return monitor


class MssCaptureSource:
    def __init__(self, prefer_native: bool = True, prefer_gpu: bool = True):
        self._screen = None
        self._native = None
        self._layout = None
        self._prefer_native = prefer_native
        self._native_failed = False
        self._prefer_gpu = prefer_gpu
        self._gpu = None
        self._gpu_failed = False
        self._gpu_error = None
        self._selection = None
        self._gpu_key = None
        self._gpu_pixels = None
        self._gpu_frame = None
        self._gpu_quality = None
        self._gpu_captured_at = None
        self._gpu_started = False

    def _clear_gpu_cache(self):
        self._gpu_key = self._gpu_pixels = self._gpu_frame = None
        self._gpu_quality = self._gpu_captured_at = None

    def _validate_layout(self):
        if os.name != "nt":
            return
        from .windows_capture import CaptureLayoutChanged
        try:
            self._layout.validate(self._screen.monitors)
        except (OSError, CaptureLayoutChanged) as error:
            self._gpu_error = str(error)
            self._clear_gpu_cache()
            if self._gpu is not None:
                try:
                    self._gpu.close()
                finally:
                    self._gpu = None
            raise

    @staticmethod
    def monitors() -> list[dict]:
        from mss import MSS
        with MSS() as screen:
            return [dict(item) for item in screen.monitors]

    def read(self, config: CaptureConfig) -> Frame | None:
        from mss import MSS
        from PIL import Image
        read_started = time.perf_counter()
        if self._screen is None:
            self._screen = MSS()
        if os.name == "nt":
            if self._gpu_error is not None:
                raise OSError(self._gpu_error)
            if self._layout is None:
                from .windows_capture import WindowsDisplayLayout
                self._layout = WindowsDisplayLayout()
            # MSS caches monitor coordinates. Fail before either backend reads
            # pixels if a display moves/disconnects or another device replaces it.
            self._validate_layout()
        monitor = capture_rectangle(config, self._screen.monitors)
        dimensions = output_size(monitor["width"], monitor["height"], config.width)
        selection = config.monitor, config.region
        if selection != self._selection:
            if self._gpu is not None:
                self._gpu.close()
                self._gpu = None
            self._clear_gpu_cache()
            self._gpu_failed = False
            self._gpu_started = False
            self._selection = selection
        if self._prefer_gpu and os.name == "nt" and not self._gpu_failed:
            from .windows_gpu import UnsupportedGpuCapture, WindowsGpuCapture
            try:
                if self._gpu is None:
                    self._gpu = WindowsGpuCapture(expected_monitors=self._screen.monitors)
                key = tuple(monitor[name] for name in ("left", "top", "width", "height")), dimensions
                pixels = self._gpu.grab(monitor, dimensions, force_latest=key != self._gpu_key)
                self._gpu_started = True
                if pixels is not None:
                    self._gpu_pixels = pixels
                    self._gpu_captured_at = time.monotonic()
                    self._gpu_key = key
                elif self._gpu_pixels is None:
                    # No first desktop update yet. Wait without reading another
                    # screen or starting an expensive CPU capture.
                    return None
                if pixels is not None or self._gpu_quality != config.quality:
                    image = Image.frombytes("RGB", dimensions, self._gpu_pixels, "raw", "BGRX")
                    output = BytesIO()
                    image.save(output, "JPEG", quality=config.quality, optimize=False)
                    ready = time.perf_counter()
                    self._gpu_frame = Frame(output.getvalue(), image.width, image.height, self._gpu_captured_at,
                                            (ready - read_started) * 1000, ready,
                                            protected_content_masked=self._gpu.protected_content_masked)
                    self._gpu_quality = config.quality
                # A static desktop can reuse the owned JPEG. Its original
                # timestamp distinguishes refresh packets from new captures.
                self._validate_layout()
                return self._gpu_frame
            except UnsupportedGpuCapture as error:
                # Never treat a later failure as initial unsupported hardware.
                if self._gpu_started:
                    self._gpu_error = str(error)
                if self._gpu is not None:
                    try:
                        self._gpu.close()
                    finally:
                        self._gpu = None
                self._clear_gpu_cache()
                if self._gpu_started:
                    raise
                self._gpu_failed = True
            except Exception as error:
                self._gpu_error = str(error)
                self._clear_gpu_cache()
                if self._gpu is not None:
                    try:
                        self._gpu.close()
                    finally:
                        self._gpu = None
                # Access loss, identity/layout changes and resource failures
                # stop this session. Only initial unsupported APIs may fall back.
                raise
        image = None
        if self._prefer_native and os.name == "nt" and not self._native_failed:
            try:
                if self._native is None:
                    from .windows_capture import WindowsGdiCapture
                    self._native = WindowsGdiCapture()
                pixels = self._native.grab(monitor, dimensions)
                image = Image.frombytes("RGB", dimensions, pixels, "raw", "BGRX")
            except (OSError, AttributeError):
                # Unsupported display/session/API: keep MSS available, using
                # precisely the same already-validated rectangle, never monitor 1.
                if self._native is not None:
                    self._native.close()
                    self._native = None
                self._native_failed = True
        if image is None:
            shot = self._screen.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            if dimensions != image.size:
                image = image.resize(dimensions, Image.Resampling.BILINEAR)
        output = BytesIO()
        image.save(output, "JPEG", quality=config.quality, optimize=False)
        # GDI/MSS can race a hotplug/move too. Reject the completed frame before
        # publication if its validated selection changed during pixel work.
        self._validate_layout()
        ready = time.perf_counter()
        return Frame(output.getvalue(), image.width, image.height, time.monotonic(),
                     (ready - read_started) * 1000, ready)

    def close(self):
        error = None
        for name in ("_gpu", "_native", "_screen"):
            resource = getattr(self, name)
            if resource is not None:
                try:
                    resource.close()
                except Exception as failure:
                    if error is None:
                        error = failure
                finally:
                    setattr(self, name, None)
        self._gpu_failed = False
        self._gpu_started = False
        self._gpu_error = None
        self._selection = None
        self._clear_gpu_cache()
        self._native_failed = False
        self._layout = None
        if error is not None:
            raise error


class LatestFrameBuffer:
    """The network loop holds exactly one pending frame, dropping older frames."""

    def __init__(self):
        self.sequence = 0
        self.frame: Frame | None = None
        self._changed = asyncio.Event()

    def publish(self, frame: Frame):
        self.frame = frame
        self.sequence += 1
        self._changed.set()

    async def next(self, after: int) -> tuple[int, Frame]:
        while self.sequence <= after or self.frame is None:
            self._changed.clear()
            await self._changed.wait()
        return self.sequence, self.frame


class CaptureWorker:
    def __init__(self, source, get_config, loop, buffer, on_error):
        self.source, self.get_config = source, get_config
        self.loop, self.buffer, self.on_error = loop, buffer, on_error
        self.active = threading.Event()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True, name="vr-capture")
        self._handoff_lock = threading.Lock()
        self._pending: Frame | None = None
        self._scheduled = False

    def start(self):
        self.thread.start()

    def _publish(self):
        with self._handoff_lock:
            frame, self._pending = self._pending, None
            self._scheduled = False
        if frame is not None:
            self.buffer.publish(frame)

    def _run(self):
        next_frame_at, previous_fps = None, None
        try:
            while not self.stop_event.is_set():
                if not self.active.wait(0.1):
                    next_frame_at = None
                    continue
                if self.stop_event.is_set():
                    break
                started = time.perf_counter()
                config = self.get_config()
                if next_frame_at is None or config.fps != previous_fps:
                    next_frame_at = started
                previous_fps = config.fps
                try:
                    frame = self.source.read(config)
                    # At most one callback in the event-loop queue, even if it stalls.
                    if frame is not None:
                        with self._handoff_lock:
                            self._pending = frame
                            if not self._scheduled:
                                self._scheduled = True
                                self.loop.call_soon_threadsafe(self._publish)
                except Exception as exc:
                    self.on_error(str(exc))
                    self.stop_event.wait(0.5)
                # CPython 3.12 on Windows uses a coarse GetTickCount64 clock
                # for monotonic(), and Event.wait() rounds small waits to system
                # ticks. QPC + sleep() uses Python's high-resolution waitable
                # timer without changing the global Windows timer resolution.
                # Keep an absolute cadence so ordinary wake-up lateness does
                # not accumulate; a slow capture resets it, with no catch-up.
                now = time.perf_counter()
                next_frame_at = max(next_frame_at + 1 / config.fps, now)
                delay = next_frame_at - now
                if delay > 0 and not self.stop_event.is_set():
                    # At most one frame interval (200ms at the minimum 5 FPS).
                    # The loop checks stop immediately after this bounded wait.
                    time.sleep(delay)
        finally:
            self.source.close()

    def stop(self):
        self.stop_event.set()
        self.active.set()
        self.thread.join(timeout=3)
