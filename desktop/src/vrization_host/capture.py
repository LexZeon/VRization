"""Capture adapters and a bounded latest-frame handoff."""

import asyncio
from dataclasses import dataclass
from io import BytesIO
import threading
import time
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class CaptureConfig:
    monitor: int = 1
    region: tuple[int, int, int, int] | None = None  # left, top, width, height (physical pixels)
    width: int = 1280
    quality: int = 75
    fps: int = 30

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
    def read(self, config: CaptureConfig) -> Frame: ...
    def close(self) -> None: ...


class MssCaptureSource:
    def __init__(self):
        self._screen = None

    @staticmethod
    def monitors() -> list[dict]:
        from mss import MSS
        with MSS() as screen:
            return [dict(item) for item in screen.monitors]

    def read(self, config: CaptureConfig) -> Frame:
        from mss import MSS
        from PIL import Image
        if self._screen is None:
            self._screen = MSS()
        if config.monitor >= len(self._screen.monitors):
            raise ValueError("selected monitor is unavailable")
        monitor = dict(self._screen.monitors[config.monitor])
        if config.region:
            left, top, width, height = config.region
            desktop = self._screen.monitors[0]
            if (left < desktop["left"] or top < desktop["top"]
                    or left + width > desktop["left"] + desktop["width"]
                    or top + height > desktop["top"] + desktop["height"]):
                raise ValueError("capture region falls outside the desktop")
            monitor = {"left": left, "top": top, "width": width, "height": height}
        shot = self._screen.grab(monitor)
        image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        dimensions = output_size(image.width, image.height, config.width)
        if dimensions != image.size:
            image = image.resize(dimensions, Image.Resampling.BILINEAR)
        output = BytesIO()
        image.save(output, "JPEG", quality=config.quality, optimize=False)
        return Frame(output.getvalue(), image.width, image.height, time.monotonic())

    def close(self):
        if self._screen is not None:
            self._screen.close()
            self._screen = None


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
