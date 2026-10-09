"""Run the public Windows ZIP in a clean directory without a developer SDK.

Only the EXE's read-only USB diagnostic entry point runs. No GUI, display
capture, reverse mapping, mouse input, driver installation or network download.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile
import zipfile


def smoke(package: Path, report: Path, version: str):
    if os.name != "nt":
        raise OSError("The packaged Windows runtime smoke test requires Windows")
    with tempfile.TemporaryDirectory(prefix="vrization-package-smoke-") as directory:
        folder = Path(directory)
        with zipfile.ZipFile(package) as archive:
            names = set(archive.namelist())
            required = {"VRization-Host.exe", "Start-Windows.bat", "Start-on-second-monitor.bat",
                        "LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "docs/USB.md"}
            if not required <= names:
                raise ValueError("The public Windows ZIP is missing runnable files or its USB guide")
            for item in archive.infolist():
                path = PurePosixPath(item.filename)
                if (path.is_absolute() or ".." in path.parts or ":" in item.filename
                        or "\\" in item.filename or stat.S_ISLNK(item.external_attr >> 16)
                        or not (folder / item.filename).resolve().is_relative_to(folder.resolve())):
                    raise ValueError("Unsafe public package path")
                if path.name.casefold() in {"adb.exe", "fastboot.exe", "adbwinapi.dll", "adbwinusbapi.dll"}:
                    raise ValueError("Separately installed Android tools must not be bundled")
            executable_sha = hashlib.sha256(archive.read("VRization-Host.exe")).hexdigest()
            archive.extractall(folder)
        diagnostic = folder / "usb-diagnostic.json"
        environment = dict(os.environ)
        environment.pop("ANDROID_HOME", None)
        environment.pop("ANDROID_SDK_ROOT", None)
        # Exercise a fresh profile with no known SDK, independently of the CI
        # runner's installed Android development environment.
        local = folder / "local-profile"
        local.mkdir()
        environment["LOCALAPPDATA"] = str(local)
        # A current-directory executable must never be chosen as an SDK tool.
        (folder / "adb.exe").write_bytes(b"NOT AN SDK TOOL")
        subprocess.run([str(folder / "VRization-Host.exe"), "--usb-diagnostics", str(diagnostic)],
                       cwd=folder, env=environment, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=30)
        data = json.loads(diagnostic.read_text(encoding="utf-8"))
        if (data.get("frozen") is not True or data.get("read_only") is not True
                or data.get("diagnostic_complete") is not True
                or data.get("forbidden_runtime_imports") != []
                or data.get("version") != version or data.get("adb_found") is not False):
            raise ValueError("The clean public package diagnostic failed its runtime contract")
        result = {"passed": True, "version": version, "windowsExecutableSHA256": executable_sha,
                  "source": "public ZIP extracted to a fresh directory",
                  "developerSDKEnvironment": False, "bundledAndroidTools": False,
                  "currentDirectoryToolIgnored": True, "diagnostic": data}
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("Public Windows ZIP runtime passed with no developer SDK or mouse/capture actions.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    smoke(args.zip, args.report, args.version)


if __name__ == "__main__":
    main()
