"""Desktop gyro policy across persistence, mocked UI, and loopback transport.

Only original synthetic JPEGs and recorded relative movements are used. No
desktop capture, Windows input, native UI, USB bridge, or user preferences are
opened by these tests.
"""

import asyncio
import json
from pathlib import Path
import queue
import socket
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from aiohttp.test_utils import TestServer
from yarl import URL

from vrization_host.capture import CaptureConfig
from vrization_host.gui import HostWindow
from vrization_host.protocol import Settings
from vrization_host.server import HostServer
from vrization_host.storage import load_input_preferences, save_input_preferences
from test_native_client_wire import (RecordingInputSink, StandardWebSocketPeer,
                                     SyntheticJpegSource)


class InputPreferenceTests(unittest.TestCase):
    def test_missing_or_corrupt_preferences_default_to_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            self.assertEqual(load_input_preferences(path), {"gyro_control_enabled": True})
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(load_input_preferences(path), {"gyro_control_enabled": True})

    def test_only_an_actual_boolean_overrides_the_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for invalid in (0, 1, "false", "true", None, [], {}):
                with self.subTest(invalid=invalid):
                    path.write_text(json.dumps({"gyro_control_enabled": invalid}), encoding="utf-8")
                    self.assertEqual(load_input_preferences(path), {"gyro_control_enabled": True})
            for non_object in ([], None, False):
                with self.subTest(non_object=non_object):
                    path.write_text(json.dumps(non_object), encoding="utf-8")
                    self.assertEqual(load_input_preferences(path), {"gyro_control_enabled": True})

    def test_round_trip_keeps_disabled_choice_without_persisting_session_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            save_input_preferences({"gyro_control_enabled": False, "armed": True,
                                    "suspended": True, "paused": True}, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")),
                             {"gyro_control_enabled": False})
            self.assertEqual(load_input_preferences(path), {"gyro_control_enabled": False})
            save_input_preferences({"gyro_control_enabled": True, "armed": True}, path)
            self.assertEqual(load_input_preferences(path), {"gyro_control_enabled": True})
            self.assertEqual(list(path.parent.glob("input-*.tmp")), [])

    def test_invalid_save_does_not_replace_existing_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            save_input_preferences({"gyro_control_enabled": False}, path)
            original = path.read_bytes()
            for invalid in (0, 1, "false", None):
                with self.subTest(invalid=invalid):
                    with self.assertRaises(ValueError):
                        save_input_preferences({"gyro_control_enabled": invalid}, path)
                    self.assertEqual(path.read_bytes(), original)


def partial_window(host):
    """Construct only the UI adapter; all widgets and native scheduling are mocks."""
    window = HostWindow.__new__(HostWindow)
    window.server = host
    window.input_preferences = {"gyro_control_enabled": True}
    window.hotkey_available = True
    window.editor = None
    window.arm_var = Mock()
    window.arm_var.get.return_value = True
    window.arm_status = Mock()
    window.resume_button = Mock()
    window._log = Mock()
    window.tr = lambda text, **values: text.format(**values)
    window.events = queue.SimpleQueue()
    window.root = Mock()
    window.root.winfo_children.return_value = []
    window._stop_in_progress = False
    window._stop_generation = 0
    window.last_error = ""
    return window


