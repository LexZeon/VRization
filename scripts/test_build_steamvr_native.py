"""Offline tests for pinned dependency provenance; no compiler/runtime/device needed."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("native_build", Path(__file__).with_name("build_steamvr_native.py"))
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class PinnedSdkTests(unittest.TestCase):
    def test_real_pin_metadata_and_verbatim_license(self):
        self.assertEqual(len(BUILD.PINS), 5)
        self.assertEqual(BUILD.COMMIT, "0924064316de3effbcd1acf1e309182a2deb1c05")
        for value in BUILD.PINS.values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")
        license_file = BUILD.ROOT / "experimental/steamvr/native/licenses/OpenVR-LICENSE.txt"
        self.assertEqual(BUILD.digest(license_file), BUILD.PINS["LICENSE"])
        self.assertIn(b"Copyright (c) 2015, Valve Corporation", license_file.read_bytes())

    def test_verified_existing_cache_does_not_download_or_change(self):
        data = b"exact dependency fixture\n"; pins = {"headers/fixture.h": hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as folder, patch.object(BUILD, "PINS", pins), patch.object(BUILD, "urlopen") as network:
            destination = Path(folder);target = destination / "headers/fixture.h";target.parent.mkdir();target.write_bytes(data)
            self.assertEqual(BUILD.fetch_sdk(destination), pins)
            self.assertEqual(target.read_bytes(), data);network.assert_not_called()

    def test_wrong_existing_cache_is_preserved_and_rejected(self):
        pins = {"LICENSE": hashlib.sha256(b"expected").hexdigest()}
        with tempfile.TemporaryDirectory() as folder, patch.object(BUILD, "PINS", pins), patch.object(BUILD, "urlopen") as network:
            target = Path(folder) / "LICENSE";target.write_bytes(b"keep this evidence")
            with self.assertRaisesRegex(ValueError, "preserved"):
                BUILD.fetch_sdk(Path(folder))
            self.assertEqual(target.read_bytes(), b"keep this evidence");network.assert_not_called()

    def test_verified_download_uses_pinned_commit_and_atomic_final_file(self):
        data = b"fixture bytes\n";pins = {"bin/win64/fixture.dll": hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as folder, patch.object(BUILD, "PINS", pins), patch.object(BUILD, "urlopen", return_value=io.BytesIO(data)) as network:
            destination = Path(folder);BUILD.fetch_sdk(destination)
            self.assertEqual((destination / "bin/win64/fixture.dll").read_bytes(), data)
            self.assertEqual(network.call_args.args[0].full_url, BUILD.BASE_URL + "bin/win64/fixture.dll")
            self.assertEqual(list(destination.rglob(".sdk-*")), [])

    def test_wrong_download_never_becomes_dependency(self):
        pins = {"headers/fixture.h": hashlib.sha256(b"expected").hexdigest()}
        with tempfile.TemporaryDirectory() as folder, patch.object(BUILD, "PINS", pins), patch.object(BUILD, "urlopen", return_value=io.BytesIO(b"corrupt")):
            with self.assertRaisesRegex(ValueError, "SHA256"):
                BUILD.fetch_sdk(Path(folder))
            self.assertFalse((Path(folder) / "headers/fixture.h").exists())

    def test_oversized_download_is_rejected_even_when_hash_matches_read_data(self):
        data = b"x" * (5 * 1024 * 1024 + 1);pins = {"bin/fixture.dll": hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as folder, patch.object(BUILD, "PINS", pins), patch.object(BUILD, "urlopen", return_value=io.BytesIO(data)):
            with self.assertRaisesRegex(ValueError, "SHA256"):
                BUILD.fetch_sdk(Path(folder))
            self.assertFalse((Path(folder) / "bin/fixture.dll").exists())


if __name__ == "__main__":
    unittest.main()
