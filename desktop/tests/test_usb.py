"""USB protocol and ownership regressions, using no hardware or real mouse input."""
import asyncio
from io import BytesIO
import json
from pathlib import Path
import plistlib
import socket
import struct
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aiohttp import ClientSession
from aiohttp.test_utils import TestServer, make_mocked_request
from PIL import Image

from vrization_host.capture import CaptureConfig
from vrization_host.profiles import PROFILES, CUSTOM, apply_profile, capture_profile, initial_capture
from vrization_host.server import HostServer
from vrization_host.storage import load_usb_preferences, save_usb_preferences
from vrization_host.usb import (AdbReverse, AndroidDevice, AppleDevice, AppleMux, IOSUsbRelay,
                                MAX_FRAME, UsbManager, pack_frame, parse_adb_devices, read_frame)
from vrization_host.usb import WindowsUsbPresence, pnp_usb_serials
from test_native_client_wire import SyntheticJpegSource, RecordingInputSink


class FakeAdbRunner:
    def __init__(self, mappings=()):
        self.mappings = set(mappings)
        self.commands = []

    def __call__(self, command, **kwargs):
        args = command[1:]
        self.commands.append(args)
        if args[-2:] == ["reverse", "--list"]:
            output = "\n".join(f"UsbFfs {remote} {local}" for remote, local in self.mappings)
        elif "--no-rebind" in args:
            remote, local = args[-2:]
            if any(source == remote for source, _ in self.mappings):
                return SimpleNamespace(returncode=1, stdout="", stderr="cannot rebind")
            self.mappings.add((remote, local))
            output = ""
        elif "--remove" in args:
            self.mappings = {pair for pair in self.mappings if pair[0] != args[-1]}
            output = ""
        else:
            raise AssertionError(args)
        return SimpleNamespace(returncode=0, stdout=output, stderr="")


