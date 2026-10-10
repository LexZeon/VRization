"""Redacted USB diagnosis for source and windowed frozen app entry points.

No GUI, screen capture, input adapters, relay, reverse mapping or adb daemon
shutdown. Only known SDK discovery and noninteractive version/device reads.
The selected OUTPUT file is the only file written; no preferences are changed.
"""

import json
import os
from pathlib import Path
import re
import sys

from ._version import __version__
from .usb import AdbReverse, find_adb, portable_adb_candidates, parse_adb_devices


FORBIDDEN_RUNTIME = ("tkinter", "_tkinter", "mss", "vrization_host.gui",
                     "vrization_host.capture", "vrization_host.input", "vrization_host.server",
                     "vrization_host.windows_capture", "vrization_host.windows_gpu")


def _error(report, stage, error):
    # Exception messages, stderr, command arguments and URLs can contain secrets.
    report["errors"].append({"stage": stage, "code": type(error).__name__})


def _virtualized(path: Path) -> bool:
    parts = str(path).replace("\\", "/").casefold().split("/")
    return "packages" in parts and "localcache" in parts and any(
        part.startswith("openai.codex_") for part in parts)


def _base_report():
    return {"diagnostic_schema": 1, "version": __version__, "frozen": bool(getattr(sys, "frozen", False)),
            "read_only": True, "adb_found": False, "sdk_source": "none", "sdk_candidates": [],
            "legacy_adb_found": False, "legacy_sdk_source": "none",
            "legacy_with_current_environment_source": "none", "launcher_sdk_environment": False,
            "possible_appdata_virtualization": False, "appdata_resolved_different": False,
            "preferences": {"exists": False, "readable": False, "enabled": True,
                            "explicit_configured": False, "preferred_device_configured": False},
            "adb_version": "", "adb_version_checked": False, "device_scan_complete": False,
            "adb_list_complete": False, "adb_listed_device_count": 0, "adb_listed_authorized_count": 0,
            "authorized_physical_count": 0, "physical_usb_count": 0, "unauthorized_count": 0,
            "observed_device_count": 0, "diagnostic_complete": False,
            "adb_probes": [], "adb_devices_probe": None,
            "errors": [], "forbidden_runtime_imports": []}


