import asyncio
from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest

from aiohttp import ClientSession, WSServerHandshakeError, WSMsgType
from aiohttp.test_utils import TestServer

from vrization_host.capture import CaptureConfig, Frame, LatestFrameBuffer, output_size
from vrization_host.input import PoseController
from vrization_host.protocol import ProtocolError, Settings, TokenLimiter, parse_message
from vrization_host.server import HostServer
from vrization_host.storage import load_preferences, save_preferences


class FakeSink:
    def __init__(self):
        self.moves = []

    def move(self, dx, dy):
        self.moves.append((dx, dy))


class FakeCapture:
    def __init__(self):
        self.reads = 0
        self.closed = False

    def read(self, config):
        self.reads += 1
        return Frame(b"\xff\xd8" + str(self.reads).encode() + b"\xff\xd9", 640, 360, 0)

    def close(self):
        self.closed = True


class CaptureTests(unittest.TestCase):
    def test_long_edge_bounds_portrait_and_landscape_without_upscaling(self):
        self.assertEqual(output_size(2560, 1440, 1280), (1280, 720))
        self.assertEqual(output_size(2160, 3840, 1280), (720, 1280))
        self.assertEqual(output_size(800, 600, 1280), (800, 600))


class ProtocolTests(unittest.TestCase):
    def test_settings_strict_and_atomic(self):
        settings = Settings()
        for patch in ({"scale": True}, {"offsetX": float("nan")}, {"distortion": float("inf")},
                      {"sensitivity": 10**1000}, {"invertY": 1}, {"mode": []}, {"unknown": 1},
                      {"scale": 0.1}, {"mode": "fps", "fov": 111}, {}):
            with self.assertRaises(ProtocolError, msg=str(patch)[:80]):
                settings.update(patch)
        self.assertEqual(settings.mode, "full")
        self.assertEqual(settings.update({"mode": "fps", "scale": .5}).scale, .5)

    def test_pose_rejects_nonfinite_and_invalid_sequence(self):
        for text in ('{"v":1,"type":"pose","seq":1,"yaw":NaN,"pitch":0}',
                     '{"v":true,"type":"recenter"}',
                     '{"v":1,"type":"pose","seq":true,"yaw":0,"pitch":0}',
                     '{"v":1,"type":"pose","seq":1,"yaw":1e999,"pitch":0}',
                     '{"v":1,"type":"pose","seq":1,"yaw":{},"pitch":0}'):
            with self.assertRaises(ProtocolError):
                parse_message(text)
        self.assertEqual(parse_message('{"v":1,"type":"recenter"}')["type"], "recenter")

    def test_pairing_limiter_expires_and_global_cap(self):
        limiter = TokenLimiter(limit=2, window=60)
        limiter.failed("a", 10)
        limiter.failed("a", 11)
        self.assertFalse(limiter.allowed("a", 12))
        self.assertTrue(limiter.allowed("b", 12))
        self.assertTrue(limiter.allowed("a", 72))
        for index in range(12):
            limiter.failed(str(index), 73)
        self.assertFalse(limiter.allowed("new", 74))

    def test_preferences_do_not_store_secret_and_validate_on_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            save_preferences(Settings(mode="fps"), CaptureConfig(region=(1, 2, 400, 300)), path)
            restored, config = load_preferences(path)
            self.assertEqual(restored.mode, "fps")
            self.assertEqual(config.region, (1, 2, 400, 300))
            self.assertNotIn("token", path.read_text())
            self.assertNotIn("armed", path.read_text())
            path.write_text('{"settings":{"mode":"invalid"},"capture":{}}')
            self.assertEqual(load_preferences(path), (Settings(), CaptureConfig()))


class InputTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.sink = FakeSink()
        self.controller = PoseController(self.sink, clock=lambda: self.now)
        self.controller.set_settings(Settings(mode="fps"))
        self.controller.set_connected(True)
        self.controller.pose(1, 0, 0)

    def test_requires_explicit_arm_and_live_fps_session(self):
        self.controller.pose(2, .1, .1)
        self.assertEqual(self.sink.moves, [])
        self.assertTrue(self.controller.arm()[0])
        self.controller.pose(3, .1, .1)
        self.controller.pose(4, .12, .11)
        self.assertEqual(self.sink.moves, [(20, -10)])
        self.controller.set_settings(Settings(mode="cinema"))
        self.controller.pose(5, .13, .12)
        self.assertEqual(len(self.sink.moves), 1)
        self.assertFalse(self.controller.arm()[0])

    def test_wrapped_yaw_recenter_and_spike_drop(self):
        self.controller.arm()
        self.controller.pose(2, math.pi - .01, 0)
        self.controller.pose(3, -math.pi + .01, 0)
        self.assertEqual(self.sink.moves[-1], (20, 0))
        self.controller.pose(4, 0, 0)
        self.assertEqual(len(self.sink.moves), 1)
        self.controller.recenter()
        self.controller.pose(5, .2, 0)
        self.assertEqual(len(self.sink.moves), 1)
        self.controller.pose(6, .4, 0)
        self.assertEqual(self.sink.moves[-1], (120, 0))

    def test_stale_and_replayed_packets_do_not_move(self):
        self.controller.arm()
        self.controller.pose(2, 0, 0)
        self.controller.pose(2, .02, 0)
        self.assertEqual(self.sink.moves, [])
        self.now += .6
        self.controller.pose(3, .03, 0)
        self.assertFalse(self.controller.armed)
        self.assertEqual(self.sink.moves, [])
        self.controller.set_connected(False)
        self.assertFalse(self.controller.arm()[0])

    def test_watchdog_and_focus_change_disarm(self):
        focus = [None]
        self.controller.focus_provider = lambda: focus[0]
        self.controller.arm()
        self.controller.pose(2, 0, 0)
        focus[0] = 100
        self.controller.pose(3, .01, 0)
        self.controller.pose(4, .02, 0)
        self.assertEqual(self.sink.moves[-1], (10, 0))
        focus[0] = 101
        self.controller.pose(5, .03, 0)
        self.assertFalse(self.controller.armed)
        self.controller.arm()
        self.now += .51
        self.controller.tick()
        self.assertFalse(self.controller.armed)


class BufferTests(unittest.IsolatedAsyncioTestCase):
    async def test_latest_frame_skips_backlog_and_waits_for_new_frame(self):
        buffer = LatestFrameBuffer()
        for index in range(50):
            buffer.publish(Frame(str(index).encode(), 1, 1, 0))
        sequence, frame = await buffer.next(0)
        self.assertEqual((sequence, frame.jpeg), (50, b"49"))
        waiting = asyncio.create_task(buffer.next(50))
        await asyncio.sleep(0)
        self.assertFalse(waiting.done())
        buffer.publish(Frame(b"new", 1, 1, 0))
        self.assertEqual((await waiting)[1].jpeg, b"new")


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.source, self.sink = FakeCapture(), FakeSink()
        self.host = HostServer(capture_source=self.source, input_sink=self.sink)
        self.server = TestServer(self.host.make_app())
        await self.server.start_server()
        self.session = ClientSession()

    async def asyncTearDown(self):
        await self.session.close()
        await self.server.close()
        self.assertTrue(self.source.closed)

    def url(self, token=None):
        return self.server.make_url("/ws?token=" + (self.host.token if token is None else token))

    async def next_json(self, socket, kind):
        for _ in range(50):
            message = await asyncio.wait_for(socket.receive(), 3)
            if message.type == WSMsgType.TEXT:
                value = json.loads(message.data)
                if value["type"] == kind:
                    return value
        self.fail("missing JSON " + kind)

    async def test_auth_single_owner_settings_stream_and_disconnect(self):
        with self.assertRaises(WSServerHandshakeError) as context:
            await self.session.ws_connect(self.url("invalid"))
        self.assertEqual(context.exception.status, 401)
        socket = await self.session.ws_connect(self.url())
        hello = await self.next_json(socket, "hello")
        self.assertEqual(hello["v"], 1)
        self.assertEqual(hello["settings"]["mode"], "full")
        with self.assertRaises(WSServerHandshakeError) as context:
            await self.session.ws_connect(self.url())
        self.assertEqual(context.exception.status, 409)
        frame = await asyncio.wait_for(socket.receive(), 3)
        self.assertEqual(frame.type, WSMsgType.BINARY)
        self.assertTrue(frame.data.startswith(b"\xff\xd8"))
        await socket.send_json({"v": 1, "type": "settings", "settings": {"mode": "fps", "scale": .6}})
        updated = await self.next_json(socket, "settings")
        self.assertEqual(updated["settings"]["scale"], .6)
        await socket.send_json({"v": 1, "type": "pose", "seq": 1, "yaw": 0, "pitch": 0})
        await asyncio.sleep(.02)
        self.assertTrue(self.host.arm()[0])
        await socket.close()
        await asyncio.sleep(.02)
        self.assertFalse(self.host.controller.armed)
        self.assertEqual(self.sink.moves, [])
        replacement = await self.session.ws_connect(self.url())
        self.assertEqual((await self.next_json(replacement, "hello"))["settings"]["mode"], "fps")
        await replacement.close()

    async def test_bad_settings_are_rejected_without_mutating_state(self):
        socket = await self.session.ws_connect(self.url())
        await self.next_json(socket, "hello")
        await socket.send_str('{"v":1,"type":"settings","settings":{"scale":0.7,"sensitivity":NaN}}')
        await self.next_json(socket, "error")
        self.assertEqual(self.host.settings, Settings())
        await socket.close()


if __name__ == "__main__":
    unittest.main()
