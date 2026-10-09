"""Loopback-only iOS UI-test fixture. Never captures a display or arms input."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import signal
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
from embedded_host import CalibrationCard  # noqa: E402
from vrization_host import HostServer  # noqa: E402
from vrization_host.capture import CaptureConfig  # noqa: E402


class NoMouse:
    def __init__(self):
        self.moves = []

    def move(self, dx, dy):
        self.moves.append([dx, dy])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--usb-fixture", action="store_true")
    args = parser.parse_args()
    events = []
    guard = threading.Lock()
    stop = threading.Event()
    sink = NoMouse()
    usb = mux_fixture = None

    def on_event(event):
        # Only synthetic fixture state; never record pairing URLs / credentials.
        if event.get("event") in {"connection", "settings", "input", "error"}:
            with guard:
                events.append(event)

    host = HostServer(capture_source=CalibrationCard(), input_sink=sink,
                      capture_config=CaptureConfig(width=1280, fps=12),
                      host="127.0.0.1", port=args.port, on_event=on_event)
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda *_: stop.set())
    try:
        host.start()
        host.token = "123456"  # Public loopback fixture, after start() rotates the real code.
        if args.usb_fixture:
            from ios_usb_fixture import NoAndroid, SimulatedAppleMux
            from vrization_host.usb import AppleMux, UsbManager
            mux_fixture = SimulatedAppleMux()
            mux_fixture.start()
            usb = UsbManager(host, adb=NoAndroid(), mux=AppleMux(address=mux_fixture.address), on_event=on_event)
            usb.start()
        print("Synthetic iOS fixture ready on loopback.", flush=True)
        stop.wait()
    finally:
        if usb:
            usb.stop()
        if mux_fixture:
            mux_fixture.stop()
        host.stop()
        with guard:
            report = {"events": events, "mouseMoves": sink.moves,
                      "settings": host.get_settings_snapshot()[0].to_dict(),
                      "usbService": "simulated" if args.usb_fixture else "disabled"}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
