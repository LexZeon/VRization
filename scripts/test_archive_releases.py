"""Focused offline regressions: fixtures are never real executable files."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import archive_releases as archive


def release_fixture(tag, include_windows=True):
    payloads = {}
    assets = []
    if include_windows:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as bundle:
            bundle.writestr("VRization-Host.exe", b"fixture only; never executed: " + tag.encode())
            bundle.writestr("README.md", "fixture documentation")
        name = "VRization-Windows-x64.zip"
        payloads[f"https://fixture.invalid/{tag}/{name}"] = output.getvalue()
        assets.append({"name": name, "browser_download_url": f"https://fixture.invalid/{tag}/{name}"})
        manifest = hashlib.sha256(output.getvalue()).hexdigest() + "  " + name + "\n"
    else:
        manifest = ""
    manifest_url = f"https://fixture.invalid/{tag}/SHA256SUMS.txt"
    payloads[manifest_url] = manifest.encode()
    assets.append({"name": "SHA256SUMS.txt", "browser_download_url": manifest_url})
    return {"tag_name": tag, "html_url": f"https://fixture.invalid/{tag}", "assets": assets}, payloads


def prepare(root, tag="v9.9.9-alpha", include_windows=True):
    release, payloads = release_fixture(tag, include_windows)
    with patch.object(archive, "fetch", lambda url: io.BytesIO(payloads[url])), \
         contextlib.redirect_stdout(io.StringIO()):
        return archive.prepare_release(root, release)


class ArchiveTests(unittest.TestCase):
    def test_unpublished_cache_is_neither_extracted_copied_nor_made_latest(self):
        with tempfile.TemporaryDirectory(prefix="vrization-archive-test-") as directory:
            root = Path(directory).resolve()
            downloads = root / "versions/v9.9.9-alpha/downloads"
            downloads.mkdir(parents=True)
            with zipfile.ZipFile(downloads / "VRization-Windows-x64.zip", "w") as bundle:
                bundle.writestr("VRization-Host.exe", "unpublished stale fixture")
            (downloads / "VRization-Android-debug.apk").write_text("unpublished stale fixture")
            folder = prepare(root, include_windows=False)
            self.assertFalse((folder / "Windows").exists())
            self.assertFalse((folder / "Android").exists())
            self.assertEqual(json.loads((folder / ".vrization-archive.json").read_text())["verifiedAssets"], [])
            with self.assertRaisesRegex(ValueError, "no verified Windows executable"):
                archive.publish_latest(root, folder)
            self.assertFalse((root / "latest").exists())
            self.assertFalse((root / "OPEN-ME.html").exists())
            self.assertEqual(list(root.glob(".latest-staging-*")), [])

    def test_verified_windows_launchers_and_history_are_preserved(self):
        with tempfile.TemporaryDirectory(prefix="vrization-archive-test-") as directory:
            root = Path(directory).resolve()
            old = prepare(root, "v1.0.0-alpha")
            (old / "Windows/unpublished-old.dll").write_text("stale fixture")
            (old / "Android").mkdir()
            (old / "Android/VRization-Android-debug.apk").write_text("stale fixture")
            (old / "downloads/VRization-Android-debug.apk").write_text("stale fixture")
            archive.publish_latest(root, old)
            self.assertFalse((root / "latest/Windows/unpublished-old.dll").exists())
            self.assertFalse((root / "latest/Android").exists())
            self.assertFalse((root / "latest/downloads/VRization-Android-debug.apk").exists())
            self.assertTrue((old / "Windows/unpublished-old.dll").exists())
            old_exe = (root / "latest/Windows/VRization-Host.exe").read_bytes()
            current = prepare(root, "v2.0.0-alpha")
            archive.publish_latest(root, current)
            self.assertTrue((root / "latest/Start-Windows.bat").is_file())
            self.assertTrue((root / "latest/Start-on-second-monitor.bat").is_file())
            self.assertTrue((root / "OPEN-ME.html").is_file())
            self.assertNotEqual((root / "latest/Windows/VRization-Host.exe").read_bytes(), old_exe)
            backups = list(root.glob("previous-latest-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / "Windows/VRization-Host.exe").read_bytes(), old_exe)
            self.assertTrue((old / "downloads/VRization-Windows-x64.zip").is_file())

    def test_unmanaged_latest_and_changed_executable_are_not_published(self):
        for tamper in (False, True):
            with self.subTest(tamper=tamper), tempfile.TemporaryDirectory(prefix="vrization-archive-test-") as directory:
                root = Path(directory).resolve()
                folder = prepare(root)
                if tamper:
                    (folder / "Windows/VRization-Host.exe").write_text("changed fixture")
                    reason = "no verified Windows executable"
                else:
                    latest = root / "latest"
                    latest.mkdir()
                    (latest / "user-file.txt").write_text("retain me")
                    reason = "not managed"
                with self.assertRaisesRegex(ValueError, reason):
                    archive.publish_latest(root, folder)
                self.assertFalse((root / "OPEN-ME.html").exists())
                self.assertEqual(list(root.glob(".latest-staging-*")), [])
                if not tamper:
                    self.assertEqual((root / "latest/user-file.txt").read_text(), "retain me")

    def test_launchers_conditionally_scope_separately_installed_sdk_without_bundling_it(self):
        with tempfile.TemporaryDirectory(prefix="vrization-archive-test-") as directory:
            root = Path(directory).resolve()
            sdk = root / "tools/android-sdk/platform-tools/adb.exe"
            sdk.parent.mkdir(parents=True)
            sdk.write_text("fixture tool; never executed")
            folder = prepare(root)
            archive.publish_latest(root, folder)
            for filename, monitor in (("Start-Windows.bat", ""), ("Start-on-second-monitor.bat", " --monitor 2")):
                with self.subTest(filename=filename):
                    launcher = (root / "latest" / filename).read_text(encoding="ascii")
                    self.assertIn('if exist "%~dp0..\\tools\\android-sdk\\platform-tools\\adb.exe" (', launcher)
                    self.assertIn('set "ANDROID_HOME=%~dp0..\\tools\\android-sdk"', launcher)
                    self.assertIn('set "ANDROID_SDK_ROOT=%~dp0..\\tools\\android-sdk"', launcher)
                    self.assertLess(launcher.index("setlocal"), launcher.index("ANDROID_HOME"))
                    self.assertLess(launcher.index("ANDROID_SDK_ROOT"), launcher.index('start ""'))
                    self.assertIn('start "" "%~dp0Windows\\VRization-Host.exe"' + monitor + '\nendlocal\n', launcher)
                    self.assertNotIn("setx ", launcher.lower())
                    self.assertNotIn(" /i ", launcher.lower())
            self.assertEqual(sdk.read_text(), "fixture tool; never executed")
            self.assertFalse((root / "latest/tools").exists())
            self.assertFalse((folder / "tools").exists())


if __name__ == "__main__":
    unittest.main()
