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
from vrization_host.storage import (default_preferences, load_preferences, save_preferences,
                                    load_usb_preferences, save_usb_preferences)
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
                owner.commit_editor(Settings(scale=.66, offsetX=.1, offsetY=-.2, eyeSeparation=.13))
            saved, config = load_preferences(path)
        self.assertEqual(saved, replace(host.settings, scale=.66, offsetX=.1, offsetY=-.2, eyeSeparation=.13))
        self.assertEqual(saved.eyeSeparation, .13)
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

    def test_pc_save_keeps_signed_joined_spacing_in_host_and_local_preferences(self):
        host = HostServer(capture_source=Mock(), input_sink=Mock())
        owner = HostWindow.__new__(HostWindow)
        owner.server, owner.config = host, CaptureConfig()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "joined.json"
            with patch("vrization_host.gui.save_preferences",
                       side_effect=lambda settings, config: save_preferences(settings, config, path)):
                owner.commit_editor(Settings(scale=.5, eyeSeparation=-.75))
            self.assertEqual(load_preferences(path)[0].eyeSeparation, -.75)
        self.assertEqual(host.get_settings_snapshot()[1], 1)
        self.assertEqual(host.settings.eyeSeparation, -.75)

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

    def test_reset_action_persists_all_defaults_and_never_changes_capture_identity(self):
        owner = HostWindow.__new__(HostWindow)
        owner.server = HostServer(capture_source=Mock(), input_sink=Mock())
        owner.server.update_settings({"mode": "fps", "scale": .6, "distortion": .4, "invertY": True})
        old = CaptureConfig(monitor=2, region=(-1280, 50, 960, 540), width=1920, quality=95, fps=30)
        owner.server.set_capture_config(old)
        owner.editor = SimpleNamespace(discard=Mock())
        owner.usb_preferences = {"enabled": False, "preferred_serial": "test-device", "adb_path": "custom/adb.exe"}
        owner.usb = SimpleNamespace(preferred_serial="test-device", set_enabled=Mock())
        owner._rebuild = Mock(); owner._log = Mock(); owner.language = "zh"
        with tempfile.TemporaryDirectory() as directory:
            path, usb_path = Path(directory) / "prefs.json", Path(directory) / "usb.json"
            with patch("vrization_host.gui.save_preferences",
                       side_effect=lambda settings, config: save_preferences(settings, config, path)), \
                 patch("vrization_host.gui.save_usb_preferences",
                       side_effect=lambda preferences: save_usb_preferences(preferences, usb_path)), \
                 patch("vrization_host.gui.save_language") as language:
                owner.reset_all()
                language.assert_called_once_with("en")
            self.assertEqual(load_preferences(path), default_preferences(old))
            self.assertEqual(load_usb_preferences(usb_path),
                             {"enabled": True, "preferred_serial": "", "adb_path": "custom/adb.exe"})
        self.assertEqual(owner.language, "en")
        owner.editor.discard.assert_called_once()
        owner.usb.set_enabled.assert_called_once_with(True)
        owner._rebuild.assert_called_once_with(0)
        self.assertFalse(owner.server.controller.armed)

    def test_editor_entry_stops_existing_authorization_and_blocks_arm_button(self):
        owner = HostWindow.__new__(HostWindow)
        owner.server = HostServer(capture_source=Mock(), input_sink=Mock())
        owner.server.update_settings({"mode": "fps"})
        owner.server.controller.set_connected(True)
        owner.server.controller.pose(0, 0, 0)
        self.assertTrue(owner.server.arm()[0])
        owner.editor = None
        owner.arm_var = Mock()
        with patch("vrization_host.gui.HeadsetEditor") as editor:
            owner.open_editor()
            editor.assert_called_once_with(owner, owner.server.settings)
        self.assertFalse(owner.server.controller.armed)
        owner.toggle_arm()
        owner.arm_var.set.assert_called_once_with(False)
        self.assertFalse(owner.server.controller.armed)

    def pointer_editor(self):
        editor = HeadsetEditor.__new__(HeadsetEditor)
        editor.transaction = EditTransaction(Settings())
        editor.geometry = lambda: (0, 0, 1000, 450)
        editor.image = None
        editor.gesture = None
        editor.draw = Mock()
        return editor

    def test_left_eye_drag_follows_pointer_and_mirrors_other_eye_without_accumulation(self):
        editor = self.pointer_editor()
        before = [editor.bounds(eye) for eye in (0, 1)]
        editor.begin(SimpleNamespace(x=242.5, y=225))
        for _ in range(3):
            editor.move(SimpleNamespace(x=217.5, y=202.5))
        self.assertAlmostEqual(editor.draft.offsetX, 0)
        self.assertAlmostEqual(editor.draft.eyeSeparation, .13)
        self.assertAlmostEqual(editor.draft.offsetY, .1)
        for eye in (0, 1):
            after = editor.bounds(eye)
            self.assertAlmostEqual(after[0] - before[eye][0], -25 if eye == 0 else 25)
            self.assertAlmostEqual(after[1] - before[eye][1], -22.5)
            self.assertAlmostEqual(after[2] - after[0], before[eye][2] - before[eye][0])

    def test_right_eye_drag_outwards_follows_pointer_and_mirrors_left_eye(self):
        editor = self.pointer_editor()
        before = [editor.bounds(eye) for eye in (0, 1)]
        editor.begin(SimpleNamespace(x=757.5, y=225))
        editor.move(SimpleNamespace(x=782.5, y=225))
        self.assertAlmostEqual(editor.draft.eyeSeparation, .13)
        self.assertEqual(editor.draft.offsetX, 0)
        for eye in (0, 1):
            after = editor.bounds(eye)
            self.assertAlmostEqual(after[0] - before[eye][0], -25 if eye == 0 else 25)

    def test_right_eye_corner_resize_keeps_centers_and_uses_gesture_start_aspect(self):
        editor = self.pointer_editor()
        before = [editor.bounds(eye) for eye in (0, 1)]
        # 16:9 image fits a 500x450 eye: fit=(1,.625), scale=.85.
        editor.begin(SimpleNamespace(x=970, y=105.46875))
        editor.image = SimpleNamespace(width=9, height=16)  # arriving frame cannot alter this drag
        editor.move(SimpleNamespace(x=995, y=91.40625))
        self.assertAlmostEqual(editor.draft.scale, .95)
        editor.image = None
        for eye in (0, 1):
            after = editor.bounds(eye)
            self.assertAlmostEqual((after[0] + after[2]) / 2, (before[eye][0] + before[eye][2]) / 2)
            self.assertAlmostEqual((after[1] + after[3]) / 2, (before[eye][1] + before[eye][3]) / 2)

    def test_small_eyes_can_drag_inward_to_the_same_pixel_with_offset_centered(self):
        for eye in (0, 1):
            with self.subTest(eye=eye):
                editor = self.pointer_editor()
                editor.transaction = EditTransaction(Settings(scale=.5, offsetX=.2))
                left, top, right, bottom = editor.bounds(eye)
                start_x = (left + right) / 2
                editor.begin(SimpleNamespace(x=start_x, y=(top + bottom) / 2))
                editor.move(SimpleNamespace(x=start_x + (600 if eye == 0 else -600), y=225))
                self.assertAlmostEqual(editor.draft.eyeSeparation, -.5)
                self.assertAlmostEqual(editor.draft.offsetX, 0)
                self.assertAlmostEqual(editor.bounds(0)[2], 500)
                self.assertAlmostEqual(editor.bounds(1)[0], 500)

    def test_resizing_joined_small_eyes_preserves_the_seam_boundary(self):
        editor = self.pointer_editor()
        editor.transaction = EditTransaction(Settings(scale=.5, eyeSeparation=-.5))
        left, top, right, bottom = editor.bounds(1)
        editor.begin(SimpleNamespace(x=right, y=top))
        editor.move(SimpleNamespace(x=right + 25, y=top - 14.0625))
        self.assertAlmostEqual(editor.draft.scale, .6)
        self.assertAlmostEqual(editor.draft.eyeSeparation, -.4)
        self.assertAlmostEqual(editor.bounds(0)[2], 500)
        self.assertAlmostEqual(editor.bounds(1)[0], 500)


if __name__ == "__main__":
    unittest.main()
