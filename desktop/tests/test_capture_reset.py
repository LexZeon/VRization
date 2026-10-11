"""Capture reconnect resets on its owning thread and drops pre-reset frames."""
import queue
import threading
import unittest

from vrization_host.capture import CaptureConfig, CaptureWorker, Frame


class CaptureResetTests(unittest.TestCase):
    def test_overlapping_reset_receipts_complete_only_after_their_own_close(self):
        entered, release = threading.Event(), threading.Event()
        completed = []
        class Source:
            closes = 0
            def close(source):
                source.closes += 1
                if source.closes == 1:
                    entered.set()
                    if not release.wait(3):raise RuntimeError("Fixture release missing")
            def read(source, config):
                return None
        source=Source()
        def reset_done():
            completed.append(worker.completed_reset_generation)
            if len(completed)==2:worker.stop_event.set()
        worker=CaptureWorker(source,lambda:CaptureConfig(),None,None,self.fail,on_source_reset=reset_done)
        self.assertEqual(worker.request_source_reset(),1)
        worker.active.set();worker.start()
        try:
            self.assertTrue(entered.wait(3))
            self.assertEqual(worker.request_source_reset(),2)
            self.assertEqual(worker.completed_reset_generation,0)
        finally:
            release.set();worker.thread.join(3)
            if worker.thread.is_alive():worker.stop()
        self.assertEqual(completed,[1,2])
        self.assertFalse(worker.thread.is_alive())

    def test_reset_during_a_read_drops_old_frame_and_closes_on_the_worker_thread(self):
        entered, release = threading.Event(), threading.Event()
        callbacks, published, calls = queue.SimpleQueue(), [], []

        class Source:
            reads = 0
            def read(source, config):
                source.reads += 1
                calls.append(("read", threading.get_ident()))
                if source.reads == 1:
                    entered.set()
                    if not release.wait(3):
                        raise RuntimeError("Fixture release missing")
                    return Frame(b"old", 1, 1, 0)
                worker.stop_event.set()
                return Frame(b"new", 1, 1, 1)
            def close(source):
                calls.append(("close", threading.get_ident()))

        class Loop:
            def call_soon_threadsafe(loop, callback):
                callbacks.put(callback)
        class Buffer:
            def publish(buffer, frame):
                published.append(frame.jpeg)

        failures = []
        source = Source()
        worker = CaptureWorker(source, lambda: CaptureConfig(), Loop(), Buffer(), failures.append,
            on_source_reset=lambda: calls.append(("reset", threading.get_ident())))
        worker.active.set()
        worker.start()
        try:
            self.assertTrue(entered.wait(3))
            self.assertTrue(worker.request_source_reset())
        finally:
            release.set()
            worker.thread.join(3)
            if worker.thread.is_alive():
                worker.stop()
        self.assertFalse(worker.thread.is_alive())
        while not callbacks.empty():
            callbacks.get()()
        self.assertEqual(failures, [])
        self.assertEqual(published, [b"new"])
        self.assertEqual([name for name, _ in calls], ["read", "close", "reset", "read", "close"])
        self.assertEqual({identity for _, identity in calls}, {worker.thread.ident})
        self.assertFalse(worker.request_source_reset(), "A stopped worker cannot accept recovery")

    def test_stop_during_reset_close_cannot_start_a_replacement_source(self):
        entered, release = threading.Event(), threading.Event()
        reads, resets = [], []
        class Source:
            closes = 0
            def read(source, config):
                reads.append(config)
                raise AssertionError("Stop during close must not read a new source")
            def close(source):
                source.closes += 1
                if source.closes == 1:
                    entered.set()
                    if not release.wait(3):
                        raise RuntimeError("Fixture release missing")
        source = Source()
        worker = CaptureWorker(source, lambda: CaptureConfig(), None, None, self.fail,
            on_source_reset=lambda: resets.append(True))
        self.assertTrue(worker.request_source_reset())
        worker.active.set()
        worker.start()
        try:
            self.assertTrue(entered.wait(3))
            worker.stop_event.set()
        finally:
            release.set()
            worker.thread.join(3)
            if worker.thread.is_alive():
                worker.stop()
        self.assertFalse(worker.thread.is_alive())
        self.assertEqual(reads, [])
        self.assertEqual(resets, [])
        self.assertEqual(source.closes, 2)

