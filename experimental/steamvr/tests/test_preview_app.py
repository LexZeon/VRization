"""Mocked widget construction checks; importing the preview never opens a window."""
import unittest
from unittest.mock import Mock, patch
from vrization_host.protocol import Settings
from vrization_steamvr.app import PhoneWindow, usb_factory


class PreviewAppTests(unittest.TestCase):
    def test_steamvr_game_tab_retains_variables_needed_by_the_shared_settings_pump(self):
        window=PhoneWindow.__new__(PhoneWindow)
        window.route="steamvr-phone";window.language="en";window.settings=Settings(mode="fps_enhanced")
        window.input_preferences={"gyro_control_enabled":True};window.server=Mock();window.root=Mock()
        window._paragraph=Mock();window._refresh_input_status=Mock();window._save_later=Mock()
        window.mode=Mock();window.settings_revision=0;window.setting_vars={};window.syncing=False
        with patch("vrization_steamvr.app.tk.BooleanVar",side_effect=lambda **kwargs:Mock()), \
             patch("vrization_steamvr.app.ttk.Label",side_effect=lambda *a,**k:Mock()), \
             patch("vrization_steamvr.app.ttk.Checkbutton",side_effect=lambda *a,**k:Mock()), \
             patch("vrization_steamvr.app.ttk.Button",side_effect=lambda *a,**k:Mock()):
            window._game_tab(Mock())
        changed=Settings(mode="fps_enhanced",scale=.6,invertY=True)
        self.assertTrue(window._apply_settings_event({"revision":1,"settings":changed.to_dict()}))
        window.invert.set.assert_called_once_with(True)
        self.assertEqual(window.settings.mode,"fps_enhanced")
        window.server.resume_control.assert_not_called()
        window._save_later.assert_called_once()

    def test_usb_factory_targets_only_the_experimental_phone_and_ports(self):
        with patch("vrization_steamvr.app.UsbManager") as manager:
            usb_factory("host","observer",adb_path="unchanged")
        values=manager.call_args.kwargs
        self.assertEqual(values["android_video_port"],18775)
        self.assertEqual(values["android_control_port"],18774)
        self.assertEqual(values["ios_video_port"],18776)
        self.assertEqual(values["ios_control_port"],18777)
        self.assertEqual(values["android_component"],"org.vrization.steamvr/org.vrization.app.MainActivity")
        self.assertEqual(values["adb_path"],"unchanged")

    def test_steamvr_capture_uses_native_limits_and_preserves_the_saved_mode(self):
        from vrization_host.capture import CaptureConfig
        window=PhoneWindow.__new__(PhoneWindow);window.route="steamvr-phone";window.root=Mock()
        window.server=Mock();window.config=CaptureConfig(monitor=2,region=(0,0,640,360))
        window.capture_vars={key:Mock() for key in ("width","fps","quality")}
        for key,value in {"width":"3840","fps":"5","quality":"45"}.items():
            window.capture_vars[key].get.return_value=value
        window._save_later=Mock()
        self.assertTrue(window.apply_capture())
        self.assertEqual((window.config.width,window.config.fps,window.config.region),(1920,30,None))
        self.assertEqual(window.config.monitor,2)
        window.server.update_settings.assert_not_called()


if __name__ == "__main__":
    unittest.main()
