"""Real loopback shutdown using synthetic capture and a recording input sink."""
import asyncio
import json
import queue
import socket
import threading
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from aiohttp import ClientSession
from aiohttp.test_utils import TestServer
from yarl import URL

from vrization_host.capture import CaptureConfig
from vrization_host.gui import HostWindow
from vrization_host.protocol import Settings
from vrization_host.server import HostServer
from test_native_client_wire import SyntheticJpegSource, RecordingInputSink, StandardWebSocketPeer


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ServerStopTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_does_not_count_a_closed_socket_as_connected(self):
        host = HostServer(SyntheticJpegSource(), RecordingInputSink())
        host._ws = SimpleNamespace(closed=False)
        self.assertTrue(json.loads((await host._health(None)).text)["connected"])
        host._ws.closed = True
        self.assertFalse(json.loads((await host._health(None)).text)["connected"])

    async def test_disconnect_releases_input_status_and_session_before_blocked_sender_cleanup(self):
        entered, cancelled, release, finished = (asyncio.Event() for _ in range(4))
        events, sink = [], RecordingInputSink()
        host = HostServer(SyntheticJpegSource(), sink, settings=Settings(mode="fps"),
                          on_event=events.append, capture_config=CaptureConfig(fps=5))
        actual_sender, calls = host._send_frames, []
        async def blocked_first_sender(ws):
            calls.append(ws)
            if len(calls) != 1:
                return await actual_sender(ws)
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                await release.wait()
            finally:
                finished.set()
        host._send_frames = blocked_first_sender
        server = TestServer(host.make_app())
        await server.start_server()
        host.port, host.running = server.port, True
        try:
            async with ClientSession() as client:
                first = await client.ws_connect(server.make_url(f"/ws?token={host.token}"))
                await first.receive_json()
                await asyncio.wait_for(entered.wait(), 1)
                host.controller.pose(1, 0, 0)
                self.assertTrue(host.arm()[0])
                await first.close()
                await asyncio.wait_for(cancelled.wait(), 1)
                self.assertFalse(finished.is_set())
                self.assertIsNone(host._ws)
                self.assertIsNone(host._sender)
                self.assertFalse(host.controller.connected)
                self.assertFalse(host.controller.armed)
                self.assertFalse(host._worker.active.is_set())
                connections = [event for event in events if event["event"] == "connection"]
                self.assertFalse(connections[-1]["connected"])
                async with client.get(server.make_url("/health")) as response:
                    self.assertFalse((await response.json())["connected"])
                async with client.ws_connect(server.make_url(f"/ws?token={host.token}&settingsSchema=2")) as fresh:
                    hello = await fresh.receive_json()
                    self.assertFalse(hello["mouseArmed"])
                    current_ws, current_sender = host._ws, host._sender
                    release.set()
                    await asyncio.wait_for(finished.wait(), 1)
                    await asyncio.sleep(.02)
                    self.assertIs(host._ws, current_ws)
                    self.assertIs(host._sender, current_sender)
                    self.assertTrue(host._settings_schema2)
                    self.assertTrue(host.controller.connected)
                    self.assertTrue(host._worker.active.is_set())
                    connections = [event for event in events if event["event"] == "connection"]
                    self.assertTrue(connections[-1]["connected"])
                    self.assertEqual(sink.moves, [])
        finally:
            release.set()
            await server.close()

    async def test_old_sender_failure_cannot_disarm_a_replacement_session(self):
        class Buffer:
            sequence = 0
            async def next(self, after):
                raise ConnectionError("old transport ended")
        class Socket:
            closed = False
            async def close(self, **kwargs):
                self.closed = True
        host = HostServer(SyntheticJpegSource(), RecordingInputSink(), settings=Settings(mode="fps"))
        host._buffer, host._ws = Buffer(), Socket()
        current = host._ws
        host.controller.set_connected(True)
        host.controller.pose(1, 0, 0)
        self.assertTrue(host.arm()[0])
        old = Socket()
        await host._send_frames(old)
        self.assertTrue(old.closed)
        self.assertFalse(current.closed)
        self.assertIs(host._ws, current)
        self.assertTrue(host.controller.connected)
        self.assertTrue(host.controller.armed)

    async def test_unresponsive_old_peer_cannot_keep_stream_or_input_alive_after_stop(self):
        sink, source = RecordingInputSink(), SyntheticJpegSource()
        host = HostServer(source, sink, settings=Settings(mode="fps"), host="127.0.0.1", port=free_port(),
                          capture_config=CaptureConfig(fps=5), usb_authorized=lambda: True)
        peer = None
        try:
            await asyncio.to_thread(host.start)
            old_token = host.token
            peer = await StandardWebSocketPeer.connect(URL(f"http://127.0.0.1:{host.port}/ws?token={old_token}"))
            await peer.next_json("hello")
            host.controller.pose(1, 0, 0)
            self.assertTrue(host.arm()[0])
            host.request_stop()
            self.assertFalse(host.running)
            self.assertFalse(host.controller.connected)
            self.assertFalse(host.controller.armed)
            host.controller.pose(2, .1, .1)
            # This raw peer never reads/responds to the server close frame.
            self.assertTrue(await asyncio.to_thread(host.stop, 4))
            self.assertEqual(sink.moves, [])
            self.assertIsNone(host._ws)
            self.assertIsNone(host._sender)
            self.assertFalse(host._worker.thread.is_alive())
            with socket.socket() as probe:
                self.assertNotEqual(probe.connect_ex(("127.0.0.1", host.port)), 0)
            await asyncio.to_thread(host.start)
            self.assertNotEqual(host.token, old_token)
            async with ClientSession() as client:
                async with client.get(f"http://127.0.0.1:{host.port}/health") as response:
                    state = await response.json()
                self.assertFalse(state["connected"])
                self.assertTrue(state["running"])
                async with client.ws_connect(f"http://127.0.0.1:{host.port}/ws?token={host.token}") as fresh:
                    hello = await fresh.receive_json()
                    self.assertFalse(hello["mouseArmed"])
                    self.assertTrue(host.controller.connected)
        finally:
            if peer:
                peer.writer.close()
                await peer.writer.wait_closed()
            await asyncio.to_thread(host.stop, 5)

    async def test_slow_capture_close_is_busy_after_worker_join_deadline_and_cannot_restart(self):
        entered, release = threading.Event(), threading.Event()
        class SlowClose(SyntheticJpegSource):
            def close(self):
                entered.set()
                release.wait(8)
                super().close()
        source = SlowClose()
        host = HostServer(source, RecordingInputSink(), host="127.0.0.1", port=free_port())
        try:
            await asyncio.to_thread(host.start)
            host.request_stop()
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            # CaptureWorker's historical 3-second join may return with a live
            # native source. Server completion must wait for its real lifetime.
            self.assertFalse(await asyncio.to_thread(host.stop, 3.2))
            self.assertTrue(host._worker.thread.is_alive())
            self.assertFalse(host.controller.connected)
            self.assertFalse(host.running)
            with self.assertRaisesRegex(RuntimeError, "still stopping"):
                host.start()
            with socket.socket() as probe:
                self.assertNotEqual(probe.connect_ex(("127.0.0.1", host.port)), 0)
            release.set()
            self.assertTrue(await asyncio.to_thread(host.stop, 3))
            self.assertTrue(source.closed)
            self.assertFalse(host._worker.thread.is_alive())
            self.assertIsNone(host._buffer.frame)
            await asyncio.to_thread(host.start)
            self.assertTrue(host.running)
        finally:
            release.set()
            await asyncio.to_thread(host.stop, 5)

    async def test_stopping_gate_revokes_bootstrap_new_ws_and_pending_frame(self):
        host = HostServer(SyntheticJpegSource(), RecordingInputSink(), usb_authorized=lambda: True)
        server = TestServer(host.make_app())
        await server.start_server()
        host.port, host.running = server.port, True
        class Socket:
            closed = False
            sent = []
            async def send_bytes(self, frame):
                self.sent.append(frame)
        ws = Socket()
        host._ws = ws
        sender = asyncio.create_task(host._send_frames(ws))
        await asyncio.sleep(0)
        try:
            host.request_stop()
            frame = replace(host.capture_source.read(host.capture_config), protected_content_masked=True)
            host._buffer.publish(frame)
            await sender
            self.assertEqual(ws.sent, [])
            host._ws = None
            async with ClientSession() as client:
                async with client.get(server.make_url("/usb-bootstrap")) as response:
                    self.assertEqual(response.status, 503)
                async with client.get(server.make_url(f"/ws?token={host.token}")) as response:
                    self.assertEqual(response.status, 503)
                async with client.get(server.make_url("/health")) as response:
                    value = await response.json()
                    self.assertEqual((value["connected"], value["running"], value["stopping"]), (False, False, True))
        finally:
            host._ws = None
            await server.close()


