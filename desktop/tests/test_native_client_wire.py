"""Independent RFC 6455 peer exercising the native-client wire contract.

This is not an Apple URLSession/device test. It verifies the host using masked
standard frames, including continuation/control frames, without capture or OS
input. Real iOS ATS, local-network permissions and rendering need Apple tests.
"""
import asyncio
import base64
import hashlib
from io import BytesIO
import json
from pathlib import Path
import random
import secrets
import struct
import time
import tomllib
import unittest

from aiohttp import ClientSession
from aiohttp.test_utils import TestServer
from PIL import Image

from vrization_host import __version__
from vrization_host.capture import CaptureConfig, Frame
from vrization_host.protocol import Settings
from vrization_host.server import HostServer


class SyntheticJpegSource:
    def __init__(self):
        # A deterministic, valid JPEG larger than 64 KiB exercises the extended
        # binary payload length instead of a toy SOI/EOI marker-only frame.
        image = Image.frombytes("RGB", (512, 288), random.Random(7).randbytes(512 * 288 * 3))
        output = BytesIO()
        image.save(output, "JPEG", quality=95)
        self.jpeg = output.getvalue()
        self.closed = False

    def read(self, config):
        return Frame(self.jpeg, 512, 288, time.monotonic())

    def close(self):
        self.closed = True


class RecordingInputSink:
    def __init__(self):
        self.moves = []

    def move(self, dx, dy):
        self.moves.append((dx, dy))


