"""Deterministic capture pacing checks; no screen access or global timer changes."""
import threading
import unittest
from unittest.mock import patch

from vrization_host.capture import CaptureConfig, CaptureWorker, Frame
from vrization_host.server import HostServer


class CapturePacingTests(unittest.TestCase):
    def run_worker(self, costs, *, fps=60, oversleep=.001, stop_on_sleep=False):
        now, starts, sleeps = [0.0], [], []

        class Source:
            closed = False

            def read(source, config):
                starts.append(now[0])
                now[0] += costs[len(starts) - 1]
                if len(starts) == len(costs):
                    worker.stop_event.set()
                return Frame(b"jpeg", 1, 1, now[0])

            def close(source):
                source.closed = True

        class Loop:
            def call_soon_threadsafe(loop, callback):
                pass  # The real loop runs this later, after the handoff lock.

        class Buffer:
            def publish(buffer, frame):
                pass

        source = Source()
        worker = CaptureWorker(source, lambda: CaptureConfig(fps=fps), Loop(), Buffer(),
                               lambda error: self.fail(error))
        worker.active.set()

        def sleep(delay):
            self.assertGreater(delay, 0)
            self.assertLessEqual(delay, 1 / fps + 1e-10)
            sleeps.append(delay)
            now[0] += delay + oversleep
            if stop_on_sleep:
                worker.stop_event.set()

        with patch("vrization_host.capture.time.perf_counter", side_effect=lambda: now[0]), \
                patch("vrization_host.capture.time.sleep", side_effect=sleep), \
                patch("vrization_host.capture.time.monotonic", side_effect=AssertionError("coarse clock")):
            worker._run()
        self.assertTrue(source.closed)
        return starts, sleeps

    def test_wakeup_lateness_does_not_accumulate_or_exceed_target_rate(self):
        starts, sleeps = self.run_worker([.003] * 20)
        self.assertEqual(len(sleeps), 19)
        self.assertAlmostEqual(starts[1], 1 / 60 + .001)
        self.assertAlmostEqual(starts[-1], 19 / 60 + .001)
        for first, second in zip(starts, starts[1:]):
            self.assertGreaterEqual(second - first, 1 / 60 - 1e-10)

    def test_slow_capture_does_not_wait_again_or_build_a_catchup_burst(self):
        starts, sleeps = self.run_worker([.022] * 10)
        self.assertEqual(sleeps, [])
        for first, second in zip(starts, starts[1:]):
            self.assertAlmostEqual(second - first, .022)

        starts, _ = self.run_worker([.003, .003, .040, .003, .003, .003])
        for first, second in zip(starts, starts[1:]):
            self.assertGreaterEqual(second - first, 1 / 60 - 1e-10)

    def test_stop_during_sleep_does_not_capture_another_frame(self):
        for fps in (5, 60):
            starts, sleeps = self.run_worker([.003] * 10, fps=fps, stop_on_sleep=True)
            self.assertEqual(len(starts), 1)
            self.assertEqual(len(sleeps), 1)

    def test_stopping_an_idle_worker_never_calls_capture(self):
        class Source:
            closed = False

            def read(source, config):
                self.fail("capture called while stopping idle worker")

            def close(source):
                source.closed = True

        source = Source()
        worker = CaptureWorker(source, lambda: CaptureConfig(), None, None, self.fail)
        worker.start()
        worker.stop()
        self.assertFalse(worker.thread.is_alive())
        self.assertTrue(source.closed)


class SenderStatisticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_masked_notice_is_once_per_viewer_and_does_not_change_frame_bytes(self):
        events = []
        masked = Frame(b"os-masked-jpeg", 640, 360, 0, protected_content_masked=True)
        class Buffer:
            sequence = 0
            async def next(buffer, after):
                buffer.sequence += 1
                return buffer.sequence, masked
        class Socket:
            closed = False
            def __init__(socket):
                socket.sent = []
            async def send_bytes(socket, data):
                socket.sent.append(data)
                socket.closed = len(socket.sent) == 3
        host = HostServer.__new__(HostServer)
        host._buffer, host.on_event = Buffer(), events.append
        host.session_generation, host._stopping = 1, threading.Event()
        for session in (1, 2):
            host.session_generation = session
            socket = Socket()
            host._ws = socket
            await host._send_frames(socket)
            self.assertEqual(socket.sent, [masked.jpeg] * 3)
        notices = [event for event in events if event["event"] == "capture_masked"]
        self.assertEqual([event["session"] for event in notices], [1, 2])

    async def test_host_component_timings_exclude_static_refresh_age(self):
        now, events = [0.0], []
        first = Frame(b"one", 640, 360, 0, capture_ms=3, ready_at=.1)
        last = Frame(b"two", 640, 360, 0, capture_ms=5, ready_at=.9)

        class Buffer:
            sequence = 0
            async def next(buffer, after):
                now[0] = (.105, .5, .91)[buffer.sequence]
                frame = (first, first, last)[buffer.sequence]
                buffer.sequence += 1
                return buffer.sequence, frame

        class Socket:
            closed = False
            sends = 0
            async def send_bytes(socket, data):
                now[0] = (.12, .52, 1.2)[socket.sends]
                socket.sends += 1
                socket.closed = socket.sends == 3

        host = HostServer.__new__(HostServer)
        host._buffer, host.on_event = Buffer(), events.append
        host.session_generation, host._stopping = 1, threading.Event()
        socket = Socket()
        host._ws = socket
        with patch("vrization_host.server.time.perf_counter", side_effect=lambda: now[0]):
            await host._send_frames(socket)
        self.assertEqual(len(events), 1)
        self.assertAlmostEqual(events[0]["captureMs"], 4)
        self.assertAlmostEqual(events[0]["queueMs"], 7.5)
        self.assertAlmostEqual(events[0]["sendMs"], (15 + 20 + 290) / 3)
        self.assertAlmostEqual(events[0]["fps"], 3 / 1.2)

    async def test_send_rate_uses_precise_elapsed_time_and_completed_sends(self):
        now, events = [0.0], []

        class Buffer:
            sequence = 0

            async def next(buffer, after):
                buffer.sequence += 1
                return buffer.sequence, Frame(b"jpeg", 960, 540, 0)

        class Socket:
            closed = False
            sends = 0

            async def send_bytes(socket, data):
                socket.sends += 1
                now[0] = (.25, .75, 1.25)[socket.sends - 1]
                socket.closed = socket.sends == 3

        host = HostServer.__new__(HostServer)
        host._buffer = Buffer()
        host.on_event = events.append
        socket = Socket()
        host.session_generation, host._stopping, host._ws = 1, threading.Event(), socket
        with patch("vrization_host.server.time.perf_counter", side_effect=lambda: now[0]):
            await host._send_frames(socket)
        self.assertEqual(len(events), 1)
        stats = events[0]
        self.assertEqual(stats["event"], "stats")
        self.assertAlmostEqual(stats["fps"], 3 / 1.25)
        self.assertAlmostEqual(stats["mbps"], 3 * 4 * 8 / 1.25 / 1_000_000)
        self.assertEqual((stats["width"], stats["height"]), (960, 540))


if __name__ == "__main__":
    unittest.main()