class Widget:
    def __init__(self):
        self.values = {}
    def configure(self, **values):
        self.values.update(values)


class GuiStopTests(unittest.TestCase):
    def test_rebuild_for_language_change_keeps_stop_busy_and_running_connect_available(self):
        window = HostWindow.__new__(HostWindow)
        window._stop_in_progress = True
        window.tr = lambda value, **kw: value
        window.root = SimpleNamespace(winfo_children=lambda: [], title=lambda *args: None)
        window.notebook = SimpleNamespace(select=lambda *args: None, index=lambda *args: 1)
        window.server = SimpleNamespace(running=False, token="000000", controller=SimpleNamespace(connected=False),
                    get_settings_snapshot=lambda: (Settings(), 0), get_capture_config=lambda: CaptureConfig())
        def build():
            for name in ("code_label", "start_button", "stop_button", "status", "stats"):
                setattr(window, name, Widget())
        window._build = build
        window._rebuild()
        self.assertEqual(window.start_button.values["state"], "disabled")
        self.assertEqual(window.stats.values["text"], "—")
        self.assertEqual(window.status.values["text"], "Stopping streaming; waiting for cleanup")
        window._stop_in_progress = False
        window.server.running = True
        window._rebuild()
        self.assertEqual(window.start_button.values["state"], "normal")
        self.assertEqual(window.stop_button.values["state"], "normal")

    def test_stop_is_immediate_but_reports_completion_only_after_cleanup(self):
        window = HostWindow.__new__(HostWindow)
        window._stop_in_progress, window._stop_generation = False, 0
        window.events = queue.SimpleQueue()
        window.tr = lambda value, **kw: value
        window._log = lambda value: None
        window.root = SimpleNamespace(after=lambda *args: None)
        for name in ("code_label", "start_button", "stop_button", "status", "stats"):
            setattr(window, name, Widget())
        calls, jobs = [], []
        window.server = SimpleNamespace(running=True, session_generation=1, controller=SimpleNamespace(connected=False),
                                         request_stop=lambda: calls.append("request"),
                                         stop=lambda: False)
        window.usb = SimpleNamespace(relay=SimpleNamespace(stop=lambda: calls.append("relay")))
        window.usb.cancel_connect = lambda: calls.append("cancel_phone")
        window.usb.request_stop_phone = lambda: calls.append("stop_phone")
        window.connection = SimpleNamespace(cancel=lambda: calls.append("cancel_ui"))
        class Thread:
            def __init__(self, target, **kw):
                self.target = target
            def start(self):
                jobs.append(self.target)
        with patch("vrization_host.gui.threading.Thread", Thread):
            window.stop()
            window.stop()
        self.assertEqual(calls, ["request", "stop_phone", "cancel_ui"])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(window.start_button.values["state"], "disabled")
        self.assertEqual(window.stats.values["text"], "—")
        jobs[0]()
        window.events.put({"event": "connection", "connected": False})
        window.events.put({"event": "stats", "width": 640, "height": 360, "fps": 60, "mbps": 12.8})
        window._pump()
        self.assertTrue(window._stop_in_progress)
        self.assertEqual(window.status.values["text"], "Stopping streaming; waiting for cleanup")
        self.assertEqual(window.stats.values["text"], "—")
        window.events.put({"event": "server", "running": False})
        window._pump()
        self.assertFalse(window._stop_in_progress)
        self.assertEqual(window.start_button.values["state"], "normal")
        # A delayed result from the completed stop cannot overwrite a new run.
        window.server.running = True
        window.status.configure(text="new run")
        window.events.put({"event": "stop_result", "complete": True, "generation": 1})
        window._pump()
        self.assertEqual(window.status.values["text"], "new run")
        window.server.controller.connected = True
        window.server.session_generation = 2
        window.events.put({"event": "stats", "session": 1, "width": 640, "height": 360, "fps": 60, "mbps": 12.8})
        window.events.put({"event": "connection", "session": 1, "connected": False})
        window._pump()
        self.assertEqual(window.stats.values["text"], "—")
        self.assertEqual(window.status.values["text"], "new run")
        window.events.put({"event": "stats", "session": 2, "width": 640, "height": 360, "fps": 60, "mbps": 12.8})
        window._pump()
        self.assertIn("60 FPS", window.stats.values["text"])
        window.server.controller.connected = False
        window.events.put({"event": "connection", "session": 2, "connected": False})
        window.events.put({"event": "stats", "session": 2, "width": 640, "height": 360, "fps": 60, "mbps": 12.8})
        window._pump()
        self.assertEqual(window.stats.values["text"], "—")


if __name__ == "__main__":
    unittest.main()
