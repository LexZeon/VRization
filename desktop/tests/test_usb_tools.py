"""Offline installer regressions; fake ZIPs and widgets, no executable or USB calls."""
import hashlib
import os
from pathlib import Path
import queue
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from vrization_host import usb_tools
from vrization_host.gui import HostWindow
from vrization_host.i18n import translate


FILES = {
    "platform-tools/adb.exe": b"fixture: never execute",
    "platform-tools/AdbWinApi.dll": b"fixture dll one",
    "platform-tools/AdbWinUsbApi.dll": b"fixture dll two",
    "platform-tools/source.properties": b"Pkg.UserSrc=false\r\nPkg.Revision=37.0.1\r\n",
    "platform-tools/NOTICE.txt": b"Original upstream notices\nAll copyright text stays intact.\n",
    "platform-tools/other-tool.exe": b"full package retained",
}


def package(path, files=None, extras=()):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as output:
        output.writestr("platform-tools/", b"")
        for name, content in (FILES if files is None else files).items():
            output.writestr(name, content)
        for entry, content in extras:
            if isinstance(entry, str):
                raw_name = entry
                entry = zipfile.ZipInfo(raw_name)
                entry.filename = entry.orig_filename = raw_name
            output.writestr(entry, content)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class UsbToolsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.zip = self.base / "download.zip"
        self.sdk = self.base / "chosen/tools/android-sdk"
        self.digest = package(self.zip)

    def tearDown(self):
        self.temporary.cleanup()

    def import_fixture(self):
        # Only the module's pinned digest is patched for small non-executable
        # fixtures. The production API has no caller-provided bypass argument.
        with patch.object(usb_tools, "PLATFORM_TOOLS_SHA256", self.digest):
            return usb_tools.import_platform_tools(self.zip, self.sdk)

    def assert_error(self, code):
        with self.assertRaises(usb_tools.UsbToolsError) as caught:
            self.import_fixture()
        self.assertEqual(caught.exception.code, code)

    def test_import_preserves_entire_package_notice_and_unrelated_sdk_file(self):
        self.sdk.mkdir(parents=True)
        original = self.sdk / "existing-config.txt"
        original.write_bytes(b"keep")
        with patch("subprocess.run", side_effect=AssertionError("never execute tools")):
            adb = self.import_fixture()
        self.assertEqual(adb, self.sdk / "platform-tools/adb.exe")
        for name, data in FILES.items():
            self.assertEqual((self.sdk / name).read_bytes(), data)
        self.assertEqual(original.read_bytes(), b"keep")
        self.assertEqual({p.name for p in self.sdk.iterdir()}, {"platform-tools", "existing-config.txt"})

    def test_identical_complete_install_reused_without_overwrite(self):
        adb = self.import_fixture()
        before = adb.stat().st_mtime_ns
        with patch.object(usb_tools, "_copy_member", side_effect=AssertionError("reuse, no extraction")):
            self.assertEqual(self.import_fixture(), adb)
        self.assertEqual(adb.stat().st_mtime_ns, before)

    def test_conflicting_install_and_extra_files_are_preserved(self):
        adb = self.import_fixture()
        for changed in (True, False):
            with self.subTest(changed=changed):
                adb.write_bytes(b"user's existing tool" if changed else FILES["platform-tools/adb.exe"])
                marker = adb.parent / "user-added-file.txt"
                marker.write_bytes(b"keep unchanged")
                before = {p.name: p.read_bytes() for p in adb.parent.iterdir()}
                self.assert_error("destination_conflict")
                self.assertEqual({p.name: p.read_bytes() for p in adb.parent.iterdir()}, before)

    def test_existing_platform_tools_file_is_not_deleted(self):
        self.sdk.mkdir(parents=True)
        target = self.sdk / "platform-tools"
        target.write_bytes(b"user file")
        self.assert_error("destination_conflict")
        self.assertEqual(target.read_bytes(), b"user file")

    def test_wrong_digest_does_not_create_destination(self):
        with patch.object(usb_tools, "PLATFORM_TOOLS_SHA256", "0" * 64):
            with self.assertRaises(usb_tools.UsbToolsError) as caught:
                usb_tools.import_platform_tools(self.zip, self.sdk)
        self.assertEqual(caught.exception.code, "wrong_hash")
        self.assertFalse(self.sdk.exists())

    def test_invalid_zip_and_missing_notice_write_nothing(self):
        self.zip.write_bytes(b"not a ZIP")
        self.digest = hashlib.sha256(self.zip.read_bytes()).hexdigest()
        self.assert_error("invalid_archive")
        self.assertFalse(self.sdk.exists())
        files = dict(FILES)
        del files["platform-tools/NOTICE.txt"]
        self.digest = package(self.zip, files)
        self.assert_error("invalid_archive")
        self.assertFalse(self.sdk.exists())

    def test_wrong_version_is_rejected_before_writing(self):
        files = {**FILES, "platform-tools/source.properties": b"Pkg.Revision=99.0.0\n"}
        self.digest = package(self.zip, files)
        self.assert_error("wrong_version")
        self.assertFalse(self.sdk.exists())

    def test_windows_path_traps_are_rejected_without_outside_writes(self):
        for name in ("../escaped.txt", "/absolute.txt", "platform-tools/../escaped.txt",
                     "platform-tools\\escaped.txt", "platform-tools/adb.exe:stream",
                     "platform-tools/CON.txt", "platform-tools/trailing. ",
                     "platform-tools//nested.txt", "platform-tools/ADB.EXE"):
            with self.subTest(name=name):
                self.digest = package(self.zip, extras=[(name, b"trap")])
                self.assert_error("invalid_archive")
                self.assertFalse(self.sdk.exists())
        self.assertFalse((self.base / "escaped.txt").exists())

    def test_zip_symlink_is_rejected(self):
        link = zipfile.ZipInfo("platform-tools/link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.digest = package(self.zip, extras=[(link, b"../outside")])
        self.assert_error("invalid_archive")
        self.assertFalse(self.sdk.exists())

    def test_archive_count_and_size_limits_are_checked_before_writes(self):
        for bound, value in (("MAX_ZIP_BYTES", 5), ("MAX_FILES", 3),
                             ("MAX_FILE_BYTES", 10), ("MAX_TOTAL_BYTES", 20)):
            with self.subTest(bound=bound), patch.object(usb_tools, bound, value):
                self.assert_error("invalid_archive")
                self.assertFalse(self.sdk.exists())

    def test_relative_parent_traversal_and_file_destination_rejected(self):
        for destination in (Path("relative"), self.base / "safe/../elsewhere", Path(self.base.anchor)):
            with self.subTest(destination=destination):
                with self.assertRaises(usb_tools.UsbToolsError) as caught:
                    usb_tools.import_platform_tools(self.zip, destination)
                self.assertEqual(caught.exception.code, "unsafe_destination")
        self.sdk.parent.mkdir(parents=True)
        self.sdk.write_bytes(b"existing file")
        self.assert_error("unsafe_destination")
        self.assertEqual(self.sdk.read_bytes(), b"existing file")

    def test_existing_import_lock_is_never_removed(self):
        self.sdk.mkdir(parents=True)
        lock = self.sdk / ".vrization-platform-tools-import.lock"
        lock.write_bytes(b"other import owner")
        self.assert_error("busy")
        self.assertEqual(lock.read_bytes(), b"other import owner")
        self.assertFalse((self.sdk / "platform-tools").exists())

    def test_partial_extraction_failure_removes_only_own_stage(self):
        self.sdk.mkdir(parents=True)
        keep = self.sdk / "existing.txt"
        keep.write_bytes(b"keep")
        copy = usb_tools._copy_member
        calls = []

        def fail(archive, entry, output):
            calls.append(entry.filename)
            if len(calls) == 2:
                raise OSError("disk full fixture")
            copy(archive, entry, output)

        with patch.object(usb_tools, "_copy_member", side_effect=fail):
            self.assert_error("write_failed")
        self.assertEqual(keep.read_bytes(), b"keep")
        self.assertEqual(list(self.sdk.iterdir()), [keep])

    def test_portable_and_archive_default_locations_do_not_use_appdata(self):
        for layout, root in (("VRization", "VRization"), ("latest/Windows", ""),
                             ("versions/v0.3.2-alpha/Windows", ""),
                             ("previous-latest-20261009-123456-abc123/Windows", "")):
            with self.subTest(layout=layout), \
                    patch.object(usb_tools.sys, "frozen", True, create=True), \
                    patch.object(usb_tools.sys, "executable", str(self.base / layout / "VRization-Host.exe")), \
                    patch.dict(os.environ, {"LOCALAPPDATA": str(self.base / "unused-appdata")}):
                self.assertEqual(usb_tools.default_tools_directory(), self.base / root / "tools/android-sdk")


class Widget:
    def __init__(self):
        self.values = {}

    def configure(self, **values):
        self.values.update(values)


class UsbToolsGuiTests(unittest.TestCase):
    def setUp(self):
        self.window = HostWindow.__new__(HostWindow)
        self.window.language = "en"
        self.window.usb_import_active = False
        self.window.usb_import_button = Widget()
        self.window.usb_path_label = Widget()
        self.window.usb_preferences = {"enabled": True, "adb_path": "old", "preferred_serial": ""}
        self.window.usb = SimpleNamespace(adb_path="old")
        self.window.events = queue.SimpleQueue()
        self.logs, self.saved = [], []
        self.window._log = self.logs.append
        self.window._save_usb = lambda: self.saved.append(dict(self.window.usb_preferences))

    def test_worker_only_queues_result_and_gui_thread_sets_persists_actual_path(self):
        workers = []

        class Thread:
            def __init__(self, *, target, **kwargs):
                workers.append(target)

            def start(self):
                pass

        actual = Path(tempfile.gettempdir()).resolve() / "normal-tools/platform-tools/adb.exe"
        with patch("vrization_host.gui.threading.Thread", Thread), \
                patch("vrization_host.gui.import_platform_tools", return_value=actual):
            self.window._start_usb_import("download.zip", "chosen folder")
            self.window._start_usb_import("duplicate.zip", "other folder")
            self.assertEqual(len(workers), 1)
            workers[0]()
        self.assertEqual(self.window.usb.adb_path, "old")
        self.assertFalse(self.saved)
        self.assertEqual(self.window.usb_import_button.values["state"], "disabled")
        event = self.window.events.get_nowait()
        self.window._finish_usb_import(event)
        self.assertEqual(self.window.usb.adb_path, str(actual))
        self.assertEqual(self.saved[-1]["adb_path"], str(actual))
        self.assertEqual(self.window.usb_import_button.values["state"], "normal")
        self.assertFalse(self.window.usb_import_active)

    def test_failure_keeps_existing_adb_and_has_english_chinese_message(self):
        self.window.usb_import_active = True
        self.window._finish_usb_import({"error": "destination_conflict"})
        english = self.logs[-1]
        self.assertIn("kept unchanged", english)
        self.assertNotEqual(translate(english, "zh"), english)
        self.assertEqual(self.window.usb.adb_path, "old")
        self.assertFalse(self.saved)
        self.assertFalse(self.window.usb_import_active)


if __name__ == "__main__":
    unittest.main()
