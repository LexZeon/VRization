"""Read-only diagnostic entry tests; no actual SDK, device or GUI is opened."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from vrization_host import usb_diagnostics as diagnostic
from vrization_host._version import __version__
from vrization_host.usb import AndroidDevice


class DiagnosticTests(unittest.TestCase):
    def test_missing_sdk_is_a_complete_redacted_report_not_an_exception(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"LOCALAPPDATA": directory}, clear=True), \
             patch("vrization_host.usb.sys.frozen", False, create=True), \
             patch.object(diagnostic, "AdbReverse", side_effect=AssertionError("no tool to execute")):
            report = diagnostic.collect_usb_diagnostics()
            self.assertTrue(report["diagnostic_complete"])
            self.assertTrue(report["read_only"])
            self.assertFalse(report["adb_found"])
            self.assertEqual(report["version"], __version__)
            self.assertFalse(report["device_scan_complete"])
            self.assertNotIn(directory, json.dumps(report))

    def test_portable_candidate_explains_legacy_failure_without_exposing_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            sdk = base / "tools/android-sdk/platform-tools/adb.exe"
            sdk.parent.mkdir(parents=True); sdk.touch()
            executable = base / "latest/Windows/VRization-Host.exe"
            for launcher_env in (False, True):
                environment = {"LOCALAPPDATA": str(base / "empty-appdata")}
                if launcher_env:
                    environment.update(ANDROID_HOME=str(sdk.parents[1]), ANDROID_SDK_ROOT=str(sdk.parents[1]))
                with self.subTest(launcher_env=launcher_env), patch.dict(os.environ, environment, clear=True), \
                     patch("vrization_host.usb.sys.frozen", True, create=True), \
                     patch("vrization_host.usb.sys.executable", str(executable)), \
                     patch.object(diagnostic, "AdbReverse") as adapter:
                    adapter.return_value.command.return_value = "Android Debug Bridge version 1.0.41"
                    adapter.return_value.devices.return_value = []
                    report = diagnostic.collect_usb_diagnostics()
                    self.assertTrue(report["frozen"])
                    self.assertTrue(report["adb_found"])
                    self.assertFalse(report["legacy_adb_found"])
                    self.assertEqual(report["sdk_source"], "android_home" if launcher_env else "portable_archive")
                    self.assertEqual(report["launcher_sdk_environment"], launcher_env)
                    self.assertNotIn(directory, json.dumps(report))
                    adapter.return_value.ensure.assert_not_called()
                    adapter.return_value.release.assert_not_called()

    def test_preferences_and_device_counts_are_independent_of_secrets_and_usb_enable(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            sdk = base / "private-selected/adb.exe"
            sdk.parent.mkdir(); sdk.touch()
            preferences = base / "VRization/usb.json"
            preferences.parent.mkdir()
            payload = {"enabled": False, "adb_path": str(sdk), "preferred_serial": "PRIVATE-SERIAL",
                       "token": "SECRET-TOKEN"}
            preferences.write_text(json.dumps(payload))
            with patch.dict(os.environ, {"LOCALAPPDATA": directory}, clear=True), \
                 patch("vrization_host.usb.sys.frozen", False, create=True), \
                 patch.object(diagnostic, "AdbReverse") as adapter:
                adapter.return_value.command.return_value = "Android Debug Bridge version 1.0.41\nInstalled as " + str(sdk)
                adapter.return_value.devices.return_value = [AndroidDevice("PRIVATE-SERIAL", "device", True),
                    AndroidDevice("PRIVATE-UNAUTHORIZED", "unauthorized", False), AndroidDevice("PRIVATE-OFFLINE", "offline", True)]
                report = diagnostic.collect_usb_diagnostics()
                self.assertFalse(report["preferences"]["enabled"])
                self.assertTrue(report["preferences"]["explicit_configured"])
                self.assertTrue(report["preferences"]["preferred_device_configured"])
                self.assertEqual(report["sdk_source"], "explicit")
                self.assertEqual(report["legacy_sdk_source"], "explicit")
                self.assertEqual(report["adb_version"], "1.0.41")
                self.assertEqual((report["authorized_physical_count"], report["physical_usb_count"],
                                  report["unauthorized_count"], report["observed_device_count"]), (1, 2, 1, 3))
                text = json.dumps(report)
                for secret in (directory, "PRIVATE-SERIAL", "PRIVATE-UNAUTHORIZED", "PRIVATE-OFFLINE", "SECRET-TOKEN"):
                    self.assertNotIn(secret, text)
                adapter.return_value.command.assert_called_once_with("version")
                adapter.return_value.ensure.assert_not_called()
                adapter.return_value.release.assert_not_called()
                self.assertEqual(json.loads(preferences.read_text()), payload)

    def test_failures_are_redacted_and_still_write_requested_json(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            with patch.object(diagnostic, "collect_usb_diagnostics", side_effect=RuntimeError("SECRET-TOKEN/private/path")):
                self.assertEqual(diagnostic.main(["--usb-diagnostics", str(output)]), 0)
            report = json.loads(output.read_text())
            self.assertEqual(report["errors"], [{"stage": "diagnostic", "code": "RuntimeError"}])
            self.assertFalse(report["diagnostic_complete"])
            self.assertNotIn("SECRET", output.read_text())

    def test_actual_adapter_uses_devnull_and_reports_physical_proof_failure_without_mapping(self):
        calls = []

        def runner(command, **kwargs):
            self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
            self.assertTrue(kwargs["capture_output"])
            args = command[1:]
            calls.append(args)
            if args == ["version"]:
                output = "Android Debug Bridge version 1.0.41"
            elif args == ["devices", "-l"]:
                output = "PRIVATE-SERIAL device model:Phone\n"
            elif args == ["-s", "PRIVATE-SERIAL", "get-devpath"]:
                output = "unknown\n"
            else:
                self.fail("Unexpected mutating ADB command")
            return SimpleNamespace(returncode=0, stdout=output, stderr="")

        with tempfile.TemporaryDirectory() as directory:
            sdk = Path(directory) / "Android/Sdk/platform-tools/adb.exe"
            sdk.parent.mkdir(parents=True); sdk.touch()
            with patch.dict(os.environ, {"LOCALAPPDATA": directory}, clear=True), \
                 patch("vrization_host.usb.sys.frozen", False, create=True), \
                 patch("vrization_host.usb.subprocess.run", side_effect=runner), \
                 patch("vrization_host.usb.windows_usb_instance_ids", side_effect=OSError("PRIVATE-SERIAL/privatepath")):
                report = diagnostic.collect_usb_diagnostics()
                self.assertTrue(report["adb_list_complete"])
                self.assertEqual(report["adb_listed_authorized_count"], 1)
                self.assertEqual(report["authorized_physical_count"], 0)
                self.assertIn({"stage": "usb_physical_proof", "code": "OSError"}, report["errors"])
                self.assertEqual(calls, [["version"], ["devices", "-l"], ["-s", "PRIVATE-SERIAL", "get-devpath"]])
                self.assertNotIn("PRIVATE-SERIAL", json.dumps(report))

    def test_appdata_virtualization_detection_outputs_only_a_boolean(self):
        self.assertTrue(diagnostic._virtualized(Path("C:/Users/private/AppData/Local/Packages/OpenAI.Codex_id/LocalCache/Local")))
        self.assertFalse(diagnostic._virtualized(Path("C:/Users/private/AppData/Local")))

    def test_source_entry_cold_start_cannot_import_gui_capture_or_mouse(self):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "cold-entry.json"
            environment = dict(os.environ)
            environment.update(LOCALAPPDATA=directory, ANDROID_HOME="", ANDROID_SDK_ROOT="",
                               PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
            result = subprocess.run([sys.executable, "-m", "vrization_host", "--usb-diagnostics", str(report_path)],
                                    env=environment, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=15,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(report_path.read_text())
            self.assertEqual(report["forbidden_runtime_imports"], [])
            self.assertFalse(report["frozen"])
            self.assertTrue(report["diagnostic_complete"])
            self.assertFalse(report["adb_found"])

    def test_lazy_package_preserves_original_public_embedding_objects(self):
        import vrization_host
        from vrization_host.input import InputSink, PoseController
        from vrization_host.capture import CaptureConfig
        self.assertIs(vrization_host.InputSink, InputSink)
        self.assertIs(vrization_host.PoseController, PoseController)
        self.assertIs(vrization_host.CaptureConfig, CaptureConfig)
        self.assertIn("HostServer", dir(vrization_host))
        with self.assertRaises(AttributeError):
            _ = vrization_host.unknown_public_member


if __name__ == "__main__":
    unittest.main()