class GuiGyroPolicyTests(unittest.TestCase):
    def make_window(self):
        sink = RecordingInputSink()
        sink.external_foreground = Mock(return_value=None)
        host = HostServer(SyntheticJpegSource(), sink, auto_control=True)
        return partial_window(host), sink

    def test_input_events_and_pause_keep_the_user_policy_checked(self):
        window, _ = self.make_window()
        host = window.server
        host.update_settings({"mode": "fps"})
        host.controller.set_connected(True)
        host.controller.pose(0, 0, 0)
        host.disarm("F8 emergency stop")
        window.events.put({"event": "input", "armed": False, "reason": "F8 emergency stop"})
        with patch("vrization_host.gui.save_input_preferences") as save:
            window._pump()
        save.assert_not_called()
        window.arm_var.set.assert_not_called()
        self.assertTrue(window.input_preferences["gyro_control_enabled"])
        self.assertTrue(host.get_control_state()["enabled"])
        self.assertTrue(host.get_control_state()["paused"])
        window.arm_status.configure.assert_called_once_with(
            text="Gyro mouse paused · click Resume gyro control")

    def test_explicit_resume_clears_f8_latch_without_a_game_or_connected_phone(self):
        window, sink = self.make_window()
        host = window.server
        host.disarm("F8 emergency stop")
        self.assertFalse(host.controller.connected)
        self.assertEqual(host.settings.mode, "full")
        with patch("vrization_host.gui.save_input_preferences") as save:
            self.assertTrue(window.resume_gyro_control())
        save.assert_called_once_with({"gyro_control_enabled": True})
        window.arm_var.set.assert_called_once_with(True)
        self.assertFalse(host.get_control_state()["paused"])
        self.assertFalse(host.get_control_state()["armed"])
        sink.external_foreground.assert_not_called()
        self.assertEqual(sink.moves, [])
        window.arm_status.configure.assert_called_once_with(
            text="Gyro mouse enabled · waiting for phone")

    def test_unchecking_disables_control_and_saves_the_off_choice(self):
        window, sink = self.make_window()
        host = window.server
        host.update_settings({"mode": "fps"})
        host.controller.set_connected(True)
        host.controller.pose(0, 0, 0)
        window.arm_var.get.return_value = False
        with patch("vrization_host.gui.save_input_preferences") as save:
            window.toggle_arm()
        save.assert_called_once_with({"gyro_control_enabled": False})
        self.assertFalse(host.get_control_state()["enabled"])
        self.assertFalse(host.get_control_state()["armed"])
        host.controller.pose(1, .03, .01)
        self.assertEqual(sink.moves, [])
        window.arm_status.configure.assert_called_once_with(text="Gyro mouse disabled")

    def test_language_rebuild_preserves_active_control_and_explicit_pause(self):
        for paused in (False, True):
            with self.subTest(paused=paused):
                window, _ = self.make_window()
                host = window.server
                host.update_settings({"mode": "fps"})
                host.controller.set_connected(True)
                host.controller.pose(0, 0, 0)
                if paused:
                    host.disarm("F8 emergency stop")
                before = host.get_control_state()
                window.language = "en"
                window.language_choice = SimpleNamespace(get=lambda: "简体中文")
                window.notebook = Mock()
                window.notebook.index.side_effect = lambda which: 2 if which == "current" else 4
                # Exercise the real rebuild while replacing only widget creation.
                window._build = Mock()
                for name in ("code_label", "start_button", "stop_button", "status", "stats"):
                    setattr(window, name, Mock())
                with patch("vrization_host.gui.save_language") as language, \
                     patch("vrization_host.gui.save_input_preferences") as save:
                    window.change_language()
                language.assert_called_once_with("zh")
                save.assert_not_called()
                window._build.assert_called_once_with()
                window.notebook.select.assert_called_once_with(2)
                window.arm_var.set.assert_not_called()
                self.assertEqual(host.get_control_state(), before)
                self.assertTrue(window.input_preferences["gyro_control_enabled"])

    def test_unavailable_emergency_hotkey_pauses_input_without_overwriting_policy(self):
        window, sink = self.make_window()
        window.events.put({"event": "hotkey_error", "message": "F8 is in use"})
        with patch("vrization_host.gui.save_input_preferences") as save:
            window._pump()
            self.assertFalse(window.resume_gyro_control())
        save.assert_not_called()
        self.assertFalse(window.hotkey_available)
        self.assertTrue(window.input_preferences["gyro_control_enabled"])
        self.assertFalse(window.server.get_control_state()["enabled"])
        self.assertTrue(window.server.get_control_state()["paused"])
        window.arm_var.set.assert_not_called()
        self.assertEqual(sink.moves, [])


class GyroWirePolicyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.source = SyntheticJpegSource()
        self.sink = RecordingInputSink()
        self.sink.external_foreground = Mock(return_value=None)
        self.host = HostServer(self.source, self.sink, settings=Settings(mode="fps"),
                               capture_config=CaptureConfig(fps=5), host="127.0.0.1",
                               auto_control=True)
        self.peers = []
        self.servers = []
        await self.start_lifecycle()

    async def start_lifecycle(self):
        self.server = TestServer(self.host.make_app(), host="127.0.0.1")
        self.servers.append(self.server)
        await self.server.start_server()

    async def asyncTearDown(self):
        for peer in self.peers:
            if not peer.writer.is_closing():
                await peer.close()
        for server in reversed(self.servers):
            await server.close()
        self.assertTrue(self.source.closed)
        self.sink.external_foreground.assert_not_called()

    async def connect(self):
        peer = await StandardWebSocketPeer.connect(
            self.server.make_url(f"/ws?token={self.host.token}&settingsSchema=2"))
        self.peers.append(peer)
        hello = await peer.next_json("hello")
        self.assertFalse(hello["mouseArmed"])
        return peer

    async def barrier(self, peer):
        # A validated ping follows the preceding messages in the same stream.
        await peer.send_json({"v": 1, "type": "ping"})
        await peer.next_json("pong")

    async def pose(self, peer, seq, yaw, pitch=0):
        await peer.send_json({"v": 1, "type": "pose", "seq": seq, "yaw": yaw, "pitch": pitch})
        await self.barrier(peer)

    async def settings(self, peer, **patch_values):
        await peer.send_json({"v": 1, "type": "settings", "settings": patch_values})
        await peer.next_json("settings")

    async def wait_until(self, predicate):
        deadline = time.monotonic() + 2
        while not predicate() and time.monotonic() < deadline:
            await asyncio.sleep(.005)
        self.assertTrue(predicate(), "Synthetic lifecycle did not reach the expected state")

    async def test_first_person_poses_move_immediately_without_arm_or_game_focus(self):
        peer = await self.connect()
        with patch.object(self.host, "arm") as explicit_arm:
            await self.pose(peer, 0, 0, 0)
            self.assertEqual(self.sink.moves, [])
            await self.pose(peer, 1, .03, .01)
        explicit_arm.assert_not_called()
        self.assertEqual(self.sink.moves, [(30, -10)])
        self.assertTrue(self.host.get_control_state()["armed"])
        self.assertFalse(self.host.get_control_state()["paused"])

    async def test_full_and_cinema_never_move_and_returning_to_first_person_is_fresh(self):
        peer = await self.connect()
        seq = 0
        for mode in ("full", "cinema"):
            with self.subTest(mode=mode):
                await self.settings(peer, mode=mode)
                await self.pose(peer, seq, .4)
                await self.pose(peer, seq + 1, .43)
                seq += 2
                self.assertFalse(self.host.get_control_state()["armed"])
                self.assertEqual(self.sink.moves, [])
        await self.settings(peer, mode="fps")
        await self.pose(peer, seq, 1)
        self.assertEqual(self.sink.moves, [])
        await self.pose(peer, seq + 1, 1.03)
        self.assertEqual(self.sink.moves, [(30, 0)])

    async def test_f8_latch_survives_settings_disconnect_and_reconnect_until_resume(self):
        peer = await self.connect()
        await self.pose(peer, 0, 0)
        await self.pose(peer, 1, .03)
        self.assertEqual(self.sink.moves, [(30, 0)])
        self.sink.moves.clear()
        self.host.disarm("F8 emergency stop")
        await self.pose(peer, 2, .06)
        for mode in ("full", "cinema", "fps"):
            await self.settings(peer, mode=mode, sensitivity=1000)
        await peer.send_json({"v": 1, "type": "recenter"})
        await peer.send_json({"v": 1, "type": "hello", "editing": False})
        await self.pose(peer, 3, .09)
        self.host.set_auto_control(True)
        self.assertTrue(self.host.get_control_state()["paused"])
        self.assertEqual(self.sink.moves, [])
        await peer.close()
        await self.wait_until(lambda: self.host._ws is None)
        self.assertFalse(self.host.get_control_state()["connected"])
        fresh = await self.connect()
        await self.pose(fresh, 0, .5)
        await self.pose(fresh, 1, .53)
        self.assertTrue(self.host.get_control_state()["paused"])
        self.assertFalse(self.host.get_control_state()["armed"])
        self.assertEqual(self.sink.moves, [])
        self.assertTrue(self.host.resume_control()[0])
        await self.pose(fresh, 2, 1)
        self.assertEqual(self.sink.moves, [])
        await self.pose(fresh, 3, 1.03)
        self.assertEqual(self.sink.moves, [(30, 0)])

    async def test_capture_failure_blocks_resume_until_a_restarted_stream(self):
        peer = await self.connect()
        await self.pose(peer, 0, 0)
        await self.pose(peer, 1, .03)
        self.sink.moves.clear()
        with patch.object(self.source, "read", side_effect=RuntimeError("synthetic capture lost")):
            await self.wait_until(lambda: self.host._capture_failed)
            self.assertTrue(self.host.get_control_state()["paused"])
            self.assertFalse(self.host.get_control_state()["armed"])
            success, reason = self.host.resume_control()
            self.assertFalse(success)
            self.assertIn("Restart streaming", reason)
            await self.pose(peer, 2, .06)
            self.assertEqual(self.sink.moves, [])
        await peer.close()
        await self.server.close()
        self.assertTrue(self.source.closed)
        self.source.closed = False
        await self.start_lifecycle()
        self.assertFalse(self.host._capture_failed)
        fresh = await self.connect()
        await self.pose(fresh, 0, .5)
        await self.pose(fresh, 1, .53)
        self.assertTrue(self.host.get_control_state()["paused"])
        self.assertEqual(self.sink.moves, [])
        self.assertTrue(self.host.resume_control()[0])
        await self.pose(fresh, 2, 1)
        self.assertEqual(self.sink.moves, [])
        await self.pose(fresh, 3, 1.03)
        self.assertEqual(self.sink.moves, [(30, 0)])

    async def test_stop_latches_immediately_and_real_restart_requires_explicit_resume(self):
        peer = await self.connect()
        await self.pose(peer, 0, 0)
        await self.pose(peer, 1, .03)
        self.assertEqual(self.sink.moves, [(30, 0)])
        self.sink.moves.clear()
        self.host.request_stop()
        self.assertTrue(self.host._stopping.is_set())
        state = self.host.get_control_state()
        self.assertTrue(state["paused"])
        self.assertFalse(state["connected"])
        self.assertFalse(state["armed"])
        for action in (self.host.arm, self.host.resume_control):
            success, reason = action()
            self.assertFalse(success)
            self.assertIn("Restart streaming", reason)
        await peer.close()
        await self.server.close()
        self.assertTrue(self.host.stop())

        # Exercise HostServer.start's real restart boundary, including a new
        # network thread, while retaining only the synthetic source and sink.
        with socket.socket() as reserved:
            reserved.bind(("127.0.0.1", 0))
            self.host.port = reserved.getsockname()[1]
        self.source.closed = False
        fresh = None
        try:
            await asyncio.to_thread(self.host.start)
            self.assertTrue(self.host.running)
            self.assertFalse(self.host._stopping.is_set())
            self.assertTrue(self.host.get_control_state()["paused"])
            fresh = await StandardWebSocketPeer.connect(URL(
                f"http://127.0.0.1:{self.host.port}/ws?token={self.host.token}&settingsSchema=2"))
            self.peers.append(fresh)
            self.assertFalse((await fresh.next_json("hello"))["mouseArmed"])
            await self.settings(fresh, mode="full")
            await self.settings(fresh, mode="fps")
            await self.pose(fresh, 0, .5)
            await self.pose(fresh, 1, .53)
            self.assertTrue(self.host.get_control_state()["paused"])
            self.assertEqual(self.sink.moves, [])
            self.assertTrue(self.host.resume_control()[0])
            await self.pose(fresh, 2, 1)
            self.assertEqual(self.sink.moves, [])
            await self.pose(fresh, 3, 1.03)
            self.assertEqual(self.sink.moves, [(30, 0)])
        finally:
            if fresh is not None and not fresh.writer.is_closing():
                await fresh.close()
            self.assertTrue(await asyncio.to_thread(self.host.stop))


if __name__ == "__main__":
    unittest.main()
