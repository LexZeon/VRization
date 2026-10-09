"""A failed capture must end input even when phone poses are still live."""
import asyncio
import threading
import unittest

from vrization_host.server import HostServer


class CaptureFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_armed_session_disarms_immediately_on_capture_failure(self):
        failed = threading.Event()
        events = []

        class Source:
            closed = False

            def read(self, config):
                raise ValueError("Display layout changed")

            def close(self):
                self.closed = True

        class Sink:
            moves = []

            def move(self, dx, dy):
                self.moves.append((dx, dy))

        def observe(event):
            events.append(event)
            if event["event"] == "error":
                failed.set()

        source, sink = Source(), Sink()
        host = HostServer(capture_source=source, input_sink=sink, on_event=observe)
        await host._startup(None)
        try:
            host.update_settings({"mode": "fps"})
            host.controller.set_connected(True)
            host.controller.last_pose_time = host.controller.clock()
            self.assertTrue(host.arm()[0])
            host._worker.active.set()
            for _ in range(40):
                if failed.is_set():
                    break
                await asyncio.sleep(.005)
            self.assertTrue(failed.is_set())
            self.assertFalse(host.controller.armed)
            self.assertTrue(any(e.get("reason") == "capture unavailable" for e in events))
            self.assertEqual(sink.moves, [])
        finally:
            await host._shutdown(None)
            await host._cleanup(None)
        self.assertTrue(source.closed)