class MemorySocket:
    def __init__(self, response):
        payload = plistlib.dumps(response)
        self.response = struct.pack("<IIII", 16 + len(payload), 1, 8, 1) + payload
        self.sent = b""
        self.closed = False

    def sendall(self, data):
        self.sent += data

    def recv(self, size):
        result, self.response = self.response[:min(size, 3)], self.response[min(size, 3):]
        return result

    def setblocking(self, value):
        self.blocking = value

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class UsbOwnershipTests(unittest.TestCase):
    def test_adb_ignores_emulator_ip_and_mdns_transports(self):
        text = ("List of devices attached\nUSB123 device usb:1-4 model:HUAWEI\n"
                "emulator-5554 device\n192.0.2.1:5555 device\n"
                "adb-123._adb-tls-connect._tcp device\nLOCKED unauthorized usb:1-2\n")
        self.assertEqual(parse_adb_devices(text), [AndroidDevice("USB123", "device", True),
                                                  AndroidDevice("LOCKED", "unauthorized", True)])

    def test_preexisting_identical_or_other_mapping_is_never_taken(self):
        for target in ("tcp:8765", "tcp:9999"):
            runner = FakeAdbRunner([("tcp:18765", target)])
            adb = AdbReverse(Path("adb.exe"), runner)
            self.assertFalse(adb.ensure("USB123", 8765))
            adb.release()
            self.assertFalse(any("--no-rebind" in command or "--remove" in command for command in runner.commands))

    def test_owned_mapping_removed_without_touching_other_ports(self):
        runner = FakeAdbRunner([("tcp:1234", "tcp:7777")])
        adb = AdbReverse(Path("adb.exe"), runner)
        self.assertTrue(adb.ensure("USB123", 8765))
        self.assertTrue(adb.ensure("USB123", 8765))
        self.assertEqual(sum("--no-rebind" in command for command in runner.commands), 1)
        adb.release()
        self.assertEqual(runner.mappings, {("tcp:1234", "tcp:7777")})
        self.assertTrue(all(command[:2] == ["-s", "USB123"] for command in runner.commands))

    def test_mapping_replaced_by_another_application_is_not_removed(self):
        runner = FakeAdbRunner()
        adb = AdbReverse(Path("adb.exe"), runner)
        adb.ensure("USB123", 8765)
        runner.mappings = {("tcp:18765", "tcp:9999")}
        adb.release()
        self.assertEqual(runner.mappings, {("tcp:18765", "tcp:9999")})

    def test_usb_preferences_default_enabled_without_pairing_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usb.json"
            value = load_usb_preferences(path)
            self.assertTrue(value["enabled"])
            value.update(enabled=False, adb_path="SDK/adb.exe", preferred_serial="USB123", token="123456")
            save_usb_preferences(value, path)
            self.assertNotIn("token", path.read_text())
            self.assertFalse(load_usb_preferences(path)["enabled"])

    def test_profiles_preserve_existing_custom_and_region(self):
        old = CaptureConfig(monitor=2, region=(-500, 0, 400, 600), width=1600, quality=85, fps=45)
        self.assertEqual(initial_capture(old, True), old)
        self.assertEqual(capture_profile(old), CUSTOM)
        first = initial_capture(old, False)
        self.assertEqual((first.width, first.fps, first.quality), (960, 60, 60))
        self.assertEqual((first.monitor, first.region), (old.monitor, old.region))
        for name in PROFILES:
            self.assertEqual(capture_profile(apply_profile(old, name)), name)

    def test_mux_filters_network_devices_and_encodes_connect_port(self):
        result = {"DeviceList": [{"DeviceID": 7, "Properties": {"ConnectionType": "USB", "SerialNumber": "IOS7"}},
                                  {"DeviceID": 8, "Properties": {"ConnectionType": "Network"}}]}
        listed, paired, connected = (MemorySocket(result),
                                     MemorySocket({"PairRecordData": plistlib.dumps({"HostID": "TEST"})}),
                                     MemorySocket({"MessageType": "Result", "Number": 0}))
        sockets = iter((listed, paired, connected))
        mux = AppleMux(connector=lambda *args, **kwargs: next(sockets))
        self.assertEqual(mux.devices(), [AppleDevice(7, "IOS7")])
        self.assertIs(mux.connect(AppleDevice(7, "IOS7")), connected)
        request = plistlib.loads(connected.sent[16:])
        self.assertEqual(request["MessageType"], "Connect")
        self.assertEqual(request["PortNumber"], socket.htons(18766))
        self.assertFalse(connected.blocking)
        self.assertEqual(plistlib.loads(paired.sent[16:])["MessageType"], "ReadPairRecord")

    def test_mux_invalid_length_and_connect_failure_close_socket(self):
        sock = MemorySocket({"Number": 2})
        sockets = iter((MemorySocket({"PairRecordData": plistlib.dumps({"HostID": "TEST"})}), sock))
        mux = AppleMux(connector=lambda *args, **kwargs: next(sockets))
        with self.assertRaises(ConnectionError):
            mux.connect(AppleDevice(1, "IOS"))
        self.assertTrue(sock.closed)
        sock = MemorySocket({})
        sock.response = struct.pack("<IIII", 1024 * 1024 + 1, 1, 8, 1)
        with self.assertRaises(ValueError):
            mux.exchange(sock, {"MessageType": "ListDevices"})

    def test_mux_requires_existing_trust_pair_record_without_creating_one(self):
        for result in ({"Number": 2}, {"PairRecordData": b"invalid"},
                       {"PairRecordData": plistlib.dumps({"Other": "value"})}):
            sock = MemorySocket(result)
            mux = AppleMux(connector=lambda *args, **kwargs: sock)
            with self.assertRaises(ConnectionError):
                mux.connect(AppleDevice(1, "IOS"))
            request = plistlib.loads(sock.sent[16:])
            self.assertEqual(request["MessageType"], "ReadPairRecord")
            self.assertTrue(sock.closed)

    def test_manager_requires_unique_device_or_explicit_selection(self):
        class Adb:
            owned = None
            calls = []
            def devices(self):
                return [AndroidDevice("A", "device", True), AndroidDevice("B", "device", True)]
            def ensure(self, serial, port):
                self.calls.append((serial, port))
                return True
            def release(self):
                pass
        adb = Adb()
        host = SimpleNamespace(port=8765, running=False)
        manager = UsbManager(host, adb=adb, mux=SimpleNamespace(devices=lambda: []))
        manager.set_enabled(True)
        manager.scan()
        self.assertFalse(manager.authorized.is_set())
        self.assertEqual(adb.calls, [])
        manager.preferred_serial = "B"
        manager.scan()
        self.assertTrue(manager.authorized.is_set())
        self.assertEqual(adb.calls, [("B", 8765)])
        manager.set_enabled(False)
        manager.scan()
        self.assertFalse(manager.authorized.is_set())

    def test_disabling_during_reverse_creation_cannot_reenable_bootstrap(self):
        class Adb:
            owned = None
            released = False
            def devices(self):
                return [AndroidDevice("A", "device", True)]
            def ensure(self, serial, port):
                manager.set_enabled(False)
                return True
            def release(self):
                self.released = True
        adb = Adb()
        manager = UsbManager(SimpleNamespace(port=8765), adb=adb)
        manager.set_enabled(True)
        manager.scan()
        self.assertFalse(manager.authorized.is_set())
        self.assertTrue(adb.released)

    def test_owned_reverse_host_port_change_is_immediate_and_preserves_other_ports(self):
        runner = FakeAdbRunner([("tcp:1111", "tcp:2222")])
        adb = AdbReverse(Path("adb.exe"), runner)
        self.assertTrue(adb.ensure("USB123", 8765))
        self.assertTrue(adb.ensure("USB123", 9000))
        self.assertEqual(runner.mappings, {("tcp:1111", "tcp:2222"), ("tcp:18765", "tcp:9000")})

    def test_windows_pnp_exact_serial_cache_and_fixed_query(self):
        calls, now = [], [0]
        def runner(command, **kwargs):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout=json.dumps([
                r"USB\VID_12D1&PID_107E\ABC123", r"ROOT\ABC123", r"USB\VID_12D1&PID_107E\ABC123suffix"]))
        presence = WindowsUsbPresence(runner, windows=True, clock=lambda: now[0])
        self.assertTrue(presence("abc123"))
        self.assertFalse(presence("ABC12"))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][-1], WindowsUsbPresence.QUERY)
        self.assertNotIn("ABC123", calls[0][-1])
        now[0] = 11
        self.assertTrue(presence("ABC123"))
        self.assertEqual(len(calls), 2)
        self.assertEqual(pnp_usb_serials([r"USB\BAD\ABC123", r"PCI\VID_12D1&PID_107E\ABC123"]), set())

    def test_windows_unknown_adb_devpath_requires_matching_physical_serial(self):
        def runner(command, **kwargs):
            args = command[1:]
            output = "USB123 device model:Huawei\nUNMATCHED device\n192.0.2.1:5555 device\n" if args == ["devices", "-l"] else "unknown\n"
            return SimpleNamespace(returncode=0, stdout=output, stderr="")
        adb = AdbReverse(Path("adb.exe"), runner, usb_presence=lambda serial: serial == "USB123")
        self.assertEqual(adb.devices(), [AndroidDevice("USB123", "device", True)])


class UsbAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_relay_cancelled_during_connect_closes_late_socket(self):
        entered, complete = threading.Event(), threading.Event()
        sock = MemorySocket({})
        class Mux:
            def connect(self, device):
                entered.set()
                complete.wait(2)
                return sock
        relay = IOSUsbRelay(SimpleNamespace(), Mux())
        relay.start(AppleDevice(1, "FIXTURE"))
        self.assertTrue(await asyncio.to_thread(entered.wait, 2))
        relay.request_stop()
        complete.set()
        await asyncio.to_thread(relay.stop)
        self.assertFalse(relay.active)
        self.assertTrue(sock.closed)

    async def test_frame_fragmentation_and_rejected_lengths_kinds(self):
        reader = asyncio.StreamReader()
        payload = '{"v":1,"type":"ping"}'.encode()
        task = asyncio.create_task(read_frame(reader))
        for byte in pack_frame(1, payload):
            reader.feed_data(bytes((byte,)))
            await asyncio.sleep(0)
        self.assertEqual(await task, (1, payload))
        for data in (struct.pack(">I", 0), struct.pack(">I", MAX_FRAME + 1),
                     struct.pack(">I", 1) + b"\x03", pack_frame(2, b"jpeg"),
                     struct.pack(">I", 16 * 1024 + 2) + b"\x01"):
            reader = asyncio.StreamReader()
            reader.feed_data(data)
            with self.assertRaises(ValueError):
                await read_frame(reader)

    async def test_bootstrap_opt_in_loopback_and_stream_lifetime(self):
        host = HostServer(capture_source=SyntheticJpegSource(), input_sink=RecordingInputSink())
        server = TestServer(host.make_app())
        await server.start_server()
        try:
            async with ClientSession() as session:
                async with session.get(server.make_url("/usb-bootstrap")) as response:
                    self.assertEqual(response.status, 403)
                host.usb_authorized = lambda: True
                async with session.get(server.make_url("/usb-bootstrap")) as response:
                    self.assertEqual(response.status, 503)
                host.running = True
                host.port = server.port
                async with session.get(server.make_url("/usb-bootstrap")) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                    data = await response.json()
                    self.assertEqual(data["token"], host.token)
                    self.assertEqual(data["port"], server.port)
                request = make_mocked_request("GET", "/usb-bootstrap",
                                              transport=SimpleNamespace(get_extra_info=lambda *args: ("192.0.2.4", 1234)))
                response = await host._usb_bootstrap(request)
                self.assertEqual(response.status, 403)
        finally:
            await server.close()

    async def test_ios_relay_real_authenticated_ws_settings_jpeg_and_disconnect(self):
        host = HostServer(capture_source=SyntheticJpegSource(), input_sink=RecordingInputSink(),
                          capture_config=CaptureConfig(fps=5))
        server = TestServer(host.make_app())
        await server.start_server()
        host.port, host.running = server.port, True
        connected = asyncio.Future()
        async def phone(reader, writer):
            connected.set_result((reader, writer))
        phone_server = await asyncio.start_server(phone, "127.0.0.1", 0)
        port = phone_server.sockets[0].getsockname()[1]
        class Mux:
            def connect(self, device):
                sock = socket.create_connection(("127.0.0.1", port), timeout=2)
                sock.setblocking(False)
                return sock
        relay = IOSUsbRelay(host, Mux())
        try:
            relay.start(AppleDevice(1, "FAKE-USB"))
            reader, writer = await asyncio.wait_for(connected, 3)
            async def receive():
                length, = struct.unpack(">I", await reader.readexactly(4))
                kind = (await reader.readexactly(1))[0]
                return kind, await reader.readexactly(length - 1)
            kind, payload = await asyncio.wait_for(receive(), 3)
            hello = json.loads(payload)
            self.assertEqual((kind, hello["v"], hello["type"], hello["mouseArmed"]), (1, 1, "hello", False))
            kind, jpeg = await asyncio.wait_for(receive(), 3)
            self.assertEqual(kind, 2)
            self.assertEqual(Image.open(BytesIO(jpeg)).size, (512, 288))
            for message in ({"v": 1, "type": "settings", "clientSeq": 9, "settings": {"mode": "fps", "scale": 1}},
                            {"v": 1, "type": "recenter"},
                            {"v": 1, "type": "pose", "seq": 1, "yaw": 0.2, "pitch": -0.1}):
                packet = pack_frame(1, json.dumps(message).encode())
                for piece in (packet[:2], packet[2:7], packet[7:]):
                    writer.write(piece)
                    await writer.drain()
            for _ in range(5):
                kind, payload = await asyncio.wait_for(receive(), 3)
                if kind == 1 and json.loads(payload).get("type") == "settings":
                    settings = json.loads(payload)
                    break
            self.assertEqual(settings["clientSeq"], 9)
            self.assertGreater(settings["revision"], hello["revision"])
            self.assertEqual(settings["settings"]["scale"], 1)
            self.assertFalse(host.controller.armed)
            self.assertEqual(host.controller.sink.moves, [])
            writer.close()
            await writer.wait_closed()
            for _ in range(30):
                if not host.controller.connected:
                    break
                await asyncio.sleep(.05)
            self.assertFalse(host.controller.connected)
        finally:
            await asyncio.to_thread(relay.stop)
            phone_server.close()
            await phone_server.wait_closed()
            await server.close()
