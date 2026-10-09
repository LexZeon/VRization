"""Keep verified public releases and an extracted, runnable latest Windows copy."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import time
from urllib.request import Request, urlopen
import uuid
import zipfile

REPO = "LexZeon/VRization"
ASSETS = {"VRization-Windows-x64.zip", "VRization-Android-debug.apk",
          "VRization-vr-core-alpha.aar", "VRization-Licenses.zip",
          "VRization-iOS-source.zip", "VRization-iOS-Simulator.zip"}


def fetch(url):
    if not url.startswith("https://"):
        raise ValueError("Only public HTTPS release downloads are accepted")
    return urlopen(Request(url, headers={"User-Agent": "VRization-Release-Archive"}), timeout=60)


def extract(archive_path, destination):
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            name = PurePosixPath(member.filename)
            target = (root / member.filename).resolve()
            mode = member.external_attr >> 16
            if (name.is_absolute() or ".." in name.parts or ":" in member.filename
                    or "\\" in member.filename or stat.S_ISLNK(mode)
                    or not target.is_relative_to(root)):
                raise ValueError(f"Unsafe archive entry: {member.filename}")
        archive.extractall(root)


def checksums(path):
    result = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(maxsplit=1)
        name = name.strip().removeprefix("*").removeprefix("./")
        if not re.fullmatch(r"[a-fA-F0-9]{64}", digest) or Path(name).name != name:
            raise ValueError("Invalid release checksum manifest")
        result[name] = digest.lower()
    return result


def download(url, target, expected=None):
    if target.exists() and expected:
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Existing archive differs from public checksum: {target.name}")
        return
    temporary = target.with_name(target.name + ".partial")
    with fetch(url) as response, temporary.open("wb") as stream:
        shutil.copyfileobj(response, stream)
    if expected and hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Downloaded checksum differs: {target.name}")
    temporary.replace(target)


def prepare_release(root, release):
    tag = release["tag_name"]
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", tag):
        raise ValueError("Unsupported release tag")
    folder = root / "versions" / tag
    downloads = folder / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    assets = {item["name"]: item for item in release["assets"]}
    manifest = assets.get("SHA256SUMS.txt")
    if not manifest:
        raise ValueError(f"{tag} has no published checksum manifest")
    download(manifest["browser_download_url"], downloads / "SHA256SUMS.txt")
    hashes = checksums(downloads / "SHA256SUMS.txt")
    verified = set()
    for name in sorted(ASSETS & assets.keys()):
        if name not in hashes:
            raise ValueError(f"{tag} omits a checksum for {name}")
        download(assets[name]["browser_download_url"], downloads / name, hashes[name])
        verified.add(name)
    windows = downloads / "VRization-Windows-x64.zip"
    executable_hash = None
    if windows.name in verified:
        extract(windows, folder / "Windows")
        # A stale extracted EXE must not make a new archive without an EXE
        # runnable. Derive its identity from the verified ZIP itself.
        with zipfile.ZipFile(windows) as archive:
            if "VRization-Host.exe" in archive.namelist():
                executable_hash = hashlib.sha256(archive.read("VRization-Host.exe")).hexdigest()
    for asset, target in (("VRization-Android-debug.apk", "Android"),
                          ("VRization-iOS-source.zip", "iOS-source"),
                          ("VRization-iOS-Simulator.zip", "iOS-Simulator")):
        source = downloads / asset
        if asset in verified:
            (folder / target).mkdir(exist_ok=True)
            shutil.copy2(source, folder / target / asset)
    metadata = {"tag": tag, "release": release["html_url"], "checksums": hashes,
                "verifiedAssets": sorted(verified), "windowsExecutableSHA256": executable_hash}
    (folder / ".vrization-archive.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Verified and archived {tag}", flush=True)
    return folder


def publish_latest(root, folder):
    latest = root / "latest"
    metadata = json.loads((folder / ".vrization-archive.json").read_text(encoding="utf-8"))
    executable = folder / "Windows" / "VRization-Host.exe"
    executable_hash = metadata.get("windowsExecutableSHA256")
    if ("VRization-Windows-x64.zip" not in metadata.get("verifiedAssets", [])
            or not isinstance(executable_hash, str)
            or not re.fullmatch(r"[a-f0-9]{64}", executable_hash)
            or not executable.is_file()
            or hashlib.sha256(executable.read_bytes()).hexdigest() != executable_hash):
        raise ValueError("Selected latest has no verified Windows executable")
    if latest.resolve().parent != root:
        raise ValueError("Archive paths escaped the destination")
    if latest.exists() and not (latest / ".vrization-archive.json").is_file():
        raise ValueError("Existing latest folder is not managed by this script")
    verified = set(metadata["verifiedAssets"])
    hashes = metadata["checksums"]
    source_downloads = folder / "downloads"
    if checksums(source_downloads / "SHA256SUMS.txt") != hashes:
        raise ValueError("Archived checksum manifest changed")
    for name in verified:
        if (name not in ASSETS or name not in hashes
                or hashlib.sha256((source_downloads / name).read_bytes()).hexdigest() != hashes[name]):
            raise ValueError("Archived release asset changed")
    staging = root / (".latest-staging-" + uuid.uuid4().hex)
    # Rebuild from this release's verified downloads. Never copy an old extracted
    # tree: it can retain an unpublished APK or a DLL absent from the new ZIP.
    staging.mkdir()
    staged_downloads = staging / "downloads"
    staged_downloads.mkdir()
    shutil.copy2(source_downloads / "SHA256SUMS.txt", staged_downloads / "SHA256SUMS.txt")
    for name in sorted(verified):
        target = staged_downloads / name
        shutil.copy2(source_downloads / name, target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != hashes[name]:
            raise ValueError("Release asset changed while copying")
    extract(staged_downloads / "VRization-Windows-x64.zip", staging / "Windows")
    for asset, target in (("VRization-Android-debug.apk", "Android"),
                          ("VRization-iOS-source.zip", "iOS-source"),
                          ("VRization-iOS-Simulator.zip", "iOS-Simulator")):
        if asset in verified:
            (staging / target).mkdir()
            shutil.copy2(staged_downloads / asset, staging / target / asset)
    (staging / ".vrization-archive.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    # Separately installed official tools live outside all public release assets.
    # setlocal scopes these SDK variables to this launcher and its child app.
    launcher = ('@echo off\r\nsetlocal\r\n'
                'if exist "%~dp0..\\tools\\android-sdk\\platform-tools\\adb.exe" (\r\n'
                '  set "ANDROID_HOME=%~dp0..\\tools\\android-sdk"\r\n'
                '  set "ANDROID_SDK_ROOT=%~dp0..\\tools\\android-sdk"\r\n'
                ')\r\nstart "" "%~dp0Windows\\VRization-Host.exe"')
    (staging / "Start-Windows.bat").write_bytes((launcher + '\r\nendlocal\r\n').encode("ascii"))
    (staging / "Start-on-second-monitor.bat").write_bytes((launcher + ' --monitor 2\r\nendlocal\r\n').encode("ascii"))
    # Never delete or overwrite an unowned user directory. All directory moves
    # resolve to siblings inside this explicit archive root before execution.
    if staging.resolve().parent != root or latest.resolve().parent != root:
        raise ValueError("Archive paths escaped the destination")
    if latest.exists():
        previous = root / ("previous-latest-" + time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
        if previous.resolve().parent != root:
            raise ValueError("Backup path escaped the destination")
        latest.rename(previous)
    staging.rename(latest)
    (root / "OPEN-ME.html").write_text("""<!doctype html><meta charset="utf-8">
