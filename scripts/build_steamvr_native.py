"""Build only the isolated SteamVR native preview; never install/register a driver.

OpenVR SDK v2.15.6, Valve BSD-3-Clause, commit and SHA256 pinned below.
Original build orchestration: VRization contributors, MIT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "0924064316de3effbcd1acf1e309182a2deb1c05"
BASE_URL = f"https://raw.githubusercontent.com/ValveSoftware/openvr/{COMMIT}/"
PINS = {
    "headers/openvr.h": "1e6ed57199896cc1f7c5484e50fa18955e97be15be690beb28d998c877ead7fd",
    "headers/openvr_driver.h": "1036efe998d63e82d1d3db2b32a2f58df4a8eeaf5280f50aaf28220ff60a40ab",
    "lib/win64/openvr_api.lib": "a0bf57c5920f569e8d21ab3e5bc95bac4b73e2016217f8b5b93495a2a7197bbb",
    "bin/win64/openvr_api.dll": "bab8ac6ef64e68a9ca53315b0014d131088584b2efdfa6db511d67ec03cfcb4a",
    "LICENSE": "f56ff606104d4ef18e617921a75c73ad73b5a1a1d70c69590c29de16919e04ad",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch_sdk(destination: Path) -> dict[str, str]:
    """Only add missing files; a wrong existing file is preserved and rejected."""
    result = {}
    for relative, expected in PINS.items():
        target = destination / relative
        if target.exists():
            if digest(target) != expected:
                raise ValueError(f"Existing SDK file has unexpected SHA256; preserved: {target}")
        else:
            request = Request(BASE_URL + relative, headers={"User-Agent": "VRization-native-pinned-build/1"})
            with urlopen(request, timeout=30) as response:
                data = response.read(5 * 1024 * 1024 + 1)
            if len(data) > 5 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f"Pinned SDK download failed SHA256: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".sdk-", delete=False) as pending:
                temporary = Path(pending.name)
                pending.write(data)
            try:
                # The cache is build-owned; do not replace files supplied by another invocation.
                if target.exists():
                    if digest(target) != expected:
                        raise ValueError(f"SDK target changed during fetch; preserved: {target}")
                else:
                    temporary.rename(target)
            finally:
                temporary.unlink(missing_ok=True)
        result[relative] = expected
    return result


def run(command: list[str]) -> None:
    print("Running:", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", type=Path, default=ROOT / "artifacts/tools" / f"openvr-{COMMIT}")
    parser.add_argument("--build-dir", type=Path, default=ROOT / "artifacts/steamvr/native-build")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/steamvr/native-bundle")
    parser.add_argument("--configuration", choices=("Release", "Debug"), default="Release")
    parser.add_argument("--test", action="store_true", help="Run CTest IPC/pose/WARP/factory fixtures; no runtime/hardware test")
    parser.add_argument("--fetch-only", action="store_true")
    args = parser.parse_args(argv)
    sdk, build, output = args.sdk_root.resolve(), args.build_dir.resolve(), args.output.resolve()
    pins = fetch_sdk(sdk)
    license_source = ROOT / "experimental/steamvr/native/licenses/OpenVR-LICENSE.txt"
    if not license_source.is_file() or digest(license_source) != PINS["LICENSE"]:
        raise ValueError("Native upstream license must be preserved byte-for-byte")
    print(f"Verified OpenVR v2.15.6 {COMMIT}, BSD-3-Clause, five pinned files.", flush=True)
    if args.fetch_only:
        return 0
    if platform.system() != "Windows":
        raise RuntimeError("Native build requires a Windows x64 MSVC runner; this script installs no compiler/runtime.")
    cmake, ctest = shutil.which("cmake"), shutil.which("ctest")
    if not cmake or (args.test and not ctest):
        raise RuntimeError("CMake/CTest missing. Use the configured GitHub Windows MSVC runner; no automatic installer is run.")
    run([cmake, "-S", str(ROOT / "experimental/steamvr/native"), "-B", str(build), "-A", "x64",
         f"-DOPENVR_SDK_ROOT={sdk.as_posix()}", "-DBUILD_TESTING=ON"])
    run([cmake, "--build", str(build), "--config", args.configuration, "--parallel"])
    if args.test:
        run([ctest, "--test-dir", str(build), "-C", args.configuration, "--output-on-failure"])
    run([cmake, "--install", str(build), "--config", args.configuration, "--prefix", str(output)])
    expected = (
        "native/VRization-SteamVR-Mirror.exe", "native/VRization-SteamVR-Overlay.exe", "native/openvr_api.dll",
        "drivers/vrization_phone/bin/win64/driver_vrization_phone.dll", "drivers/vrization_phone/driver.vrdrivermanifest",
        "drivers/vrization_phone/resources/settings/default.vrsettings", "native/licenses/OpenVR-LICENSE.txt",
        "native/licenses/VRization-MIT.txt", "native/README.md", "native/licenses/README.md",
    )
    missing = [name for name in expected if not (output / name).is_file()]
    if missing:
        raise RuntimeError(f"Incomplete native staging: {missing}")
    if digest(output / "native/openvr_api.dll") != PINS["bin/win64/openvr_api.dll"]:
        raise ValueError("Staged OpenVR binary is not the pinned SDK DLL")
    if digest(output / "native/licenses/OpenVR-LICENSE.txt") != PINS["LICENSE"]:
        raise ValueError("Staged OpenVR license differs from upstream")
    allowed_binaries = {name for name in expected if Path(name).suffix.lower() in (".exe", ".dll", ".lib")}
    unexpected_binaries = [path.relative_to(output).as_posix() for path in output.rglob("*")
                           if path.is_file() and path.suffix.lower() in (".exe", ".dll", ".lib")
                           and path.relative_to(output).as_posix() not in allowed_binaries]
    if unexpected_binaries:
        raise ValueError(f"Unexpected native staging binaries preserved; refusing package: {unexpected_binaries}")
    report = {
        "generatedUtc": datetime.now(timezone.utc).isoformat(), "sdkCommit": COMMIT,
        "sdkLicense": "BSD-3-Clause", "sdkPins": pins, "configuration": args.configuration,
        "ctestExecuted": args.test, "hardwareTested": False, "runtimeLaunched": False,
        "driverRegistered": False, "bundledWindowsSystemDlls": False,
        "files": {name: digest(output / name) for name in expected},
    }
    if args.test:
        log = build / "Testing/Temporary/LastTest.log"
        if not log.is_file():
            raise RuntimeError("CTest finished but its native fixture log is missing")
        report["ctestLogSha256"] = digest(log)
    report_path = output / "native-build-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Native staging complete. Report: {report_path}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Native build failed: {error}", file=sys.stderr)
        raise SystemExit(1)
