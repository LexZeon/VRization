"""Isolated preferences and mocked widgets; no display, device or native runtime."""

from dataclasses import replace
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from vrization_host.capture import CaptureConfig
from vrization_host.gui import HostWindow
from vrization_host.profiles import initial_capture
from vrization_host.protocol import Settings
from vrization_host.storage import load_preferences, preference_path, save_preferences
from vrization_steamvr.app import PhoneWindow
from vrization_steamvr.profiles import (BALANCED, CUSTOM, HMD_PROFILES, LOW_LATENCY,
    SHARPER, apply_hmd_profile, hmd_capture_profile, initial_hmd_capture,
    limit_hmd_capture, profile_label)


class ProfilePolicyTests(unittest.TestCase):
    def test_all_presets_are_bounded_stereo_targets_and_preserve_display_selection(self):
        original=CaptureConfig(monitor=3,region=(12,20,800,600),width=960,fps=45,quality=85)
        for name, expected in ((BALANCED,(1280,60,75)),(SHARPER,(1920,60,80)),(LOW_LATENCY,(640,60,45))):
            with self.subTest(name=name):
                config=apply_hmd_profile(original,name)
                self.assertEqual((config.width,config.fps,config.quality),expected)
                self.assertGreaterEqual(config.fps,30)
                self.assertEqual((config.monitor,config.region),(original.monitor,original.region))
                self.assertEqual(hmd_capture_profile(config),name)
        self.assertEqual((original.width,original.fps,original.quality),(960,45,85))

    def test_new_hmd_users_get_balanced_but_every_saved_capture_is_preserved(self):
        original=CaptureConfig()
        self.assertEqual(hmd_capture_profile(initial_hmd_capture(original,False)),BALANCED)
        for config in (original,CaptureConfig(width=1600,fps=45,quality=85),apply_hmd_profile(original,SHARPER)):
            with self.subTest(config=config):
                self.assertIs(initial_hmd_capture(config,True),config)
        self.assertEqual((original.width,original.quality),(640,45))

    def test_native_limits_apply_without_changing_jpeg_quality_or_monitor(self):
        config=limit_hmd_capture(CaptureConfig(monitor=4,region=(1,2,640,360),width=3840,fps=5,quality=95))
        self.assertEqual((config.width,config.fps,config.quality,config.monitor,config.region),(1920,30,95,4,None))

    def test_custom_label_requires_all_three_targets_to_match(self):
        config=apply_hmd_profile(CaptureConfig(),BALANCED)
        for changed in (replace(config,width=960),replace(config,fps=45),replace(config,quality=80)):
            with self.subTest(changed=changed):self.assertEqual(hmd_capture_profile(changed),CUSTOM)
        self.assertIs(apply_hmd_profile(config,CUSTOM),config)
        self.assertEqual(profile_label(BALANCED,"en"),BALANCED)
        self.assertEqual(profile_label(BALANCED,"zh"),"均衡 · 1280 / 60 FPS / Q75")
        self.assertEqual(profile_label(SHARPER,"zh"),"更清晰 · 1920 / 60 FPS / Q80")
        self.assertEqual(profile_label(CUSTOM,"zh"),"自定义")


class ProfileWindowTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{"VRIZATION_PROFILE_DIRECTORY":self.directory.name})
        self.env.start()

    def tearDown(self):
        self.env.stop();self.directory.cleanup()

    def initialize(self,route,stored=None):
        if stored is not None:save_preferences(Settings(mode="fps_enhanced"),stored)
        def shared_init(window,root,initial_monitor=None,*,server_factory,**kwargs):
            window.settings,window.config=load_preferences()
            window.config=initial_capture(window.config,preference_path().exists())
            if initial_monitor is not None:window.config=replace(window.config,monitor=initial_monitor,region=None)
            window.server=server_factory(settings=window.settings,capture_config=window.config)
        with patch.object(HostWindow,"__init__",shared_init), \
             patch("vrization_steamvr.app.PreviewHost") as server, \
             patch("vrization_steamvr.app.MirrorCaptureSource"):
            window=PhoneWindow(Mock(),route,monitor=3)
            return window,server.call_args.kwargs

    def test_initial_factory_receives_balanced_before_build_or_capture_starts(self):
        window,kwargs=self.initialize("steamvr-phone")
        self.assertEqual(hmd_capture_profile(kwargs["capture_config"]),BALANCED)
        self.assertEqual(kwargs["capture_config"].monitor,3)
        self.assertEqual(window.config,kwargs["capture_config"])
        self.assertFalse(preference_path().exists(),"Opening the panel must not rewrite preferences")

    def test_explicit_old_and_custom_hmd_settings_are_not_migrated(self):
        for stored in (CaptureConfig(),CaptureConfig(width=1600,fps=45,quality=85)):
            with self.subTest(stored=stored):
                before=None
                save_preferences(Settings(mode="fps_enhanced"),stored)
                before=preference_path().read_bytes()
                window,kwargs=self.initialize("steamvr-phone",stored)
                self.assertEqual((window.config.width,window.config.fps,window.config.quality),
                                 (stored.width,stored.fps,stored.quality))
                self.assertEqual(kwargs["settings"].mode,"fps_enhanced")
                self.assertEqual(preference_path().read_bytes(),before)

    def test_direct_factory_keeps_original_low_latency_default_and_saved_capture(self):
        window,kwargs=self.initialize("direct-phone")
        self.assertEqual((window.config.width,window.config.fps,window.config.quality),(640,60,45))
        self.assertNotIn("capture_source",kwargs)
        saved=CaptureConfig(width=960,fps=30,quality=60)
        window,_=self.initialize("direct-phone",saved)
        self.assertEqual((window.config.width,window.config.fps,window.config.quality),(960,30,60))

    def fake_window(self,route="steamvr-phone"):
        window=PhoneWindow.__new__(PhoneWindow)
        window.route=route;window.root=Mock();window.language="zh";window.editor=None
        window.config=CaptureConfig(monitor=2,width=1600,fps=45,quality=85)
        current=[window.config];settings=[Settings(mode="fps_enhanced",scale=.6)]
        window.server=Mock()
        window.server.get_capture_config.side_effect=lambda:current[0]
        window.server.set_capture_config.side_effect=lambda config:current.__setitem__(0,config)
        window.server.get_settings_snapshot.side_effect=lambda:(settings[0],0)
        window.server.update_settings.side_effect=lambda value:settings.__setitem__(0,settings[0].update(value))
        window.profile_names=list(HMD_PROFILES)+[CUSTOM];window.profile=Mock()
        window.capture_vars={key:Mock() for key in ("width","fps","quality")}
        for key,var in window.capture_vars.items():
            var.get.return_value=str(getattr(window.config,key))
            var.set.side_effect=lambda value,var=var:setattr(var.get,"return_value",value)
        window._save_later=Mock();window._log=Mock();window._rebuild=Mock()
        window.usb=Mock();window.usb_preferences={"enabled":False,"preferred_serial":"old", "adb_path":"retained-adb.exe"}
        window._save_usb=Mock();window._save_input=Mock();window.hotkey_available=True
        window.input_preferences={"gyro_control_enabled":False}
        window.save_job=None
        return window

    def test_preset_selection_updates_all_targets_then_saves_only_current_preferences(self):
        window=self.fake_window();window.profile.current.return_value=window.profile_names.index(SHARPER)
        window.change_profile()
        self.assertEqual((window.config.width,window.config.fps,window.config.quality),(1920,60,80))
        window.profile.current.assert_called_with(window.profile_names.index(SHARPER))
        window._save_later.assert_called_once()
        window._save()
        self.assertEqual(load_preferences()[1],window.config)
        self.assertEqual(load_preferences()[0].mode,"fps_enhanced")
        window.server.resume_control.assert_not_called();window.server.update_settings.assert_not_called()

    def test_manual_targets_show_custom_and_invalid_changes_are_atomic(self):
        window=self.fake_window();window.capture_vars["width"].get.return_value="1280"
        self.assertTrue(window.apply_capture())
        window.profile.current.assert_called_with(window.profile_names.index(CUSTOM))
        previous=window.config;window.server.reset_mock();window._save_later.reset_mock()
        window.capture_vars["quality"].get.return_value="96"
        with patch("vrization_steamvr.app.messagebox.showerror") as error:
            self.assertFalse(window.apply_capture());error.assert_called_once()
        self.assertEqual(window.config,previous)
        window.server.set_capture_config.assert_not_called();window._save_later.assert_not_called()

    def test_shared_reset_saves_balanced_before_rebuild_and_keeps_input_paused(self):
        window=self.fake_window();paused=[False]
        window.server.disarm.side_effect=lambda reason:paused.__setitem__(0,True)
        def check_rebuild(index):
            self.assertEqual(hmd_capture_profile(load_preferences()[1]),BALANCED)
            self.assertTrue(paused[0])
        window._rebuild.side_effect=check_rebuild
        with patch("vrization_host.gui.save_language") as language:
            window.reset_all();language.assert_called_once_with("en")
        stored_settings,stored=load_preferences()
        self.assertEqual((stored.width,stored.fps,stored.quality,stored.monitor,stored.region),(1280,60,75,2,None))
        self.assertEqual(stored_settings,Settings())
        self.assertEqual(window.usb_preferences["adb_path"],"retained-adb.exe")
        self.assertEqual(window.input_preferences,{"gyro_control_enabled":True})
        self.assertFalse(window._hmd_reset_capture)
        window.server.resume_control.assert_not_called()
        # Later ordinary saves must keep a manually selected custom goal.
        window.config=CaptureConfig(width=1600,fps=45,quality=85)
        window._save()
        self.assertEqual(load_preferences()[1],window.config)

    def test_direct_reset_still_uses_original_defaults_and_display_region(self):
        window=self.fake_window("direct-phone")
        selection=replace(window.config,region=(10,20,640,360))
        window.server.get_capture_config.side_effect=lambda:selection
        with patch("vrization_host.gui.save_language"):window.reset_all()
        stored=load_preferences()[1]
        self.assertEqual((stored.width,stored.fps,stored.quality),(640,60,45))
        self.assertEqual((stored.monitor,stored.region),(2,selection.region))
        self.assertFalse(hasattr(window,"_hmd_reset_capture"))
        window.server.resume_control.assert_not_called()

    def test_hmd_capture_widgets_offer_profiles_with_actual_custom_selection_and_stereo_width(self):
        class Widget:
            def __init__(self,children=(),row=None,**values):self.children=children;self.row=row;self.values=values
            def winfo_children(self):return self.children
            def grid_info(self):return {"row":self.row}
            def configure(self,**values):self.values.update(values)
            def cget(self,key):return self.values.get(key)
            def current(self,index):self.index=index
            def grid_remove(self):self.removed=True
        class Label(Widget):pass
        class LabelFrame(Widget):pass
        class Combobox(Widget):pass
        window=self.fake_window();window._paragraph=Mock();window.use_region=Mock()
        window.monitor=Combobox();window.profile=Combobox()
        labels=[Label(row=0),Label(row=4)];region=LabelFrame(row=3)
        width_label=Label(text=window.tr("最长输出边"))
        width_box=Combobox(textvariable=str(window.capture_vars["width"]))
        fps_box=Combobox(textvariable=str(window.capture_vars["fps"]))
        quality=Widget(children=(Widget(children=(width_label,width_box)),Widget(children=(fps_box,))))
        tab=Widget(children=(*labels,region,quality))
        with patch.object(HostWindow,"_capture_tab"), \
             patch("vrization_steamvr.app.ttk.Label",Label), \
             patch("vrization_steamvr.app.ttk.LabelFrame",LabelFrame), \
             patch("vrization_steamvr.app.ttk.Combobox",Combobox):
            window._capture_tab(tab)
        self.assertEqual(window.profile.values["state"],"readonly")
        self.assertEqual(window.profile.values["values"],[profile_label(name,"zh") for name in window.profile_names])
        self.assertEqual(window.profile.index,window.profile_names.index(CUSTOM))
        self.assertEqual(width_label.cget("text"),"双眼总宽度")
        self.assertEqual(width_box.cget("values"),(640,960,1280,1600,1920))
        self.assertEqual(fps_box.cget("values"),(30,45,60))
        self.assertTrue(region.removed)
        self.assertIn("默认使用均衡",labels[1].cget("text"))
        self.assertEqual((window.config.width,window.config.fps,window.config.quality),(1600,45,85))

    def test_fit_reset_explanation_is_hmd_specific_in_both_languages_only(self):
        class Label:
            def __init__(self,text):self.text=text
            def cget(self,key):return self.text
            def configure(self,**values):self.text=values["text"]
        original="Reset restores the default picture, low latency, English, automatic USB and enabled gyro mouse. Your selected display/region and installed ADB path stay selected."
        for language in ("en","zh"):
            with self.subTest(language=language):
                window=self.fake_window();window.language=language
                label=Label(window.tr(original));tab=Mock();tab.winfo_children.return_value=[label]
                with patch.object(HostWindow,"_fit_tab"),patch("vrization_steamvr.app.ttk.Label",Label):
                    window._fit_tab(tab)
                self.assertIn("Balanced" if language=="en" else "均衡",label.text)
                self.assertIn("paused" if language=="en" else "暂停",label.text)
        window=self.fake_window("direct-phone");label=Label(window.tr(original))
        tab=Mock();tab.winfo_children.return_value=[label]
        with patch.object(HostWindow,"_fit_tab"),patch("vrization_steamvr.app.ttk.Label",Label):window._fit_tab(tab)
        self.assertEqual(label.text,window.tr(original))


if __name__ == "__main__":
    unittest.main()
