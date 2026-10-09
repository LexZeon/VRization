"""Editor commit/persistence boundaries without native APIs or GUI automation."""

from dataclasses import replace
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from vrization_host.capture import CaptureConfig, Frame
from vrization_host.gui import HostWindow
from vrization_host.protocol import Settings
from vrization_host.server import HostServer
from vrization_host.storage import default_preferences, load_preferences, save_preferences
from vrization_host.view_edit import EditTransaction
from vrization_host.view_editor import HeadsetEditor


class EditorIntegrationTests(unittest.TestCase):
    def make_editor(self):
        editor = HeadsetEditor.__new__(HeadsetEditor)
        editor.transaction = EditTransaction(Settings(mode="fps", distortion=.25))
        editor.transaction.preview("pan", .1, -.2, 16 / 9, 10 / 9)
        editor.closed = False
        editor._close = Mock(side_effect=lambda: setattr(editor, "closed", True))
        editor.owner = SimpleNamespace(commit_editor=Mock())
        return editor

    def test_save_applies_one_complete_draft_even_on_duplicate_click(self):
        editor = self.make_editor()
        expected = editor.draft
        editor.save()
        editor.save()
        editor.owner.commit_editor.assert_called_once_with(expected)
        self.assertFalse(editor.transaction.active)

    def test_discard_and_window_close_never_send_or_persist_preview(self):
        editor = self.make_editor()
        editor.discard()
        editor.discard()
        self.assertEqual(editor.draft, editor.transaction.entry)
        editor.owner.commit_editor.assert_not_called()
        editor._close.assert_called_once()

    def test_commit_preserves_phone_changes_outside_fit_and_persists_exact_result(self):
        host = HostServer(capture_source=Mock(), input_sink=Mock())
        host.update_settings({"mode": "fps", "distortion": .3, "sensitivity": 2200})
        owner = HostWindow.__new__(HostWindow)
        owner.server = host
        owner.config = CaptureConfig(monitor=2, region=(20, 30, 640, 360))
        owner.save_job = None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs.json"
            with patch("vrization_host.gui.save_preferences",
                       side_effect=lambda settings, config: save_preferences(settings, config, path)):
                owner.commit_editor(Settings(scale=.66, offsetX=.1, offsetY=-.2))
            saved, config = load_preferences(path)
        self.assertEqual(saved, replace(host.settings, scale=.66, offsetX=.1, offsetY=-.2))
        self.assertEqual((saved.mode, saved.distortion, saved.sensitivity), ("fps", .3, 2200))
        self.assertEqual(host.get_settings_snapshot()[1], 2)  # one settings send/commit
        self.assertEqual(config, owner.config)
        self.assertFalse(host.controller.armed)

    def test_reset_defaults_keeps_explicit_capture_selection_and_survives_reload(self):
        old = CaptureConfig(monitor=2, region=(-1280, 100, 960, 540), width=1920, fps=30, quality=95)
        settings, config = default_preferences(old)
        self.assertEqual(settings, Settings())
        self.assertEqual(config, CaptureConfig(monitor=old.monitor, region=old.region))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prefs.json"
            save_preferences(settings, config, path)
            self.assertEqual(load_preferences(path), (Settings(), config))

    def test_local_preview_reads_owned_frame_without_invoking_capture(self):
        source = Mock()
        host = HostServer(capture_source=source, input_sink=Mock())
        frame = Frame(b"owned", 640, 360, 1)
        host._buffer = SimpleNamespace(frame=frame)
        self.assertIsNone(host.get_latest_frame())
        host.running = True
        self.assertIs(host.get_latest_frame(), frame)
        source.read.assert_not_called()
        host.running = False
        self.assertIsNone(host.get_latest_frame())


if __name__ == "__main__":
    unittest.main()
