"""Isolated synthetic SBS iOS fixture: real preview protocol, no driver or OS mouse.

Only capture pixels, pose destination and usbmux enumeration are synthetic.
The original preview host, settings/capability gate, USB relay and phone decoder
remain in use. No SteamVR driver registration or physical device claim is made.
"""
from contextlib import suppress
import argparse
from http.server import BaseHTTPRequestHandler
from io import BytesIO
import json
from pathlib import Path
import plistlib
import re
import signal
import socket
import struct
import sys
import threading
import time

from PIL import Image, ImageDraw
from ios_usb_fixture import Handler, Server, NoAndroid, LoopbackObservationServer, receive_exact

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experimental/steamvr/python"))
sys.path.insert(0, str(ROOT / "desktop/src"))
from vrization_steamvr.host import PreviewHost
from vrization_host.capture import CaptureConfig, Frame
from vrization_host.protocol import Settings
from vrization_host.usb import AppleMux, UsbManager


class StereoCard:
    """A 1280x480 packed card with distinguishable 640x480 eye images.

    These original solid RGB quadrants provide exportable native pixel oracles:
    left red/green, right blue/yellow. Thin white borders expose accidental warp
    or full-packed-aspect fit. No user image, display capture or SteamVR required.
    """
    def __init__(self):
        image = Image.new("RGB", (1280, 480))
        draw = ImageDraw.Draw(image)
        for eye, top, bottom in ((0, (196, 35, 53), (34, 155, 74)),
                                 (1, (31, 83, 196), (214, 170, 34))):
            x = eye * 640
            draw.rectangle((x, 0, x + 639, 239), fill=top)
            draw.rectangle((x, 240, x + 639, 479), fill=bottom)
            draw.rectangle((x + 12, 12, x + 627, 467), outline=(235, 235, 235), width=3)
            draw.line((x + 320, 15, x + 320, 465), fill=(240, 240, 240), width=3)
        buffer = BytesIO(); image.save(buffer, "JPEG", quality=95, subsampling=0)
        self.jpeg = buffer.getvalue()
    def read(self, _config):
        return Frame(self.jpeg, 1280, 480, time.time())
    def close(self):
        pass


class RecordingPoseSink:
    def __init__(self):
        self.records = []
        self.lock = threading.Lock()
    def publish(self, q, seq, connected, paused):
        record = {"q": None if q is None else list(q), "seq": seq,
                  "connected": connected, "paused": paused}
        with self.lock:
            self.records.append(record)
            self.records[:] = self.records[-512:]
    def snapshot(self):
        with self.lock:
            return list(self.records)


class NoMouse:
    def __init__(self):
        self.moves = []
    def move(self, dx, dy):
        self.moves.append([dx, dy])
        raise AssertionError("Synthetic virtual-HMD route must never call a mouse sink")


class PreviewMuxHandler(Handler):
    """Same fake usbmux protocol, solely on the preview's isolated device ports."""
    def handle(self):
        stream = self.request; stream.settimeout(3)
        try:
            length, version, kind, tag = struct.unpack("<IIII", receive_exact(stream, 16))
            if not 16 <= length <= 65536 or version != 1 or kind != 8:
                return
            request = plistlib.loads(receive_exact(stream, length - 16))
            message = request.get("MessageType")
            if message == "ListDevices":
                self.reply({"DeviceList": [{"DeviceID": 1, "Properties": {
                    "ConnectionType": "USB", "SerialNumber": "VRization-SteamVR-Simulated-USB"}}]}, tag)
            elif message == "ReadPairRecord":
                self.reply({"PairRecordData": plistlib.dumps({"HostID": "VRization-SteamVR-Fixture",
                                                            "SystemBUID": "VRization-SteamVR-Fixture"})}, tag)
            elif message == "Connect":
                port = socket.ntohs(request.get("PortNumber", 0))
                if request.get("DeviceID") != 1 or port not in (18776, 18777):
                    self.reply({"Number": 3}, tag); return
                try:
                    phone = socket.create_connection(("127.0.0.1", port), timeout=1)
                except OSError:
                    self.reply({"Number": 3}, tag); return
                self.reply({"Number": 0}, tag)
                stream.settimeout(None); phone.settimeout(None)
                with phone:
                    done = threading.Event()
                    def pump(source, target):
                        try:
                            while not done.is_set():
                                data = source.recv(32768)
                                if not data: break
                                target.sendall(data)
                        except OSError:
                            pass
                        finally:
                            done.set()
                            for endpoint in (source, target):
                                with suppress(OSError): endpoint.shutdown(socket.SHUT_RDWR)
                    worker = threading.Thread(target=pump, args=(stream, phone), daemon=True)
                    worker.start(); pump(phone, stream); worker.join(timeout=2)
        except (OSError, ValueError, plistlib.InvalidFileException):
            return


