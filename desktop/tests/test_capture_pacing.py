"""Deterministic capture pacing checks; no screen access or global timer changes."""
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
