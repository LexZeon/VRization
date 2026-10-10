"""Check the complete Windows preview without opening GUI or SteamVR.

Derived from VRization's original smoke_windows_package.py (project MIT).
Only the frozen EXE's read-only diagnostics run. A short child of this Python
helper uses the ZIP's own IPC DLL with unique frame/event names; it never opens
the fixed phone pose map, captures a display, moves a mouse, starts a native
helper, registers a driver, or downloads anything.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
from unittest.mock import patch
import zipfile

from build_steamvr_native import COMMIT, PINS
from package_release import check_document_links

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.0-steamvr-preview"
EXE = "VRization-SteamVR.exe"
NATIVE_FILES = {
    "native/VRization-SteamVR-Mirror.exe", "native/VRization-SteamVR-Overlay.exe",
    "native/VRization-SteamVR-IPC.dll", "native/openvr_api.dll",
    "drivers/vrization_phone/bin/win64/driver_vrization_phone.dll",
    "drivers/vrization_phone/driver.vrdrivermanifest",
    "drivers/vrization_phone/resources/settings/default.vrsettings",
    "native/licenses/OpenVR-LICENSE.txt", "native/licenses/VRization-MIT.txt",
    "native/README.md", "native/licenses/README.md",
}
REQUIRED = NATIVE_FILES | {
    EXE, "native-build-report.json", "Start-SteamVR-Preview.bat",
    "Start-SteamVR-Preview-second-monitor.bat", "LICENSE", "NOTICE",
    "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "docs/USB.md",
    "experimental/steamvr/README.md", "experimental/steamvr/docs/ARCHITECTURE.md",
    "experimental/steamvr/docs/AI_HANDOFF.md",
    "experimental/steamvr/python/vrization_steamvr/__init__.py",
    "experimental/steamvr/python/vrization_steamvr/ipc.py",
    "experimental/steamvr/python/vrization_steamvr/runtime.py",
}
BINARIES = {EXE} | {name for name in NATIVE_FILES if Path(name).suffix in {".exe", ".dll"}}
FORBIDDEN_TOOLS = {"adb.exe", "fastboot.exe", "adbwinapi.dll", "adbwinusbapi.dll"}
FORBIDDEN_SYSTEM = {"kernel32.dll", "user32.dll", "advapi32.dll", "gdi32.dll", "ntdll.dll", "ucrtbase.dll"}
FORBIDDEN_SDK_PARTS = {"sdk", "android-sdk", "platform-tools", "cmdline-tools", "openvr-sdk",
                       "windows-sdk", "windows-kits", "ndk", "android-ndk"}
PRIVATE_SUFFIXES = {".jks", ".keystore", ".p12", ".pfx", ".key", ".pem"}
TEXT_SUFFIXES = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".xml", ".ini", ".toml", ".conf"}
RESERVED = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1, 10)} | {f"lpt{i}" for i in range(1, 10)}
PRIVATE_HEADER = re.compile(br"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_archive(package: Path, folder: Path) -> dict:
    """Validate all entries before extracting, including Windows path aliases."""
    with zipfile.ZipFile(package) as archive:
        items = archive.infolist()
        require(len(items) <= 20_000 and sum(item.file_size for item in items) <= 1024**3,
                "Preview ZIP exceeds the extraction bounds")
        names: set[str] = set()
        folded: dict[str, bool] = {}
        executable_names: set[str] = set()
        for item in items:
            # ZipInfo normalizes backslashes on Windows and truncates NULs.
            # Check the original central-directory spelling as well.
            raw = item.orig_filename
            path = PurePosixPath(raw)
            kind = stat.S_IFMT(item.external_attr >> 16)
            parts = raw.rstrip("/").split("/")
            if (not raw or raw != item.filename or path.is_absolute() or any(character in raw for character in ':\\<>"|?*')
                    or any(part in {"", ".", ".."} for part in parts)
                    or any(ord(character) < 32 for character in raw)
                    or any(part.endswith((" ", ".")) or part.split(".", 1)[0].casefold() in RESERVED for part in parts)
                    or kind not in {0, stat.S_IFREG, stat.S_IFDIR}
                    or item.flag_bits & 1
                    or not (folder / raw).resolve().is_relative_to(folder.resolve())):
                raise ValueError("Unsafe preview package path")
            key = raw.rstrip("/").casefold()
            require(key not in folded, "Duplicate or case-aliased preview package path")
            folded[key] = item.is_dir()
            if item.is_dir():
                continue
            require(item.file_size <= 256 * 1024**2, "Preview ZIP member exceeds the extraction bounds")
            name = path.name.casefold()
            suffix = path.suffix.casefold()
            require(name not in FORBIDDEN_TOOLS, "Separately installed Android tools must not be bundled")
            require(not ({part.casefold() for part in path.parts} & FORBIDDEN_SDK_PARTS)
                    and name not in {"openvr.h", "openvr_driver.h", "windows.h", "d3d11.h",
                                     "d3dcompiler.h", "dxgi.h", "sdkmanager", "sdkmanager.bat"},
                    "An SDK must not be bundled in the runnable preview ZIP")
            require(suffix != ".lib", "Native import libraries must not be bundled")
            require(name not in FORBIDDEN_SYSTEM and not (
                suffix == ".dll" and name.startswith(("d3d", "dxgi", "api-ms-win-", "vcruntime", "msvcp"))),
                "Windows system or toolchain DLLs must not be bundled")
            require(suffix not in PRIVATE_SUFFIXES and not name.startswith(".env"),
                    "Private key or environment file found in the preview ZIP")
            if suffix in TEXT_SUFFIXES or name in {"license", "notice"}:
                require(not PRIVATE_HEADER.search(archive.read(item)), "Private key text found in the preview ZIP")
            if suffix in {".dll", ".exe", ".lib"}:
                executable_names.add(raw)
            names.add(raw)
        for key in folded:
            parent = PurePosixPath(key).parent
            while str(parent) != ".":
                require(folded.get(str(parent), True), "A file aliases a preview package directory")
                parent = parent.parent
        require(REQUIRED <= names, "Complete Windows preview assets, source or notices are missing")
        require(executable_names == BINARIES, "Unexpected executable in the complete preview ZIP")
        report = json.loads(archive.read("native-build-report.json"))
        require(isinstance(report, dict) and report.get("sdkCommit") == COMMIT
                and report.get("sdkPins") == PINS and report.get("sdkLicense") == "BSD-3-Clause"
                and report.get("configuration") == "Release" and report.get("ctestExecuted") is True,
                "Pinned native Release/CTest provenance is missing")
        require(all(report.get(key) is False for key in (
            "hardwareTested", "runtimeLaunched", "driverRegistered", "bundledWindowsSystemDlls")),
            "Native report must preserve its software-only build scope")
        require(isinstance(report.get("ctestLogSha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", report["ctestLogSha256"]) is not None,
                "Native CTest log hash is missing")
        hashes = report.get("files")
        require(isinstance(hashes, dict) and set(hashes) == NATIVE_FILES, "Native asset manifest is incomplete")
        for name in NATIVE_FILES:
            require(hashes[name] == hashlib.sha256(archive.read(name)).hexdigest(),
                    f"Native build manifest does not match {name}")
        require(hashes["native/openvr_api.dll"] == PINS["bin/win64/openvr_api.dll"]
                and hashes["native/licenses/OpenVR-LICENSE.txt"] == PINS["LICENSE"],
                "Bundled OpenVR binary or original license differs from its pin")
        driver = json.loads(archive.read("drivers/vrization_phone/driver.vrdrivermanifest"))
        require(isinstance(driver, dict) and driver.get("name") == "vrization_phone"
                and driver.get("hmd_presence") == ["VRizationPhone"], "Unexpected phone driver identity")
        for name in ("Start-SteamVR-Preview.bat", "Start-SteamVR-Preview-second-monitor.bat"):
            launcher = archive.read(name).decode("utf-8").casefold()
            require("vrization-steamvr.exe" in launcher
                    and not any(word in launcher for word in ("adddriver", "removedriver", "vrpathreg", "steam://")),
                    "Launcher must not register a driver or open a runtime")
        check_document_links(package)
        executable_sha = hashlib.sha256(archive.read(EXE)).hexdigest()
        archive.extractall(folder)
    return {"assetCount": len(names), "nativeBuildReport": report,
            "windowsExecutableSHA256": executable_sha}


def isolated_environment(folder: Path) -> dict[str, str]:
    environment = dict(os.environ)
    for name in ("ANDROID_HOME", "ANDROID_SDK_ROOT", "ANDROID_SDK_HOME", "JAVA_HOME", "PYTHONPATH", "PYTHONHOME"):
        environment.pop(name, None)
    local = folder / "fresh-profile"
    for name in ("local", "roaming", "user", "temp"):
        (local / name).mkdir(parents=True)
    environment.update({"LOCALAPPDATA": str(local / "local"), "APPDATA": str(local / "roaming"),
                        "USERPROFILE": str(local / "user"), "HOME": str(local / "user"),
                        "TEMP": str(local / "temp"), "TMP": str(local / "temp"),
                        "VRIZATION_PROFILE_DIRECTORY": str(local / "local/VRizationSteamVR/Windows"),
                        "PYTHONDONTWRITEBYTECODE": "1"})
    # Keep only CWD and Windows system tools; inherited development SDK paths
    # cannot participate in this fixture. ADB itself is never executed.
    environment["PATH"] = str(folder) + os.pathsep + str(Path(environment.get("SystemRoot", r"C:\Windows")) / "System32")
    return environment


def check_diagnostic(data: dict, version: str) -> None:
    require(isinstance(data, dict) and data.get("version") == version
            and data.get("channel") == "steamvr-experimental", "Wrong frozen preview identity")
    require(data.get("routes") == ["direct-phone", "steamvr-phone", "steamvr-headset"]
            and type(data.get("hostPort")) is int and data["hostPort"] == 8766
            and data.get("androidPorts") == [18774, 18775] and data.get("iosPorts") == [18776, 18777],
            "Frozen preview routes or isolated ports are incorrect")
    require(all(data.get(key) is True for key in ("nativeHelpersPresent", "driverPresent", "atomicIPCPresent")),
            "Frozen preview cannot find its native bundle")
    require(all(data.get(key) is False for key in (
        "runtimeDetected", "hardwareVerified", "startsCapture", "injectsMouse", "registersDriver")),
        "Fresh-profile diagnostics must not capture, inject input, register, or claim hardware")


def ipc_child(folder: Path, report: Path) -> None:
    """Real ZIP DLL fixture in a short process, releasing loaded DLLs on exit."""
    require(os.name == "nt", "Windows IPC fixture requires Windows")
    folder = folder.resolve()
    sys.path[:0] = [str(folder / "experimental/steamvr/python"), str(ROOT / "desktop/src")]
    from vrization_steamvr import ipc, runtime
    from vrization_host import usb
    require(Path(ipc.__file__).resolve().is_relative_to(folder), "IPC fixture did not import the ZIP's source")
    require(Path(runtime.__file__).resolve().is_relative_to(folder), "Runtime fixture did not import the ZIP's source")
    # This source resolver assertion is explicitly separate from frozen EXE
    # diagnostics, which currently expose no adb_found field.
    with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(folder / EXE)):
        require(usb.find_adb() is None, "A fresh profile unexpectedly adopted a CWD/PATH ADB tool")
    pixels = b"".join(bytes((0, 29 + y, 255, 255) if x < 2 else (255, 61 + y, 0, 255))
                      for y in range(2) for x in range(4))
    writer = reader = event = None
    with patch.object(runtime, "bundle_root", return_value=folder):
        try:
            name = ipc.frame_name()
            require(name != ipc.POSE_NAME and name.startswith("Local\\VRizationFrame-"), "Unique frame name is required")
            writer = ipc.FrameWriter(name)
            require(Path(writer.mapping.atomic._name).resolve() == folder / "native/VRization-SteamVR-IPC.dll",
                    "IPC fixture loaded a DLL outside the ZIP")
            reader = ipc.FrameReader(name, stereo=True)
            writer.publish(4, 2, pixels)
            sample = reader.read()
            require(sample is not None and sample[:3] == (4, 2, pixels), "Real IPC stereo color bytes were not preserved")
            try:
                conflict = ipc.FrameWriter(name)
            except FileExistsError:
                pass
            else:
                conflict.close()
                raise ValueError("A second frame writer unexpectedly acquired the existing map")
            writer.close()
            require(reader.read() is None, "Closed writer did not invalidate the frame")
            event = ipc.StopEvent()
            require(event.name.startswith("Local\\VRizationStop-"), "Unique owned Stop event is required")
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.WaitForSingleObject.restype = wintypes.DWORD
            require(kernel.WaitForSingleObject(event.handle, 0) == 258, "New Stop event was already signaled")
            event.signal()
            require(kernel.WaitForSingleObject(event.handle, 0) == 0, "Owned Stop event signal was not observed")
        finally:
            for resource in (writer, reader, event):
                if resource is not None:
                    resource.close()
                    resource.close()
    result = {"passed": True, "frameDimensions": [4, 2], "pixelSHA256": hashlib.sha256(pixels).hexdigest(),
              "source": "IPC source and atomic DLL extracted from the checked ZIP",
              "inactiveAfterClose": True, "duplicateWriterRejected": True, "ownedStopEventVerified": True,
              "fixedPoseMapOpened": False, "currentDirectoryToolIgnored": True,
              "adbCheckScope": "Shared source resolver with extracted frozen EXE identity; not a frozen diagnostic adb_found claim",
              "sharedResolverSHA256": digest(Path(usb.__file__)), "ipcSourceSHA256": digest(Path(ipc.__file__)),
              "nativeAtomicSHA256": digest(folder / "native/VRization-SteamVR-IPC.dll")}
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def smoke(package: Path, report: Path, version: str = VERSION) -> None:
    require(os.name == "nt", "The packaged Windows preview smoke test requires Windows")
    require(version == VERSION, "This helper validates the 0.5.0-steamvr-preview contract")
    package, report = package.resolve(), report.resolve()
    require(package != report, "The smoke report must not overwrite its input ZIP")
    zip_sha = digest(package)
    with tempfile.TemporaryDirectory(prefix="vrization-steamvr-smoke-") as directory:
        folder = Path(directory).resolve()
        inventory = validate_archive(package, folder)
        environment = isolated_environment(folder)
        fake_adb = folder / "adb.exe"
        fake_adb.write_bytes(b"NOT AN SDK TOOL - DO NOT EXECUTE")
        diagnostic, ipc_report = folder / "preview-diagnostic.json", folder / "ipc-fixture.json"
        options = {"cwd": folder, "env": environment, "stdin": subprocess.DEVNULL,
                   "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
                   "check": True, "timeout": 30, "creationflags": subprocess.CREATE_NO_WINDOW}
        subprocess.run([str(folder / EXE), "--diagnostics-output", str(diagnostic)], **options)
        data = json.loads(diagnostic.read_text(encoding="utf-8"))
        check_diagnostic(data, version)
        subprocess.run([sys.executable, "-X", "utf8", str(Path(__file__).resolve()),
                        "--ipc-root", str(folder), "--ipc-report", str(ipc_report)], **options)
        ipc_data = json.loads(ipc_report.read_text(encoding="utf-8"))
        require(ipc_data.get("passed") is True and ipc_data.get("currentDirectoryToolIgnored") is True
                and ipc_data.get("fixedPoseMapOpened") is False
                and ipc_data.get("nativeAtomicSHA256") == inventory["nativeBuildReport"]["files"]["native/VRization-SteamVR-IPC.dll"],
                "ZIP-owned IPC/source-resolver fixture failed")
        require(fake_adb.read_bytes() == b"NOT AN SDK TOOL - DO NOT EXECUTE", "CWD ADB fixture was modified")
        require(digest(package) == zip_sha, "ZIP changed during its smoke check")
        result = {"passed": True, "verifiedUtc": datetime.now(timezone.utc).isoformat(), "version": version,
                  "zipSHA256": zip_sha, "windowsExecutableSHA256": inventory["windowsExecutableSHA256"],
                  "assetCount": inventory["assetCount"], "source": "Complete ZIP extracted to an isolated temporary directory",
                  "developerSDKEnvironment": False, "bundledSDK": False, "bundledAndroidTools": False,
                  "bundledSystemGraphicsDlls": False, "bundledImportLibraries": False, "privateKeyEntries": False,
                  "currentDirectoryToolIgnored": True, "diagnostic": data, "ipcFixture": ipc_data,
                  "nativeBuildReport": inventory["nativeBuildReport"],
                  "actions": {"displayCaptures": 0, "mouseInjections": 0, "steamVrRuntimeLaunches": 0,
                              "driverRegistrations": 0, "nativeMirrorOverlayLaunches": 0, "guiWindows": 0,
                              "adbCommands": 0, "hardwareTests": 0},
                  "hardwareTested": False}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Complete SteamVR Windows ZIP diagnostics and owned IPC passed; no GUI, capture, mouse, runtime or driver actions.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--version", default=VERSION)
    parser.add_argument("--ipc-root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--ipc-report", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.ipc_root is not None or args.ipc_report is not None:
        if args.ipc_root is None or args.ipc_report is None or args.zip is not None or args.report is not None:
            parser.error("Both internal IPC arguments are required, without ZIP/report arguments")
        ipc_child(args.ipc_root, args.ipc_report)
    else:
        if args.zip is None or args.report is None:
            parser.error("--zip and --report are required")
        smoke(args.zip, args.report, args.version)


if __name__ == "__main__":
    main()