class PreviewMux:
    def __init__(self):
        self.server = Server(("127.0.0.1", 0), PreviewMuxHandler)
        self.address = self.server.server_address
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    def start(self): self.thread.start()
    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18785)
    parser.add_argument("--control-port", type=int, default=18789)
    args = parser.parse_args()
    stop, ready = threading.Event(), threading.Event()
    guard = threading.Lock(); events, checkpoints = [], []
    sink, poses = NoMouse(), RecordingPoseSink()
    def on_event(event):
        if event.get("event") in {"connection", "settings", "input", "error", "stream-session"}:
            with guard: events.append(event)
    host = PreviewHost(route="steamvr-phone", capture_source=StereoCard(), pose_sink=poses,
                       input_sink=sink, settings=Settings(mode="fps_enhanced"),
                       host="127.0.0.1", port=args.port,
                       capture_config=CaptureConfig(width=1280, fps=12), on_event=on_event)
    def snapshot():
        with guard: count = sum(event.get("event") == "settings" for event in events)
        return {"fixtureReady": ready.is_set(), "connected": host.controller.connected,
                "settingsCount": count, "settings": host.get_settings_snapshot()[0].to_dict(),
                "mouseMoves": list(sink.moves), "poses": poses.snapshot()}
    class ObservationHandler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def respond(self, payload, status=200):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            if self.path == "/snapshot": self.respond(snapshot())
            else: self.respond({"error": "unknown observation"}, 404)
        def do_POST(self):
            if self.path == "/checkpoint":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 1024: raise ValueError
                    name = json.loads(self.rfile.read(length))["name"]
                    if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name): raise ValueError
                except (ValueError, KeyError, TypeError):
                    self.respond({"error": "invalid checkpoint"}, 400); return
                record = {"name": name, **snapshot()}
                with guard: checkpoints.append(record)
                self.respond(record)
            else: self.respond({"error": "unknown action"}, 404)
    control = usb = mux = None
    for number in (signal.SIGINT, signal.SIGTERM): signal.signal(number, lambda *_: stop.set())
    try:
        host.start(); host.token = "123456"
        control = LoopbackObservationServer(("127.0.0.1", args.control_port), ObservationHandler)
        threading.Thread(target=control.serve_forever, daemon=True).start()
        mux = PreviewMux(); mux.start()
        usb = UsbManager(host, adb=NoAndroid(), mux=AppleMux(address=mux.address), on_event=on_event,
                         ios_video_port=18776, ios_control_port=18777)
        usb.start(); ready.set(); print("Synthetic SteamVR SBS fixture ready; no native driver.", flush=True)
        stop.wait()
    finally:
        ready.clear()
        if control: control.shutdown(); control.server_close()
        if usb: usb.stop()
        if mux: mux.stop()
        host.stop()
        with guard:
            report = {"events": events, "checkpoints": checkpoints, "mouseMoves": sink.moves,
                      "poses": poses.snapshot(), "usbService": "simulated", "nativeDriverRegistered": False,
                      "physicalPhoneTested": False}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__": main()
