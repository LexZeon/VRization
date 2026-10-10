"""Public-release signing regressions; no private keys or real APK signing."""
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import verify_android_release as signing


DIGEST = "c8221633041e9b4551cd6e9f4f657e7beeb0901a4b77999d1bfc11d3825b6d74"
OUTPUT = f"Verifies\nNumber of signers: 1\nSigner #1 certificate SHA-256 digest: {DIGEST}\n"


class AndroidReleaseSigningTests(unittest.TestCase):
    def test_single_certificate_matches_the_published_identity(self):
        self.assertEqual(signing.read_fingerprint(signing.CANONICAL_CERTIFICATE), DIGEST)
        self.assertEqual(signing.verified_fingerprint(OUTPUT.replace(DIGEST, DIGEST.upper())), DIGEST)

    def test_ambiguous_missing_and_multiple_signers_are_rejected(self):
        for output in ("", "Verifies\n", OUTPUT.replace("Number of signers: 1", "Number of signers: 2"),
                       OUTPUT + f"Signer #2 certificate SHA-256 digest: {DIGEST}\n",
                       OUTPUT + f"Signer #1 certificate SHA-256 digest: {DIGEST}\n",
                       OUTPUT + "Number of signers: 1\n",
                       OUTPUT.replace("Signer #1", "Signer #2"),
                       OUTPUT.replace(DIGEST, "bad-fingerprint")):
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    signing.verified_fingerprint(output)

    def test_signature_failure_and_different_debug_key_block_publication(self):
        with tempfile.TemporaryDirectory(prefix="vrization-signature-test-") as directory:
            folder = Path(directory)
            apk, tool, certificate = folder / "test.apk", folder / "apksigner", folder / "certificate.sha256"
            apk.touch(); tool.touch(); certificate.write_text(DIGEST, encoding="ascii")
            for code, output in ((1, OUTPUT), (0, OUTPUT.replace(DIGEST, "a" * 64))):
                def runner(command, **kwargs):
                    return SimpleNamespace(returncode=code, stdout=output)
                with self.subTest(returncode=code):
                    with self.assertRaisesRegex(ValueError, "publication blocked"):
                        signing.verify_apk(apk, tool, certificate, runner=runner)

    def test_official_verifier_receives_apk_as_an_argument_without_a_shell(self):
        with tempfile.TemporaryDirectory(prefix="vrization-signature-test-") as directory:
            folder = Path(directory)
            apk, tool, certificate = folder / "download & test.apk", folder / "apksigner", folder / "certificate.sha256"
            apk.touch(); tool.touch(); certificate.write_text(DIGEST, encoding="ascii")
            observed = []
            def runner(command, **kwargs):
                observed.append((command, kwargs))
                return SimpleNamespace(returncode=0, stdout=OUTPUT)
            self.assertEqual(signing.verify_apk(apk, tool, certificate, runner=runner), DIGEST)
            command, options = observed[0]
            self.assertEqual(command, [str(tool.resolve()), "verify", "--verbose", "--print-certs", str(apk.resolve())])
            self.assertNotIn("shell", options)
            self.assertEqual(options["stdin"], subprocess.DEVNULL)
            self.assertEqual(options["timeout"], 60)

    def test_windows_batch_uses_the_official_jar_without_cmd_parsing(self):
        with tempfile.TemporaryDirectory(prefix="vrization-signature-test-") as directory:
            folder = Path(directory)
            tool = folder / "sdk/build-tools/apksigner.bat"
            jar = tool.parent / "lib/apksigner.jar"
            java = folder / "jdk/bin/java.exe"
            for file in (tool, jar, java):
                file.parent.mkdir(parents=True, exist_ok=True); file.touch()
            with patch.dict(os.environ, {"JAVA_HOME": str(java.parent.parent)}):
                self.assertEqual(signing.verifier_command(tool), [str(java), "-jar", str(jar)])

    def test_invalid_expected_fingerprint_and_missing_verifier_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="vrization-signature-test-") as directory:
            folder = Path(directory)
            certificate = folder / "certificate.sha256"
            for value in ("", DIGEST + "\n" + DIGEST, "z" * 64):
                certificate.write_text(value, encoding="ascii")
                with self.assertRaises(ValueError):
                    signing.read_fingerprint(certificate)
            with self.assertRaises(FileNotFoundError):
                signing.verifier_command(folder / "missing-apksigner")


if __name__ == "__main__":
    unittest.main()
