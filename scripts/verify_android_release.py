"""Require the public APK's existing signing identity before publication.

This reads only a public certificate fingerprint and runs the official Android
apksigner verifier. It never signs an APK or reads a private signing key.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess


CANONICAL_CERTIFICATE = Path(__file__).with_name("android-release-certificate.sha256")


def read_fingerprint(path: Path) -> str:
    fingerprint = path.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", fingerprint):
        raise ValueError("Expected exactly one SHA-256 certificate fingerprint")
    return fingerprint.lower()


def verified_fingerprint(output: str) -> str:
    """Fail closed on missing, ambiguous or multiple-signature verifier output."""
    counts = re.findall(r"^Number of signers:\s*([0-9]+)\s*$", output, re.MULTILINE)
    certificates = re.findall(
        r"^Signer #([0-9]+) certificate SHA-256 digest:\s*([0-9a-fA-F]{64})\s*$",
        output, re.MULTILINE)
    if counts != ["1"] or len(certificates) != 1 or certificates[0][0] != "1":
        raise ValueError("The public APK must have exactly one verified signer")
    return certificates[0][1].lower()


def verifier_command(apksigner: Path) -> list[str]:
    apksigner = apksigner.resolve()
    if not apksigner.is_file():
        raise FileNotFoundError("Official Android SDK apksigner was not found")
    if apksigner.suffix.lower() not in {".bat", ".cmd"}:
        return [str(apksigner)]
    # Use the official JAR directly on Windows. Passing a .bat and an APK path
    # through cmd.exe would interpret shell metacharacters in a download path.
    jar = next((path for path in (apksigner.parent / "lib/apksigner.jar",
                                 apksigner.parent / "apksigner.jar") if path.is_file()), None)
    java_home = os.environ.get("JAVA_HOME")
    java = Path(java_home) / "bin/java.exe" if java_home else None
    if java is None or not java.is_file():
        found = shutil.which("java")
        java = Path(found) if found else None
    if jar is None or java is None:
        raise FileNotFoundError("Official apksigner JAR and a Java runtime are required")
    return [str(java), "-jar", str(jar)]


def verify_apk(apk: Path, apksigner: Path, certificate: Path = CANONICAL_CERTIFICATE,
               *, runner=None) -> str:
    expected = read_fingerprint(certificate)
    apk = apk.resolve()
    if not apk.is_file():
        raise FileNotFoundError("The public Android APK was not found")
    command = verifier_command(apksigner) + ["verify", "--verbose", "--print-certs", str(apk)]
    result = (runner or subprocess.run)(command, stdin=subprocess.DEVNULL,
                                       capture_output=True, text=True, encoding="utf-8",
                                       errors="replace", check=False, timeout=60)
    if result.returncode != 0:
        raise ValueError("Official apksigner rejected the APK signature; publication blocked")
    actual = verified_fingerprint(result.stdout)
    if actual != expected:
        raise ValueError("APK certificate differs from the public upgrade identity; publication blocked")
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--apksigner", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, default=CANONICAL_CERTIFICATE)
    args = parser.parse_args()
    try:
        digest = verify_apk(args.apk, args.apksigner, args.certificate)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"Android release blocked / Android 发布已阻止: {error}\n")
    print(f"Android signature verified / Android 签名已验证: {digest}")


if __name__ == "__main__":
    main()