<title>VRization downloads / 下载</title><style>body{font:17px system-ui;max-width:820px;margin:50px auto;padding:20px;line-height:1.7}a{color:#08786e}code{background:#eee;padding:3px}</style>
<h1>🥽 VRization — English</h1><p>Latest version: <strong>""" + html.escape(folder.name) + """</strong></p>
<p>Open <a href="latest/">latest</a>. Double-click <code>Start-Windows.bat</code> to run the extracted Windows app. The second-monitor launcher selects display 2; verify its name. Install the APK in <code>latest/Android</code> on Android.</p>
<p>iOS source needs Xcode and your Apple signing for an iPhone. The Simulator download is for a Mac Simulator and cannot be installed on a phone. See <a href="latest/Windows/docs/IOS.md">the iOS guide</a>. Older verified versions remain in <a href="versions/">versions</a>; original downloads and SHA-256 checksums are retained.</p>
<hr><h1>🥽 VRization — 简体中文</h1><p>最新版：<strong>""" + html.escape(folder.name) + """</strong></p>
<p>打开 <a href="latest/">latest 最新版</a>，双击 <code>Start-Windows.bat</code> 运行已解压的 Windows 程序。另一个启动器选择编号 2 的显示器，请核对名称。<code>latest/Android</code> 内的 APK 用于 Android 手机安装。</p>
<p>iOS 源码需要用 Xcode 和自己的 Apple 签名安装到 iPhone；模拟器下载仅用于 Mac 模拟器，不能装到手机。参见 <a href="latest/Windows/docs/IOS.md">iOS 教程</a>。<a href="versions/">versions</a> 保留旧版及原始下载与 SHA-256 校验。</p>""", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--latest-tag")
    args = parser.parse_args()
    root = args.destination.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    with fetch(f"https://api.github.com/repos/{REPO}/releases?per_page=100") as response:
        releases = [release for release in json.load(response) if not release["draft"]]
    if not releases:
        raise ValueError("No public releases available")
    latest_tag = args.latest_tag or releases[0]["tag_name"]
    selected = None
    for release in reversed(releases):
        folder = prepare_release(root, release)
        if release["tag_name"] == latest_tag:
            selected = folder
    if selected is None:
        raise ValueError("Requested latest tag is not a public release")
    publish_latest(root, selected)
    print(f"Runnable Windows latest and historical downloads: {root}", flush=True)


if __name__ == "__main__":
    main()
