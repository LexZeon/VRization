"""Original isolated package gates: no network, executable, driver or runtime use."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import package_steamvr as package
import verify_android_release as verifier


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
        (self.native / "drivers/vrization_phone/driver.vrdrivermanifest").write_text(json.dumps({
            "name": "vrization_phone", "directory": "", "alwaysActivate": True,
            "resourceOnly": False, "hmd_presence": []}), encoding="utf-8")
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


    def test_hash_matching_invalid_or_always_present_manifest_is_not_packaged(self):
        name = "drivers/vrization_phone/driver.vrdrivermanifest"
        path = self.native / name
        value = json.loads(path.read_text(encoding="utf-8"))
        for presence in (["VRizationPhone"], ["*.*"]):
            with self.subTest(presence=presence):
                value["hmd_presence"] = presence
                path.write_text(json.dumps(value), encoding="utf-8")
                self.report["files"][name] = self.digest(path)
                self.write_report()
                with self.assertRaisesRegex(ValueError, "explicit empty list"):
                    package.windows()
                self.assertFalse((self.out / "VRization-SteamVR-Windows-x64.zip").exists())


class SteamVrAndroidPackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="vrization-android-package-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.out = self.root / "artifacts/steamvr/release"
        self.apk = self.root / "android/steamvr-app/build/outputs/apk/steamvr/debug/steamvr-app-steamvr-debug.apk"
        self.aar = self.root / "android/vr-core/build/outputs/aar/vr-core-debug.aar"
        for path, data in ((self.apk, b"inert APK fixture"), (self.aar, b"inert AAR fixture")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.apksigner = self.root / "sdk with spaces/apksigner.exe"
        self.apksigner.parent.mkdir()
        self.apksigner.write_bytes(b"inert verifier fixture - never executed")
        self.fingerprint = verifier.read_fingerprint(verifier.CANONICAL_CERTIFICATE)
        self.valid_output = self.signer_output(self.fingerprint)
        for replacement in (patch.object(package, "ROOT", self.root), patch.object(package, "OUT", self.out)):
            replacement.start()
            self.addCleanup(replacement.stop)

    @staticmethod
    def signer_output(fingerprint):
        return f"Number of signers: 1\nSigner #1 certificate SHA-256 digest: {fingerprint}\n"

    def test_wrong_signer_preserves_existing_public_apk_and_aar(self):
        self.out.mkdir(parents=True)
        assets = (self.out / "VRization-SteamVR-Android-debug.apk", self.out / "VRization-SteamVR-vr-core.aar")
        for path in assets:
            path.write_bytes(b"verified prior publication sentinel")
        wrong = "0" * 64 if self.fingerprint != "0" * 64 else "1" * 64
        result = subprocess.CompletedProcess([], 0, self.signer_output(wrong), "")
        with patch.object(verifier.subprocess, "run", return_value=result), patch.object(package.shutil, "copyfile") as copy:
            with self.assertRaisesRegex(ValueError, "public upgrade identity"):
                package.android(self.apksigner)
            copy.assert_not_called()
        for path in assets:
            self.assertEqual(path.read_bytes(), b"verified prior publication sentinel")

    def test_invalid_verifier_or_output_cannot_create_public_android_assets(self):
        cases = (
            ("missing verifier", self.root / "missing-apksigner.exe", 0, self.valid_output, FileNotFoundError),
            ("verifier rejects signature", self.apksigner, 1, self.valid_output, ValueError),
            ("missing certificate output", self.apksigner, 0, "", ValueError),
            ("ambiguous signer output", self.apksigner, 0, self.valid_output + self.valid_output, ValueError),
        )
        for name, tool, code, output, error in cases:
            with self.subTest(name=name):
                result = subprocess.CompletedProcess([], code, output, "")
                with patch.object(verifier.subprocess, "run", return_value=result) as run, patch.object(package.shutil, "copyfile") as copy:
                    with self.assertRaises(error):
                        package.android(tool)
                    copy.assert_not_called()
                    if error is FileNotFoundError:
                        run.assert_not_called()
                self.assertFalse(self.out.exists())

    def test_full_and_android_only_require_explicit_verifier_before_any_packaging(self):
        for args in ([], ["--android-only"]):
            with self.subTest(args=args), patch.object(sys, "argv", ["package_steamvr.py", *args]), patch.object(sys, "stderr", io.StringIO()), patch.object(package, "windows") as windows, patch.object(package, "source") as source, patch.object(package.shutil, "copyfile") as copy:
                with self.assertRaises(SystemExit) as stopped:
                    package.main()
                self.assertEqual(stopped.exception.code, 2)
                windows.assert_not_called()
                source.assert_not_called()
                copy.assert_not_called()
                self.assertFalse(self.out.exists())

    def test_verified_android_only_copies_exact_assets_after_official_verification(self):
        events = []
        real_copy = shutil.copyfile

        def verified(command, **options):
            events.append("verify")
            return subprocess.CompletedProcess(command, 0, self.valid_output, "")

        def copy(source, destination):
            events.append(destination.name)
            return real_copy(source, destination)

        with patch.object(sys, "argv", ["package_steamvr.py", "--android-only", "--apksigner", str(self.apksigner)]), patch.object(verifier.subprocess, "run", side_effect=verified) as run, patch.object(package.shutil, "copyfile", side_effect=copy) as copies:
            package.main()
            run.assert_called_once_with([str(self.apksigner.resolve()), "verify", "--verbose", "--print-certs", str(self.apk.resolve())], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False, timeout=60)
            self.assertEqual(copies.call_args_list, [
                unittest.mock.call(self.apk, self.out / "VRization-SteamVR-Android-debug.apk"),
                unittest.mock.call(self.aar, self.out / "VRization-SteamVR-vr-core.aar"),
            ])
        self.assertEqual(events, ["verify", "VRization-SteamVR-Android-debug.apk", "VRization-SteamVR-vr-core.aar"])
        self.assertEqual((self.out / "VRization-SteamVR-Android-debug.apk").read_bytes(), self.apk.read_bytes())
        self.assertEqual((self.out / "VRization-SteamVR-vr-core.aar").read_bytes(), self.aar.read_bytes())
        self.assertEqual({path.name for path in self.out.iterdir()}, {"VRization-SteamVR-Android-debug.apk", "VRization-SteamVR-vr-core.aar"})

    def test_windows_and_source_only_remain_independent_of_android_sdk(self):
        for flag, expected in (("--windows-only", "windows"), ("--source-only", "source")):
            with self.subTest(flag=flag), patch.object(sys, "argv", ["package_steamvr.py", flag]), patch.object(package, "windows") as windows, patch.object(package, "source") as source, patch.object(package, "verify_apk") as verify:
                package.main()
                (windows if expected == "windows" else source).assert_called_once_with()
                (source if expected == "windows" else windows).assert_not_called()
                verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
