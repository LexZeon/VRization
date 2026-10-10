"""Original isolated package gates: no network, executable, driver or runtime use."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import package_steamvr as package


class SteamVrPackageTests(unittest.TestCase):
    required = (
        "native/VRization-SteamVR-Mirror.exe", "native/VRization-SteamVR-Overlay.exe",
        "native/VRization-SteamVR-IPC.dll", "native/openvr_api.dll",
        "drivers/vrization_phone/bin/win64/driver_vrization_phone.dll",
        "drivers/vrization_phone/driver.vrdrivermanifest",
        "drivers/vrization_phone/resources/settings/default.vrsettings",
        "native/licenses/OpenVR-LICENSE.txt", "native/licenses/VRization-MIT.txt",
        "native/README.md", "native/licenses/README.md", "native-build-report.json",
    )

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="vrization-package-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.native = self.root / "artifacts/steamvr/native-bundle"
        self.out = self.root / "artifacts/steamvr/release"
        self.out.mkdir(parents=True)
        for name in self.required[:-1]:
            target = self.native / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(("original inert fixture " + name).encode())
        (self.native / "native/README.md").write_text("[Licenses](licenses/README.md)\n")
        (self.native / "native/licenses/README.md").write_text("[Native](../README.md)\n")
        executable = self.root / "artifacts/steamvr/windows-dist/VRization-SteamVR.exe"
        executable.parent.mkdir(parents=True)
        executable.write_bytes(b"inert freezer fixture - never executed")
        self.stable = self.root / "artifacts/release/VRization-Windows-x64.zip"
        self.stable.parent.mkdir(parents=True)
        self.stable.write_bytes(b"historical stable sentinel")
        self.license = self.root / "LICENSE"
        self.license.write_text("original fixture license\n")
        self.page = self.root / "experimental/steamvr/README.md"
        self.page.parent.mkdir(parents=True)
        self.page.write_text("[Project license](../../LICENSE)\n")
        self.pins = {
            "bin/win64/openvr_api.dll": self.digest(self.native / "native/openvr_api.dll"),
            "LICENSE": self.digest(self.native / "native/licenses/OpenVR-LICENSE.txt"),
        }
        self.report = {
            "sdkCommit": "fixture-commit", "sdkPins": self.pins,
            "ctestExecuted": True, "configuration": "Release",
            "files": {name: self.digest(self.native / name) for name in self.required[:-1]},
        }
        self.write_report()
        self.patches = (
            patch.object(package, "ROOT", self.root), patch.object(package, "OUT", self.out),
            patch.object(package, "COMMIT", "fixture-commit"), patch.object(package, "PINS", self.pins),
            patch.object(package, "tracked_files", return_value=[self.license, self.page]),
        )
        for replacement in self.patches:
            replacement.start()
            self.addCleanup(replacement.stop)

    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def write_report(self):
        (self.native / "native-build-report.json").write_text(json.dumps(self.report))

    def test_complete_bundle_contains_native_driver_notices_and_offline_links(self):
        package.windows()
        with zipfile.ZipFile(self.out / "VRization-SteamVR-Windows-x64.zip") as archive:
            names = set(archive.namelist())
            self.assertTrue(set(self.required).issubset(names))
            self.assertIn("VRization-SteamVR.exe", names)
            self.assertIn("experimental/steamvr/README.md", names)
            self.assertIn("LICENSE", names)
            launcher = archive.read("Start-SteamVR-Preview.bat").decode()
            self.assertIn('start "" "%~dp0VRization-SteamVR.exe"', launcher)
            self.assertNotIn("adddriver", launcher)
            self.assertNotIn("removedriver", launcher)
            self.assertIn(" --monitor 2", archive.read("Start-SteamVR-Preview-second-monitor.bat").decode())
        self.assertEqual(self.stable.read_bytes(), b"historical stable sentinel")

    def test_each_required_native_file_is_mandatory_before_archive_creation(self):
        for name in self.required:
            with self.subTest(name=name):
                path = self.native / name
                content = path.read_bytes()
                path.unlink()
                try:
                    with self.assertRaisesRegex(FileNotFoundError, "Incomplete native bundle"):
                        package.windows()
                    self.assertFalse((self.out / "VRization-SteamVR-Windows-x64.zip").exists())
                finally:
                    path.write_bytes(content)

    def test_any_payload_change_must_match_its_native_build_report(self):
        for name in self.required[:-1]:
            with self.subTest(name=name):
                path = self.native / name
                content = path.read_bytes()
                path.write_bytes(content + b" changed")
                try:
                    with self.assertRaisesRegex(ValueError, "Native report does not match"):
                        package.windows()
                finally:
                    path.write_bytes(content)

    def test_sdk_identity_release_and_executed_ctest_are_required(self):
        for key, value in (("sdkCommit", "wrong"), ("sdkPins", {}),
                           ("ctestExecuted", False), ("ctestExecuted", 1),
                           ("configuration", "Debug")):
            with self.subTest(key=key, value=value):
                original = self.report[key]
                self.report[key] = value
                self.write_report()
                try:
                    with self.assertRaisesRegex(ValueError, "passing Release build"):
                        package.windows()
                finally:
                    self.report[key] = original
                    self.write_report()

    def test_upstream_pins_reject_changes_even_if_the_report_hash_is_rewritten(self):
        for name in ("native/openvr_api.dll", "native/licenses/OpenVR-LICENSE.txt"):
            with self.subTest(name=name):
                path = self.native / name
                content = path.read_bytes()
                path.write_bytes(content + b" changed")
                self.report["files"][name] = self.digest(path)
                self.write_report()
                try:
                    with self.assertRaisesRegex(ValueError, "Upstream binary/license changed"):
                        package.windows()
                finally:
                    path.write_bytes(content)
                    self.report["files"][name] = self.digest(path)
                    self.write_report()

    def test_unexpected_native_binaries_are_preserved_and_rejected(self):
        for suffix in (".dll", ".EXE", ".lib"):
            with self.subTest(suffix=suffix):
                extra = self.native / ("native/unexpected" + suffix)
                extra.write_bytes(b"unreviewed inert fixture")
                try:
                    with self.assertRaisesRegex(ValueError, "Unexpected native binary"):
                        package.windows()
                    self.assertEqual(extra.read_bytes(), b"unreviewed inert fixture")
                finally:
                    extra.unlink()

    def test_package_rejects_missing_targets_in_staged_markdown(self):
        name = "native/README.md"
        path = self.native / name
        path.write_text("[Missing offline guide](missing.md)\n")
        self.report["files"][name] = self.digest(path)
        self.write_report()
        with self.assertRaisesRegex(ValueError, "links to missing native/missing.md"):
            package.windows()


if __name__ == "__main__":
    unittest.main()
