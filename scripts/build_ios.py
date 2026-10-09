"""Build and exercise the iOS app on macOS; no Apple signing secrets required."""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/ios"


def run(*args, **kwargs):
    print("+ " + " ".join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), cwd=ROOT, check=True, **kwargs)


def run_with_deadline(*args, timeout):
    """Bound the complete UI phase, including a hung simulator/test runner startup."""
    command = list(map(str, args))
    print("+ " + " ".join(command), flush=True)
    process = subprocess.Popen(command, cwd=ROOT, start_new_session=True)
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # xcodebuild starts runner helpers. Stop the group so they cannot outlive
        # the fixture cleanup or keep a timed-out GitHub job running indefinitely.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        raise
    if code:
        raise subprocess.CalledProcessError(code, command)


def export_ui_report():
    result = OUT / "UI.xcresult"
    if not result.exists():
        return
    screenshots = OUT / "screenshots"
    screenshots.mkdir(exist_ok=True)
    # Export errors must not replace the original test failure (or timeout).
    try:
        run("xcrun", "xcresulttool", "export", "attachments", "--path", result,
            "--output-path", screenshots, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"Warning: could not export UI attachments: {type(error).__name__}", flush=True)
    try:
        summary = run("xcrun", "xcresulttool", "get", "test-results", "summary", "--path", result,
                      capture_output=True, text=True, timeout=30)
        payload = json.loads(summary.stdout)
        (screenshots / "test-summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as error:
        print(f"Warning: could not export UI summary: {type(error).__name__}", flush=True)


def main():
    if sys.platform != "darwin":
        raise SystemExit("This script requires macOS with Xcode. The Windows host has a separate build script.")
    OUT.mkdir(parents=True, exist_ok=True)
    # Hosted runners may default to an older Xcode with no matching runtime.
    # Honor an explicit selection; otherwise use the newest installed stable Xcode.
    if not os.environ.get("DEVELOPER_DIR"):
        candidates = []
        for app in Path("/Applications").glob("Xcode_*.app"):
            match = re.fullmatch(r"Xcode_([0-9.]+)\.app", app.name)
            if match:
                candidates.append((tuple(map(int, match[1].split("."))), app))
        if candidates:
            os.environ["DEVELOPER_DIR"] = str(max(candidates)[1] / "Contents/Developer")
    run("xcodebuild", "-version")
    run("swift", "test", "--package-path", "ios")
    common = ["xcodebuild", "-project", "ios/VRization.xcodeproj", "-scheme", "VRization",
              "-configuration", "Debug", "CODE_SIGNING_ALLOWED=NO", "-quiet"]
    simulator_arch = platform.machine()
    run(*common, f"ARCHS={simulator_arch}", "ONLY_ACTIVE_ARCH=YES", "-destination", "generic/platform=iOS Simulator",
        "-derivedDataPath", OUT / "simulator", "build")
    run(*common, "-destination", "generic/platform=iOS", "-derivedDataPath", OUT / "device", "build")
    result = run("xcrun", "simctl", "list", "devices", "available", "--json", capture_output=True, text=True)
    devices = json.loads(result.stdout)["devices"]
    phones = []
    for runtime, rows in devices.items():
        if ".iOS-" in runtime:
            version = tuple(map(int, re.findall(r"\d+", runtime.split(".iOS-", 1)[1])))
            for row in rows:
                if row.get("isAvailable") and row["name"].startswith("iPhone"):
                    generation = tuple(map(int, re.findall(r"\d+", row["name"]))) or (0,)
                    phones.append((version, generation, row["name"], row["udid"]))
    if not phones:
        raise SystemExit("No available iPhone simulator runtime. Install one in Xcode Settings > Components.")
    runtime, _, name, device = max(phones)
    (OUT / "environment.json").write_text(json.dumps({"simulator": name, "runtime": runtime,
        "architecture": simulator_arch, "developerDirectory": os.environ.get("DEVELOPER_DIR")}, indent=2), encoding="utf-8")
    print(f"Testing on {name}, iOS {'.'.join(map(str, runtime))}", flush=True)
    # The previous hosted run never reached a test: AX initialization failed
    # while XCTest was cold-booting its simulator. Complete boot and open the
    # matching Simulator first; this is a readiness step, not a passing UI test.
    run("xcrun", "simctl", "bootstatus", device, "-b", timeout=180)
    simulator_app = Path(os.environ.get("DEVELOPER_DIR", "/Applications/Xcode.app/Contents/Developer")) / "Applications/Simulator.app"
    run("open", "-a", simulator_app, "--args", "-CurrentDeviceUDID", device, timeout=30)
    fixture = subprocess.Popen([sys.executable, str(ROOT / "scripts/ios_test_host.py"),
        "--report", str(OUT / "host-report.json"), "--usb-fixture"], cwd=ROOT)
    try:
        for _ in range(60):
            if fixture.poll() is not None:
                raise RuntimeError("Synthetic fixture stopped before test startup")
            try:
                with urlopen("http://127.0.0.1:18765/health", timeout=1):
                    break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("Synthetic fixture did not become ready")
        run_with_deadline(*common, f"ARCHS={simulator_arch}", "ONLY_ACTIVE_ARCH=YES", "-destination", f"platform=iOS Simulator,id={device},arch={simulator_arch}",
            "-derivedDataPath", OUT / "simulator", "-parallel-testing-enabled", "NO",
            "-test-timeouts-enabled", "YES", "-default-test-execution-time-allowance", "300",
            "-maximum-test-execution-time-allowance", "300", "-destination-timeout", "120",
            "-resultBundlePath", OUT / "UI.xcresult", "test", timeout=900)
    finally:
        fixture.terminate()
        try:
            fixture.wait(timeout=15)
        except subprocess.TimeoutExpired:
            fixture.kill()
            fixture.wait()
        export_ui_report()
    report = json.loads((OUT / "host-report.json").read_text(encoding="utf-8"))
    assert not report["mouseMoves"], "The fixture must never move the OS mouse"
    assert any(event["event"] == "connection" and event.get("connected") for event in report["events"]), "UI tests never connected to the host"
    assert any(event["event"] == "settings" for event in report["events"]), "UI tests never synchronized settings"
    run("python3", "scripts/package_release.py", "--ios-only")


if __name__ == "__main__":
    main()
