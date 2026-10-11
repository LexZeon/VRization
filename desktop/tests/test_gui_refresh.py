"""Rebuild waits for complete cleanup; Stop supersedes pending refresh."""
import queue
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from vrization_host.gui import HostWindow


class GuiRefreshTests(unittest.TestCase):
    def fixture(self):
        window = HostWindow.__new__(HostWindow)
        window._stop_in_progress, window._stop_generation = False, 0
        window._refresh_after_stop = False
        window._refresh_cleanup_pending = False
        window.editor = None
        window.events = queue.SimpleQueue()
        window.tr = lambda value, **kw: value
        window._log, window._refresh_input_status = Mock(), Mock()
        window.root = SimpleNamespace(after=Mock())
        for name in ("code_label", "start_button", "stop_button", "status", "stats"):
            setattr(window, name, Mock())
        window.server = SimpleNamespace(request_stop=Mock(), stop=Mock(return_value=True),
            resume_control=Mock(), running=False, session_generation=1)
        window.usb = SimpleNamespace(request_stop_phone=Mock(), relay=SimpleNamespace(stop=Mock()))
        window.connection = SimpleNamespace(cancel=Mock())
        window.start = Mock()
        jobs = []
        class Thread:
            def __init__(self, target, **kw):
                self.target = target
            def start(self):
                jobs.append(self.target)
        return window, jobs, patch("vrization_host.gui.threading.Thread", Thread)

    def test_refresh_waits_for_stop_job_not_server_exit_and_does_not_resume_control(self):
        window, jobs, thread = self.fixture()
        with thread:
            self.assertTrue(window.refresh_connection())
            self.assertFalse(window.refresh_connection())
        window.events.put({"event":"server", "running":False})
        window._pump()
        self.assertTrue(window._stop_in_progress)
        window.start.assert_not_called()
        jobs[0]()
        window._pump()
        window.start.assert_called_once_with()
        self.assertFalse(window._stop_in_progress)
        self.assertFalse(window._refresh_after_stop)
        self.assertFalse(window._refresh_cleanup_pending)
        window.server.resume_control.assert_not_called()
        window.events.put({"event":"stop_result", "complete":True, "generation":1})
        window._pump()
        self.assertEqual(window.start.call_count, 1, "Late completion cannot start another session")

    def test_manual_stop_cancels_pending_refresh(self):
        window, jobs, thread = self.fixture()
        with thread:
            window.refresh_connection()
            window.stop()
        self.assertEqual(len(jobs), 1)
        self.assertFalse(window._refresh_after_stop)
        jobs[0]()
        window._pump()
        window.start.assert_not_called()
        window.server.request_stop.assert_called_once_with()

    def test_incomplete_cleanup_is_retried_before_refresh_restarts(self):
        window, jobs, thread = self.fixture()
        window.server.stop.side_effect = (False, True)
        with thread:
            window.refresh_connection()
        jobs[0]()
        self.assertEqual(window.server.stop.call_count, 2)
        window._pump()
        window.start.assert_called_once_with()

    def test_transient_relay_cleanup_failure_is_retried_before_refresh_restarts(self):
        window, jobs, thread = self.fixture()
        window.usb.relay.stop.side_effect = (OSError("Temporary relay close failure"), None)
        with thread:
            window.refresh_connection()
        jobs[0]()
        self.assertEqual(window.usb.relay.stop.call_count, 2)
        window.server.stop.assert_called_once_with()
        window._pump()
        window.start.assert_called_once_with()

    def test_cancel_refresh_still_retires_cleanup_after_an_early_server_exit_and_relay_error(self):
        window, jobs, thread = self.fixture()
        window.usb.relay.stop.side_effect = (OSError("Temporary relay close failure"), None)
        with thread:
            window.refresh_connection()
            window.events.put({"event":"server", "running":False})
            window._pump()
            self.assertTrue(window._stop_in_progress)
            window.stop()
            window.events.put({"event":"server", "running":False})
            window._pump()
            self.assertTrue(window._stop_in_progress, "Cancelling restart cannot retire still-running cleanup")
            self.assertTrue(window._refresh_cleanup_pending)
        jobs[0]()
        window._pump()
        self.assertFalse(window._stop_in_progress)
        self.assertFalse(window._refresh_after_stop)
        self.assertEqual(window.usb.relay.stop.call_count, 2)
        window.start.assert_not_called()

    def test_refresh_keeps_an_open_editor_until_user_saves_or_discards(self):
        window, jobs, thread = self.fixture()
        window.editor = Mock()
        with thread:
            self.assertFalse(window.refresh_connection())
        window.editor.discard.assert_not_called()
        window.server.request_stop.assert_not_called()
        self.assertEqual(jobs, [])

