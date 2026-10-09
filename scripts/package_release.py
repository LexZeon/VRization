"""Package binaries and complete offline documentation; never publish keys."""
import argparse
import hashlib
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def add_tree(archive, path, name=None):
    if path.is_dir():
        for file in sorted(path.rglob("*")):
            if (file.is_file() and "__pycache__" not in file.parts
                    and file.suffix not in {".pyc", ".pyo"}):
                archive.write(file, file.relative_to(ROOT).as_posix())
    else:
        archive.write(path, name or path.relative_to(ROOT).as_posix())


def check_document_links(path):
    """Reject a ZIP with missing targets in its included Markdown pages."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        for name in names:
            if not name.endswith(".md") or "/LICENSE" in name:
                continue
            prose = re.sub(r"```.*?```", "", archive.read(name).decode("utf-8"), flags=re.S)
            for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", prose):
                target = match.group(1).strip().split(' "', 1)[0].strip("<>")
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                destination = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
                if destination not in names and not any(item.startswith(destination.rstrip("/") + "/") for item in names):
                    raise ValueError(f"{path.name}: {name} links to missing {destination}")


def package_windows(out):
    path = out / "VRization-Windows-x64.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        add_tree(archive, ROOT / "desktop/dist/VRization-Host.exe", "VRization-Host.exe")
        launcher = ('@echo off\r\nsetlocal\r\n'
                    'if exist "%~dp0tools\\android-sdk\\platform-tools\\adb.exe" (\r\n'
                    '  set "ANDROID_HOME=%~dp0tools\\android-sdk"\r\n'
                    '  set "ANDROID_SDK_ROOT=%~dp0tools\\android-sdk"\r\n'
                    ')\r\nstart "" "%~dp0VRization-Host.exe"{arguments}\r\nendlocal\r\n')
        archive.writestr("Start-Windows.bat", launcher.format(arguments=""))
        archive.writestr("Start-on-second-monitor.bat", launcher.format(arguments=" --monitor 2"))
        for page in sorted(ROOT.glob("*.md")):
            add_tree(archive, page)
        for name in ("LICENSE", "NOTICE", "docs", "licenses", "examples", "desktop/requirements-lock.txt"):
            add_tree(archive, ROOT / name)
    check_document_links(path)


def package_android(out, core_variant):
    shutil.copyfile(ROOT / "android/app/build/outputs/apk/debug/app-debug.apk", out / "VRization-Android-debug.apk")
    shutil.copyfile(ROOT / f"android/vr-core/build/outputs/aar/vr-core-{core_variant}.aar", out / "VRization-vr-core-alpha.aar")
    path = out / "VRization-Licenses.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "licenses", "desktop/requirements-lock.txt"):
            add_tree(archive, ROOT / name)
    check_document_links(path)


def package_ios_source(out):
    path = out / "VRization-iOS-source.zip"
    # Complete, editable project and core, not an unsigned IPA presented as installable.
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "docs", "licenses",
                     "examples", "desktop/requirements-lock.txt", "desktop/pyproject.toml", "desktop/src"):
            add_tree(archive, ROOT / name)
        for page in sorted(ROOT.glob("*.md")):
            if page.name != "THIRD_PARTY_NOTICES.md":
                add_tree(archive, page)
        for name in (ROOT / "ios").rglob("*"):
            if name.is_file() and not any(part in {".build", ".swiftpm", "xcuserdata", "DerivedData"}
                                          for part in name.relative_to(ROOT / "ios").parts):
                add_tree(archive, name)
        for name in ("scripts/build_ios.py", "scripts/ios_test_host.py", "scripts/ios_usb_fixture.py", "scripts/package_release.py"):
            add_tree(archive, ROOT / name)
    check_document_links(path)


def package_ios(out):
    package_ios_source(out)
    app = ROOT / "artifacts/ios/simulator/Build/Products/Debug-iphonesimulator/VRizationApp.app"
    if not app.is_dir():
        raise FileNotFoundError("Build the iOS Simulator app on macOS before packaging")
    subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app),
                    str(out / "VRization-iOS-Simulator.zip")], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--windows-only", action="store_true")
    selection.add_argument("--android-only", action="store_true")
    selection.add_argument("--ios-only", action="store_true")
    selection.add_argument("--ios-source-only", action="store_true")
    parser.add_argument("--core-variant", choices=("debug", "release"), default="release")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/release")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.ios_only:
        package_ios(out)
    elif args.ios_source_only:
        package_ios_source(out)
    elif not args.android_only:
        package_windows(out)
    if not (args.windows_only or args.ios_only or args.ios_source_only):
        package_android(out, args.core_variant)
    assets = [path for path in sorted(out.iterdir()) if path.name in {
        "VRization-Windows-x64.zip", "VRization-Android-debug.apk",
        "VRization-vr-core-alpha.aar", "VRization-Licenses.zip",
        "VRization-iOS-source.zip", "VRization-iOS-Simulator.zip"}]
    (out / "SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in assets), encoding="utf-8")
    for path in assets:
        print(f"{path.name}: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