class StandardWebSocketPeer:
    """Small independent test peer; no aiohttp client-side WebSocket code."""
    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.pongs = []
        self.closed = False

    @classmethod
    async def connect(cls, url):
        reader, writer = await asyncio.open_connection(url.host, url.port)
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        # URLSession is not a browser: Origin and subprotocol are optional.
        request = (f"GET {url.raw_path_qs} HTTP/1.1\r\n"
                   f"Host: {url.host}:{url.port}\r\n"
                   "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                   f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
                   "User-Agent: VRization-native-wire-test\r\n\r\n")
        writer.write(request.encode("ascii"))
        await writer.drain()
        response = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 3)
        lines = response.decode("ascii").split("\r\n")
        if not lines[0].startswith("HTTP/1.1 101 "):
            writer.close()
            await writer.wait_closed()
            raise AssertionError(f"WebSocket handshake failed: {lines[0]}")
        headers = {key.lower(): value.strip() for key, value in
                   (line.split(":", 1) for line in lines[1:] if ":" in line)}
        expected = base64.b64encode(hashlib.sha1(
            (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()).decode("ascii")
        assert headers.get("sec-websocket-accept") == expected
        assert "sec-websocket-protocol" not in headers
        assert "sec-websocket-extensions" not in headers
        return cls(reader, writer)

    async def send_frame(self, opcode, payload=b"", *, final=True):
        mask = secrets.token_bytes(4)
        size = len(payload)
        header = bytes([(0x80 if final else 0) | opcode])
        if size < 126:
            header += bytes([0x80 | size])
        elif size <= 65535:
            header += bytes([0x80 | 126]) + struct.pack("!H", size)
        else:
            header += bytes([0x80 | 127]) + struct.pack("!Q", size)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.writer.write(header + mask + masked)
        await self.writer.drain()

    async def send_json(self, value):
        await self.send_frame(1, json.dumps(value, ensure_ascii=False).encode("utf-8"))

    async def receive(self):
        opcode, fragments = None, []
        while True:
            first, second = await asyncio.wait_for(self.reader.readexactly(2), 3)
            assert first & 0x70 == 0, "Unexpected reserved/compression bits"
            assert second & 0x80 == 0, "Servers must not mask their frames"
            kind, size = first & 0x0f, second & 0x7f
            if size == 126:
                size = struct.unpack("!H", await self.reader.readexactly(2))[0]
            elif size == 127:
                size = struct.unpack("!Q", await self.reader.readexactly(8))[0]
            assert size <= 8 * 1024 * 1024, "Unexpectedly oversized test-server frame"
            payload = await asyncio.wait_for(self.reader.readexactly(size), 3)
            if kind == 9:
                await self.send_frame(10, payload)
                continue
            if kind == 10:
                self.pongs.append(payload)
                continue
            if kind == 8:
                if not self.closed:
                    await self.send_frame(8, payload)
                self.closed = True
                return kind, payload
            if kind in (1, 2):
                assert opcode is None, "Interleaved data messages"
                opcode = kind
            else:
                assert kind == 0 and opcode is not None, "Unexpected continuation"
            fragments.append(payload)
            if first & 0x80:
                return opcode, b"".join(fragments)

    async def next_json(self, kind):
        for _ in range(50):
            opcode, payload = await self.receive()
            if opcode == 1:
                value = json.loads(payload)
                if value.get("type") == kind:
                    return value
            assert opcode != 8, "Socket closed before expected JSON"
        raise AssertionError("Missing JSON " + kind)

    async def next_binary(self):
        for _ in range(50):
            opcode, payload = await self.receive()
            if opcode == 2:
                return payload
            assert opcode != 8, "Socket closed before expected JPEG"
        raise AssertionError("Missing JPEG")

    async def next_close(self):
        for _ in range(50):
            opcode, payload = await self.receive()
            if opcode == 8:
                return struct.unpack("!H", payload[:2])[0] if len(payload) >= 2 else None
        raise AssertionError("Missing close frame")

    async def close(self, code=1000):
        if not self.closed and not self.writer.is_closing():
            await self.send_frame(8, struct.pack("!H", code))
            self.closed = True
            await self.next_close()
        self.writer.close()
        await self.writer.wait_closed()


class NativeClientWireTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.source, self.sink = SyntheticJpegSource(), RecordingInputSink()
        self.host = HostServer(capture_source=self.source, input_sink=self.sink,
                               capture_config=CaptureConfig(fps=5), host="127.0.0.1")
        self.server = TestServer(self.host.make_app(), host="127.0.0.1")
        await self.server.start_server()
        self.peers = []

    async def asyncTearDown(self):
        for peer in self.peers:
            if not peer.writer.is_closing():
                await peer.close()
        await self.server.close()
        self.assertTrue(self.source.closed)
        self.assertEqual(self.sink.moves, [])

    async def connect(self, *, settings_schema2=False):
        url = self.server.make_url("/ws?token=" + self.host.token + ("&settingsSchema=2" if settings_schema2 else ""))
        peer = await StandardWebSocketPeer.connect(url)
        self.peers.append(peer)
        return peer

    async def wait_disconnected(self):
        for _ in range(100):
            if self.host._ws is None and not self.host.controller.connected:
                return
            await asyncio.sleep(.01)
        self.fail("Host did not release its previous session")

    async def test_standard_handshake_valid_jpeg_and_consistent_versions(self):
        peer = await self.connect()
        hello = await peer.next_json("hello")
        self.assertEqual((hello["v"], hello["version"], hello["revision"]), (1, __version__, 0))
        legacy = Settings().to_dict()
        legacy.pop("stabilization", None)
        self.assertEqual(hello["settings"], legacy)
        self.assertEqual(hello["capabilities"], ["stabilization"])
        self.assertEqual(hello["stream"]["codec"], "jpeg")
        self.assertFalse(hello["mouseArmed"])
        jpeg = await peer.next_binary()
        self.assertGreater(len(jpeg), 65535)
        self.assertEqual(jpeg, self.source.jpeg)
        with Image.open(BytesIO(jpeg)) as image:
            self.assertEqual((image.format, image.size), ("JPEG", (512, 288)))
            image.verify()
        async with ClientSession() as session:
            async with session.get(self.server.make_url("/health")) as response:
                health = await response.json()
        self.assertEqual((health["version"], health["protocol"], health["connected"]), (__version__, 1, True))
        project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(project["project"]["version"], __version__)

    async def test_schema2_settings_roundtrip_and_legacy_reconnect(self):
        peer = await self.connect(settings_schema2=True)
        hello = await peer.next_json("hello")
        self.assertEqual(hello["settings"]["stabilization"], 0)
        await peer.send_json({"v": 1, "type": "settings", "clientSeq": 7,
                              "settings": {"stabilization": .75}})
        ack = await peer.next_json("settings")
        self.assertEqual((ack["clientSeq"], ack["settings"]["stabilization"]), (7, .75))
        await peer.close()
        await self.wait_disconnected()
        legacy = await self.connect()
        old_hello = await legacy.next_json("hello")
        self.assertNotIn("stabilization", old_hello["settings"])
        self.assertEqual(self.host.get_settings_snapshot()[0].stabilization, .75)
        self.host.update_settings({"stabilization": .5})
        self.assertNotIn("stabilization", (await legacy.next_json("settings"))["settings"])
        self.assertFalse(self.host.controller.armed)

    async def test_usb_style_hello_upgrades_settings_without_new_session(self):
        self.host.update_settings({"stabilization": .6})
        peer = await self.connect()
        hello = await peer.next_json("hello")
        self.assertNotIn("stabilization", hello["settings"])
        await peer.send_json({"v": 1, "type": "hello", "settingsSchema": 2, "editing": True})
        settings = await peer.next_json("settings")
        self.assertEqual((settings["revision"], settings["settings"]["stabilization"]), (1, .6))
        self.assertTrue(self.host.controller.connected)
        self.assertFalse(self.host.controller.armed)
        await peer.send_json({"v": 1, "type": "settings", "clientSeq": 8,
                              "settings": {"offsetY": .12}})
        ack = await peer.next_json("settings")
        self.assertEqual((ack["clientSeq"], ack["settings"]["stabilization"]), (8, .6))

    async def test_non_integer_capability_does_not_change_legacy_wire_shape(self):
        peer = await self.connect()
        await peer.next_json("hello")
        await peer.send_json({"v": 1, "type": "hello", "settingsSchema": "2", "editing": True})
        await peer.send_json({"v": 1, "type": "settings", "clientSeq": 1,
                              "settings": {"offsetX": .12}})
        self.assertNotIn("stabilization", (await peer.next_json("settings"))["settings"])
        self.assertFalse(self.host.controller.armed)

    async def test_fragmented_utf8_settings_ping_and_revision_acknowledgement(self):
        peer = await self.connect()
        await peer.next_json("hello")
        request = {"v": 1, "type": "settings", "clientSeq": 2**53 - 1,
                   "settings": {"scale": 1.0, "offsetX": -.3, "eyeSeparation": .2,
                                "invertY": False}, "client": "iPhone 🥽 / 手机"}
        payload = json.dumps(request, ensure_ascii=False).encode("utf-8")
        split = payload.index("🥽".encode("utf-8")) + 1
        await peer.send_frame(1, payload[:split], final=False)
        await peer.send_frame(9, b"native-ping")
        await peer.send_frame(0, payload[split:])
        ack = await peer.next_json("settings")
        self.assertEqual((ack["clientSeq"], ack["revision"]), (2**53 - 1, 1))
        self.assertEqual(ack["settings"]["offsetX"], -.3)
        self.assertEqual(ack["settings"]["eyeSeparation"], .2)
        self.assertIs(ack["settings"]["invertY"], False)
        self.assertIn(b"native-ping", peer.pongs)
        self.host.update_settings({"fov": 110})
        broadcast = await peer.next_json("settings")
        self.assertEqual((broadcast["revision"], broadcast["settings"]["fov"]), (2, 110))
        self.assertNotIn("clientSeq", broadcast)

    async def test_pose_recenter_and_remote_arm_never_authorize_mouse(self):
        peer = await self.connect()
        await peer.next_json("hello")
        await peer.send_json({"v": 1, "type": "settings", "settings": {"mode": "fps"}})
        await peer.next_json("settings")
        for sequence, yaw in ((0, 0), (1, .1)):
            await peer.send_json({"v": 1, "type": "pose", "seq": sequence, "yaw": yaw, "pitch": 0})
        await peer.send_json({"v": 1, "type": "recenter"})
        await peer.send_json({"v": 1, "type": "pose", "seq": 2, "yaw": .2, "pitch": -.1})
        await peer.send_json({"v": 1, "type": "arm"})
        self.assertIn("unknown", (await peer.next_json("error"))["message"])
        await peer.send_json({"v": 1, "type": "ping"})
        await peer.next_json("pong")  # Processing barrier; no timing sleeps.
        self.assertEqual(self.host.controller.last_seq, 2)
        self.assertFalse(self.host.controller.armed)
        self.assertEqual(self.sink.moves, [])

    async def test_joined_spacing_is_accepted_acknowledged_and_broadcast_to_phone(self):
        peer = await self.connect()
        await peer.next_json("hello")
        await peer.send_json({"v": 1, "type": "settings", "clientSeq": 7,
                              "settings": {"scale": .5, "offsetX": 0, "eyeSeparation": -.75}})
        ack = await peer.next_json("settings")
        self.assertEqual((ack["clientSeq"], ack["revision"]), (7, 1))
        self.assertEqual(ack["settings"]["eyeSeparation"], -.75)
        self.host.update_settings({"scale": .6, "eyeSeparation": -.7})
        broadcast = await peer.next_json("settings")
        self.assertEqual((broadcast["revision"], broadcast["settings"]["eyeSeparation"]), (2, -.7))
        self.assertNotIn("clientSeq", broadcast)
        self.assertFalse(self.host.controller.armed)
        self.assertEqual(self.sink.moves, [])

    async def test_normal_close_reconnect_preserves_settings_resets_pose_sequence(self):
        first = await self.connect()
        await first.next_json("hello")
        await first.send_json({"v": 1, "type": "settings", "clientSeq": 0,
                               "settings": {"scale": .75, "mode": "fps"}})
        await first.next_json("settings")
        await first.send_json({"v": 1, "type": "pose", "seq": 99, "yaw": .1, "pitch": .1})
        await first.send_json({"v": 1, "type": "ping"})
        await first.next_json("pong")
        await first.close()
        await self.wait_disconnected()
        replacement = await self.connect()
        hello = await replacement.next_json("hello")
        self.assertEqual((hello["revision"], hello["settings"]["scale"]), (1, .75))
        self.assertFalse(hello["mouseArmed"])
        await replacement.send_json({"v": 1, "type": "pose", "seq": 0, "yaw": 0, "pitch": 0})
        await replacement.send_json({"v": 1, "type": "ping"})
        await replacement.next_json("pong")
        self.assertEqual(self.host.controller.last_seq, 0)
        self.assertFalse(self.host.controller.armed)
        self.assertEqual(await replacement.next_binary(), self.source.jpeg)

    async def test_host_going_away_close_releases_owner_for_reconnect(self):
        first = await self.connect()
        await first.next_json("hello")
        closing = asyncio.create_task(self.host._ws.close(code=1001, message=b"host stopping"))
        self.assertEqual(await first.next_close(), 1001)
        await asyncio.wait_for(closing, 3)
        await first.close()
        await self.wait_disconnected()
        replacement = await self.connect()
        self.assertFalse((await replacement.next_json("hello"))["mouseArmed"])
        self.assertEqual(await replacement.next_binary(), self.source.jpeg)

    async def test_fragmented_message_size_limit_applies_to_complete_message(self):
        peer = await self.connect()
        await peer.next_json("hello")
        payload = json.dumps({"v": 1, "type": "hello", "padding": "x" * (17 * 1024)}).encode()
        await peer.send_frame(1, payload[:9000], final=False)
        await peer.send_frame(0, payload[9000:])
        self.assertEqual(await peer.next_close(), 1009)
        await self.wait_disconnected()
        self.assertEqual(self.host.get_settings_snapshot(), (Settings(), 0))


if __name__ == "__main__":
    unittest.main()