def collect_usb_diagnostics() -> dict:
    report = _base_report()
    local = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    preference_file = local / "VRization" / "usb.json"
    explicit = ""
    try:
        report["preferences"]["exists"] = preference_file.is_file()
        if report["preferences"]["exists"]:
            value = json.loads(preference_file.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Invalid preferences object")
            report["preferences"]["readable"] = True
            if type(value.get("enabled")) is bool:
                report["preferences"]["enabled"] = value["enabled"]
            if isinstance(value.get("adb_path"), str):
                explicit = value["adb_path"]
            report["preferences"]["explicit_configured"] = bool(explicit)
            report["preferences"]["preferred_device_configured"] = bool(value.get("preferred_serial"))
    except Exception as error:
        _error(report, "preferences", error)

    candidates = [("explicit", Path(explicit) if explicit else None),
                  ("android_home", Path(os.environ["ANDROID_HOME"]) / "platform-tools/adb.exe"
                   if os.environ.get("ANDROID_HOME") else None),
                  ("android_sdk_root", Path(os.environ["ANDROID_SDK_ROOT"]) / "platform-tools/adb.exe"
                   if os.environ.get("ANDROID_SDK_ROOT") else None),
                  ("standard", local / "Android/Sdk/platform-tools/adb.exe"),
                  ("managed", local / "VRization/tools/android-sdk/platform-tools/adb.exe")]
    portable = portable_adb_candidates()
    labels = ("portable_executable", "portable_container", "portable_archive")
    candidates.extend(zip(labels, portable))
    portable_roots = [path.parents[1].resolve() for path in portable]
    available = []
    launcher_environment = set()
    try:
        resolved = local.resolve()
        report["appdata_resolved_different"] = resolved != local.absolute()
        report["possible_appdata_virtualization"] = _virtualized(resolved) or _virtualized(preference_file.resolve())
    except Exception as error:
        _error(report, "appdata", error)
    for source, path in candidates:
        exists = False
        try:
            exists = path is not None and path.name.casefold() in ("adb", "adb.exe") and path.is_file()
            if path is not None:
                resolved = path.resolve()
                if exists and _virtualized(resolved):
                    report["possible_appdata_virtualization"] = True
                if source in ("android_home", "android_sdk_root") and resolved.parents[1] in portable_roots:
                    launcher_environment.add(source)
            if exists:
                available.append((source, resolved))
        except Exception as error:
            _error(report, "sdk_" + source, error)
        report["sdk_candidates"].append({"source": source, "configured": path is not None, "available": bool(exists)})
    report["launcher_sdk_environment"] = bool(launcher_environment)
    for source, _ in available:
        if not source.startswith("portable_"):
            report["legacy_with_current_environment_source"] = source
            break
    for source, _ in available:
        if not source.startswith("portable_") and source not in launcher_environment:
            report["legacy_adb_found"], report["legacy_sdk_source"] = True, source
            break
    try:
        selected = find_adb(explicit)
        if selected is not None:
            report["adb_found"] = True
            report["sdk_source"] = next((source for source, path in available if path == selected), "known_sdk")
            adb = AdbReverse(selected)
            original_runner = adb.runner
            original_presence_reader = adb.usb_presence.reader

            def read_command(command, **kwargs):
                result = original_runner(command, **kwargs)
                if command[1:] == ["devices", "-l"] and result.returncode == 0:
                    listed = parse_adb_devices(result.stdout)
                    report["adb_list_complete"] = True
                    report["adb_listed_device_count"] = len(listed)
                    report["adb_listed_authorized_count"] = sum(device.state == "device" for device in listed)
                return result

            def read_presence():
                try:
                    return original_presence_reader()
                except Exception as error:
                    _error(report, "usb_physical_proof", error)
                    raise

            # Observe the same scan without duplicate ADB calls or recording IDs.
            adb.runner, adb.usb_presence.reader = read_command, read_presence
            try:
                version = adb.command("version")
                report["adb_version_checked"] = True
                match = re.search(r"Android Debug Bridge version (\d+\.\d+\.\d+)", version)
                if match:
                    report["adb_version"] = match[1]
            except Exception as error:
                _error(report, "adb_version", error)
            try:
                devices = adb.devices()
                report["device_scan_complete"] = True
                report["observed_device_count"] = len(devices)
                report["physical_usb_count"] = sum(device.usb for device in devices)
                report["authorized_physical_count"] = sum(device.usb and device.state == "device" for device in devices)
                report["unauthorized_count"] = sum(device.state == "unauthorized" for device in devices)
            except Exception as error:
                _error(report, "adb_devices", error)
            report["adb_probes"] = list(getattr(adb, "recent_commands", ()))
            probe = getattr(adb, "last_devices_probe", None)
            report["adb_devices_probe"] = probe if isinstance(probe, dict) else None
    except Exception as error:
        _error(report, "adb_discovery", error)
    report["forbidden_runtime_imports"] = [prefix for prefix in FORBIDDEN_RUNTIME if any(
        name == prefix or name.startswith(prefix + ".") for name in sys.modules)]
    report["diagnostic_complete"] = True
    return report


def main(arguments: list[str]) -> int:
    # Avoid argparse stderr/traceback paths in a console=False frozen process.
    if len(arguments) != 2 or arguments[0] != "--usb-diagnostics" or not arguments[1]:
        return 2
    try:
        report = collect_usb_diagnostics()
    except Exception as error:
        report = _base_report()
        _error(report, "diagnostic", error)
    try:
        output = Path(arguments[1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except Exception:
        return 1
    return 0
