"""Actual masked loopback peers; only synthetic capture and recorded mouse deltas."""
import asyncio
import json
import unittest

from aiohttp.test_utils import TestServer

from vrization_host.capture import CaptureConfig
from vrization_host.protocol import ProtocolError, Settings, parse_message
from vrization_host.server import HostServer
from test_native_client_wire import RecordingInputSink, StandardWebSocketPeer, SyntheticJpegSource


class EnhancedCapabilityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.source = SyntheticJpegSource()
        self.sink = RecordingInputSink()
        self.host = HostServer(self.source, self.sink, Settings(mode="fps_enhanced"),
                               CaptureConfig(fps=5), auto_control=True)
        self.server = TestServer(self.host.make_app(), host="127.0.0.1")
        self.peers = []
        await self.server.start_server()

    async def asyncTearDown(self):
        for peer in self.peers:
            if not peer.writer.is_closing():
                await peer.close()
        await self.server.close()
        self.assertTrue(self.source.closed)

    async def connect(self, query=""):
        peer = await StandardWebSocketPeer.connect(self.server.make_url(f"/ws?token={self.host.token}{query}"))
        self.peers.append(peer)
        return peer, await peer.next_json("hello")

    async def opt_in(self, peer, editing=False):
        await peer.send_json({"v": 1, "type": "hello", "settingsSchema": 2,
                              "capabilities": ["enhanced-first-person"], "editing": editing})
        return await peer.next_json("settings")

    async def pose(self, peer, sequence, yaw):
        await peer.send_json({"v": 1, "type": "pose", "seq": sequence, "yaw": yaw, "pitch": 0})
        await peer.send_json({"v": 1, "type": "ping"})
        await peer.next_json("pong")

    async def test_legacy_client_gets_flat_first_person_without_changing_host(self):
        peer, hello = await self.connect()
        self.assertEqual(hello["settings"]["mode"], "fps")
        self.assertIs(hello["enhancedFirstPerson"], False)
        self.assertNotIn("stabilization", hello["settings"])
        self.assertEqual(self.host.settings.mode, "fps_enhanced")
        self.host.update_settings({"scale": .6})
        update = await peer.next_json("settings")
        self.assertEqual(update["settings"]["mode"], "fps")
        self.assertIs(update["enhancedFirstPerson"], False)

    async def test_lan_query_negotiates_initial_full_snapshot(self):
        peer, hello = await self.connect("&settingsSchema=2&enhancedFirstPerson=1")
        self.assertEqual(hello["settings"], self.host.settings.to_dict())
        self.assertIs(hello["enhancedFirstPerson"], True)
        self.assertFalse(self.host.controller.armed)
        await self.pose(peer, 0, 0)
        self.assertEqual(self.sink.moves, [])
        await self.pose(peer, 1, .03)
        self.assertEqual(self.sink.moves, [(30, 0)])

    async def test_usb_opt_in_sends_complete_true_marked_snapshot_without_mode_edit(self):
        peer, hello = await self.connect()
        self.assertEqual(hello["settings"]["mode"], "fps")
        before = self.host.get_settings_snapshot()
        update = await self.opt_in(peer)
        self.assertIs(update["enhancedFirstPerson"], True)
        self.assertEqual(update["settings"], before[0].to_dict())
        self.assertNotIn("clientSeq", update)
        self.assertEqual(self.host.get_settings_snapshot(), before)
        self.assertFalse(self.host.controller.armed)

    async def test_undeclared_enhanced_patch_is_rejected_atomically(self):
        peer, _ = await self.connect("&settingsSchema=2")
        before = self.host.get_settings_snapshot()
        await peer.send_json({"v": 1, "type": "settings", "settings": {"mode": "fps_enhanced", "scale": .5}})
        error = await peer.next_json("error")
        self.assertIn("capability", error["message"])
        self.assertEqual(self.host.get_settings_snapshot(), before)
        update = await self.opt_in(peer)
        self.assertTrue(update["enhancedFirstPerson"])
        await peer.send_json({"v": 1, "type": "settings", "clientSeq": 2,
                              "settings": {"mode": "fps_enhanced", "scale": .5}})
        accepted = await peer.next_json("settings")
        self.assertEqual(accepted["clientSeq"], 2)
        self.assertEqual(accepted["settings"]["scale"], .5)

    async def test_capability_mode_switches_and_editor_exit_cannot_clear_f8_latch(self):
        peer, _ = await self.connect()
        self.host.disarm("F8 emergency stop")
        await self.opt_in(peer, editing=True)
        await self.pose(peer, 0, 0)
        for mode in ("fps", "fps_enhanced"):
            await peer.send_json({"v": 1, "type": "settings", "settings": {"mode": mode}})
            await peer.next_json("settings")
            await peer.send_json({"v": 1, "type": "hello", "editing": False})
            await self.pose(peer, 1 if mode == "fps" else 2, .1)
        self.assertTrue(self.host.controller.suspended)
        self.assertEqual(self.sink.moves, [])
        self.host.resume_control()
        await self.pose(peer, 3, 1)
        self.assertEqual(self.sink.moves, [])
        await self.pose(peer, 4, 1.03)
        self.assertEqual(self.sink.moves, [(30, 0)])

    async def test_negotiation_is_owned_by_session_and_does_not_leak_to_next_phone(self):
        peer, hello = await self.connect("&settingsSchema=2&enhancedFirstPerson=1")
        self.assertTrue(hello["enhancedFirstPerson"])
        await peer.close()
        deadline = asyncio.get_running_loop().time() + 2
        while self.host._ws is not None and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(.005)
        self.assertIsNone(self.host._ws)
        _, next_hello = await self.connect()
        self.assertIs(next_hello["enhancedFirstPerson"], False)
        self.assertEqual(next_hello["settings"]["mode"], "fps")


class CapabilityValidationTests(unittest.TestCase):
    def test_invalid_capability_shapes_fail_and_future_bounded_strings_work(self):
        for value in (True, "enhanced-first-person", [1], [""], ["x" * 65], ["x"] * 33):
            with self.subTest(value=value):
                with self.assertRaises(ProtocolError):
                    parse_message(json.dumps({"v": 1, "type": "hello", "capabilities": value}))
        message = {"v": 1, "type": "hello", "capabilities": ["enhanced-first-person", "future-capability"]}
        self.assertEqual(parse_message(json.dumps(message)), message)
