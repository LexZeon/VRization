"""Loopback-only iOS UI-test fixture. Never captures a display or arms input."""
from __future__ import annotations

import faulthandler
if __name__ == "__main__":
    # Diagnose imports as well as service startup, before loading app libraries.
    faulthandler.enable()
    faulthandler.dump_traceback_later(30, repeat=True)
    print("Synthetic iOS fixture: loading modules.", flush=True)

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import signal
import re
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
    parser.add_argument("--control-port", type=int, default=18769)
    args = parser.parse_args()
    events = []
    guard = threading.Lock()
    stop = threading.Event()
    ready = threading.Event()
    sink = NoMouse()
    usb = mux_fixture = None
    control = None
    checkpoints = []

    def on_event(event):
        # Only synthetic fixture state; never record pairing URLs / credentials.
        if event.get("event") in {"connection", "settings", "input", "error"}:
            with guard:
                events.append(event)

    host = HostServer(capture_source=CalibrationCard(), input_sink=sink,
                      capture_config=CaptureConfig(width=1280, fps=12),
                      host="127.0.0.1", port=args.port, on_event=on_event)

    def snapshot():
        with guard:
            count = sum(event["event"] == "settings" for event in events)
        return {"settingsCount": count, "settings": host.get_settings_snapshot()[0].to_dict(), "mouseMoves": list(sink.moves), "connected": host.controller.connected,
                "fixtureReady": ready.is_set()}

    class ObservationHandler(BaseHTTPRequestHandler):
        # Snapshot/checkpoints only observe. Explicit phone-connect uses the real
        # paired control adapter; host-update uses the same public settings path
        # as the desktop GUI. Both operate only on the calibration fixture.
        def log_message(self, *_):
            pass

        def respond(self, payload, status=200):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/snapshot":
                self.respond(snapshot())
            else:
                self.respond({"error": "unknown observation"}, 404)

        def do_POST(self):
            if self.path in ("/pause-relay", "/resume-relay"):
                if usb is None:
                    self.respond({"error": "simulated USB is unavailable"}, 503)
                    return
                usb.set_enabled(self.path == "/resume-relay")
                if self.path == "/pause-relay":
                    usb.relay.stop()
                self.respond(snapshot())
                return
            if self.path in ("/phone-connect", "/phone-stop"):
                if mux_fixture is None:
                    self.respond({"error": "simulated USB is unavailable"}, 503)
                    return
                from vrization_host.ios_usb import request_ios_connect, request_ios_stop
                from vrization_host.usb import AppleDevice, AppleMux
                try:
                    action = request_ios_stop if self.path == "/phone-stop" else request_ios_connect
                    action(AppleMux(address=mux_fixture.address), AppleDevice(1, "VRization-Simulated-USB-Fixture"))
                except (OSError, ValueError):
                    self.respond({"error": "foreground control is unavailable"}, 503)
                    return
                self.respond(snapshot())
                return
            if self.path == "/host-update":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 1024:
                        raise ValueError
                    patch = json.loads(self.rfile.read(length))
                    if not isinstance(patch, dict) or set(patch) not in (
                            {"scale"}, {"stabilization"}, {"mode", "stabilization"}):
                        raise ValueError
                    host.update_settings(patch)
                except (ValueError, KeyError, TypeError):
                    self.respond({"error": "invalid fixture host update"}, 400)
                    return
                self.respond(snapshot())
                return
            if self.path != "/checkpoint":
                self.respond({"error": "unknown observation"}, 404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1024:
                    raise ValueError
                name = json.loads(self.rfile.read(length))["name"]
                if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name):
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                self.respond({"error": "invalid observation name"}, 400)
                return
            record = {"name": name, **snapshot()}
            with guard:
                checkpoints.append(record)
            self.respond(record)
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda *_: stop.set())
    try:
        print("Synthetic iOS fixture: starting video host.", flush=True)
        host.start()
        host.token = "123456"  # Public loopback fixture, after start() rotates the real code.
        print("Synthetic iOS fixture: starting observation service.", flush=True)
        control = ThreadingHTTPServer(("127.0.0.1", args.control_port), ObservationHandler)
        threading.Thread(target=control.serve_forever, daemon=True).start()
        if args.usb_fixture:
            print("Synthetic iOS fixture: starting simulated USB service.", flush=True)
            from ios_usb_fixture import NoAndroid, SimulatedAppleMux
            from vrization_host.usb import AppleMux, UsbManager
            mux_fixture = SimulatedAppleMux()
            mux_fixture.start()
            usb = UsbManager(host, adb=NoAndroid(), mux=AppleMux(address=mux_fixture.address), on_event=on_event)
            usb.start()
        ready.set()
        faulthandler.cancel_dump_traceback_later()
        print("Synthetic iOS fixture ready on loopback.", flush=True)
        stop.wait()
    finally:
        faulthandler.cancel_dump_traceback_later()
        if control:
            control.shutdown(); control.server_close()
        if usb:
            usb.stop()
        if mux_fixture:
            mux_fixture.stop()
        host.stop()
        with guard:
            report = {"events": events, "mouseMoves": sink.moves,
                      "settings": host.get_settings_snapshot()[0].to_dict(),
                      "usbService": "simulated" if args.usb_fixture else "disabled",
                      "checkpoints": checkpoints}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
