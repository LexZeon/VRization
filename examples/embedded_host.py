"""A transport integration example with an original animated calibration card.

Run after installing the desktop package:
    python examples/embedded_host.py
No screen capture or OS input is used by this example.
"""
from __future__ import annotations

from io import BytesIO
import time
from PIL import Image, ImageDraw, ImageFont
from vrization_host import HostServer
from vrization_host.capture import CaptureConfig, Frame


class CalibrationCard:
    """Replace read() with your engine's JPEG-encoded render target."""
    def read(self, config: CaptureConfig) -> Frame:
        width = min(config.width, 1280)
        height = round(width * 9 / 16)
        image = Image.new("RGB", (width, height), "#0d1629")
        draw = ImageDraw.Draw(image)
        for x in range(0, width, 40):
            draw.line((x, 0, x, height), fill="#203149")
        for y in range(0, height, 40):
            draw.line((0, y, width, y), fill="#203149")
        try:
            font = ImageFont.truetype("arial.ttf", width // 16)
            small = ImageFont.truetype("arial.ttf", width // 32)
        except OSError:
            font = ImageFont.load_default(size=width // 16)
            small = ImageFont.load_default(size=width // 32)
        draw.rounded_rectangle((width*.08, height*.15, width*.92, height*.83),
                               radius=24, fill="#13263a", outline="#49d4b9", width=3)
        draw.text((width*.15, height*.26), "VRization", font=font, fill="#49d4b9")
        draw.text((width*.15, height*.47), "LIVE CALIBRATION STREAM", font=small, fill="white")
        draw.text((width*.15, height*.60), time.strftime("%H:%M:%S"), font=small, fill="#b5c9df")
        x = width * (.18 + .62 * ((time.monotonic() % 5) / 5))
        draw.ellipse((x-12, height*.75-12, x+12, height*.75+12), fill="#ffbe5c")
        output = BytesIO()
        image.save(output, "JPEG", quality=config.quality)
        return Frame(output.getvalue(), width, height, time.monotonic())

    def close(self) -> None:
        pass


class GameCameraSink:
    """An engine integration consumes these deltas instead of moving the OS mouse."""
    def move(self, dx: int, dy: int) -> None:
        print(f"Engine camera delta: {dx}, {dy}", flush=True)


if __name__ == "__main__":
    host = HostServer(capture_source=CalibrationCard(), input_sink=GameCameraSink(),
                      on_event=lambda event: print(event, flush=True))
    host.start()
    print(f"Host: 8765; pairing code: {host.token}", flush=True)
    print("The example does not arm input automatically. Ctrl+C stops the host.", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        host.stop()
