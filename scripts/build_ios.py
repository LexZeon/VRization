"""Build and exercise the iOS app on macOS; no Apple signing secrets required."""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import re
import signal
from statistics import median
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


def check_rendered_card_colors():
    """Check actual Metal screenshots from both transports against the original card.

    Native screenshot EXIF is honored. Sampling opaque, flat card regions detects
    a skipped-alpha/channel upload error; the upper heading also checks row origin.
    No screenshot is modified or substituted for the exported test evidence.
    """
    from PIL import Image, ImageOps

    folder = OUT / "screenshots"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    attachments = [item for group in manifest for item in group["attachments"]]
    records, failures = [], []
    for name in ("05-full-stereo-Metal", "USB-02-real-Metal-stereo"):
        matches = [item for item in attachments if item["suggestedHumanReadableName"].startswith(name + "_")]
        if len(matches) != 1:
            raise AssertionError(f"Expected one real screenshot for {name}; found {len(matches)}")
        with Image.open(folder / matches[0]["exportedFileName"]) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
        width, height = image.size
        if width <= height:
            raise AssertionError(f"{name}: the physical screen is not landscape")
        left_width = width // 2
        for eye in range(2):
            eye_width = left_width if eye == 0 else width - left_width
            origin = 0 if eye == 0 else left_width
            fit_y = min(1.0, (eye_width / height) / (1280 / 720))
            sign = -1 if eye == 0 else 1

            def point(u, v):
                # Default full mode, scale .85, eye separation .03, no offsets
                # or distortion: match the displayed card's placement.
                x = origin + eye_width * (.5 + ((u * 2 - 1) * .85 + sign * .03) / 2)
                y = height * (.5 - ((1 - v * 2) * fit_y * .85) / 2)
                return round(x), round(y)

            for uv, expected in (((.97, .05), (13, 21, 40)), ((.8, .4), (20, 38, 60)), ((.8, .65), (20, 38, 60))):
                x, y = point(*uv)
                neighborhood = [image.getpixel((x + dx, y + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
                actual = tuple(round(median(pixel[channel] for pixel in neighborhood)) for channel in range(3))
                records.append({"screenshot": name, "eye": eye, "sourceUV": uv,
                                "screenXY": (x, y), "expectedRGB": expected, "actualRGB": actual})
                if max(abs(a - b) for a, b in zip(actual, expected)) > 12:
                    failures.append(f"{name} eye {eye}: RGB {actual}, expected near {expected}")
            x0, y0 = point(.15, .24)
            x1, y1 = point(.58, .40)
            heading = image.crop((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
            teal = sum(g > 150 and g - r > 60 and b > 100 for r, g, b in heading.get_flattened_data())
            records.append({"screenshot": name, "eye": eye, "upperHeadingTealPixels": teal})
            if teal < 40:
                failures.append(f"{name} eye {eye}: the upper teal heading is missing or upside down")
    (folder / "color-check.json").write_text(json.dumps({"samples": records, "failures": failures}, indent=2), encoding="utf-8")
    assert not failures, "; ".join(failures)
    print("Both real LAN/USB Metal screenshots preserve card RGB, row origin and both eyes.", flush=True)


def check_rendered_seam(report):
    """Inspect the original fullscreen Metal screenshot after a negative-gap Save."""
    from PIL import Image, ImageOps

    folder = OUT / "screenshots"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    attachments = [item for group in manifest for item in group["attachments"]]
    matches = [item for item in attachments if item["suggestedHumanReadableName"].startswith("EDITOR-05-negative-seam-Metal_")]
    assert len(matches) == 1, "Missing real negative-separation Metal screenshot"
    saved = next(item["settings"] for item in report["checkpoints"] if item["name"] == "editor-saved")
    with Image.open(folder / matches[0]["exportedFileName"]) as raw:
        image = ImageOps.exif_transpose(raw).convert("RGB")
    width, height = image.size
    assert width > height, "Contact screenshot is not landscape"
    middle = width // 2
    samples, failures = [], []
    for eye in range(2):
        eye_width = middle if eye == 0 else width - middle
        fit_x = min(1, (1280 / 720) / (eye_width / height))
        fit_y = min(1, (eye_width / height) / (1280 / 720))
        half_width = fit_x * saved["scale"]
        separation = max(half_width - 1, saved["eyeSeparation"])
        assert abs(1 + separation - half_width) < 1e-6 and abs(saved["offsetX"]) < 1e-6, "Saved profile does not reach contact"
        # Source V=.43 avoids the original card's horizontal grid lines. These
        # points lie immediately on either side of the physical eye boundary.
        x = middle - 4 if eye == 0 else middle + 4
        y = round(height * (.5 - ((1 - 2 * .43) * fit_y * saved["scale"] + saved["offsetY"]) / 2))
        pixels = [image.getpixel((x + dx, y + dy)) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
        actual = tuple(round(median(pixel[channel] for pixel in pixels)) for channel in range(3))
        expected = (13, 22, 41)
        boundary_x = middle - 1 if eye == 0 else middle
        boundary = [image.getpixel((boundary_x, y + dy)) for dy in (-1, 0, 1)]
        samples.append({"eye": eye, "screenXY": (x, y), "expectedRGB": expected,
                        "actualRGB": actual, "boundaryRGB": boundary})
        if max(abs(a - b) for a, b in zip(actual, expected)) > 12:
            failures.append(f"Eye {eye} has a gap or wrong video at the seam: {actual}")
        if any(pixel[2] <= 20 or sum(pixel) <= 35 for pixel in boundary):
            failures.append(f"Eye {eye} has black pixels at its exact viewport boundary")
    (folder / "seam-check.json").write_text(json.dumps({"samples": samples, "failures": failures}, indent=2), encoding="utf-8")
    assert not failures, "; ".join(failures)
    print("The real Metal screenshot has video on both sides of the contact seam.", flush=True)


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
    checkpoints = {item["name"]: item for item in report["checkpoints"]}
    before = checkpoints["editor-entry"]
    for name in ("editor-discard-preview", "editor-discarded"):
        assert checkpoints[name]["settingsCount"] == before["settingsCount"], "Editor preview/discard sent settings"
        assert checkpoints[name]["settings"] == before["settings"], "Editor preview/discard changed host settings"
    saved = checkpoints["editor-saved"]
    assert saved["settingsCount"] == before["settingsCount"] + 1, "Editor Save was not one real settings transaction"
    assert saved["settings"]["scale"] != before["settings"]["scale"], "Real corner drag did not resize the saved image"
    assert saved["settings"]["eyeSeparation"] < 0, "Real inward eye drag did not save negative spacing"
    assert abs(saved["settings"]["eyeSeparation"] - (saved["settings"]["scale"] - 1)) < 1e-6, "Resizing joined images did not preserve contact"
    assert saved["settings"]["offsetX"] == 0, "Contact did not align the common horizontal offset"
    desktop = checkpoints["editor-desktop-updated"]
    assert desktop["settingsCount"] == saved["settingsCount"] + 1 and desktop["settings"]["scale"] == .78, "Real PC update was not broadcast"
    assert checkpoints["editor-local-restored"]["settings"]["scale"] != saved["settings"]["scale"], "Offline phone profile was not restored over old host state"
    check_rendered_card_colors()
    check_rendered_seam(report)
    run("python3", "scripts/package_release.py", "--ios-only")


if __name__ == "__main__":
    main()
