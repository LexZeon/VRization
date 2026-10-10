"""Keep every preview under a separate archive; never touch stable latest."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
import uuid
from archive_releases import download,extract,checksums,fetch,REPO

ASSETS={"VRization-SteamVR-Windows-x64.zip","VRization-SteamVR-Android-debug.apk",
        "VRization-SteamVR-vr-core.aar","VRization-SteamVR-Licenses.zip",
        "VRization-SteamVR-iOS-source.zip","VRization-SteamVR-iOS-Simulator.zip"}


def prepare(root,release):
    import re
    tag=release["tag_name"]
    if not re.fullmatch(r"v\d+\.\d+\.\d+-steamvr[-a-zA-Z0-9.]*",tag):raise ValueError("Not a SteamVR preview tag")
    folder=root/"versions"/tag;downloads=folder/"downloads";downloads.mkdir(parents=True,exist_ok=True)
    assets={item["name"]:item for item in release["assets"]}
    if not ASSETS<=assets.keys() or "SHA256SUMS.txt" not in assets:raise ValueError("Incomplete public preview")
    download(assets["SHA256SUMS.txt"]["browser_download_url"],downloads/"SHA256SUMS.txt")
    hashes=checksums(downloads/"SHA256SUMS.txt")
    for name in sorted(ASSETS):
        download(assets[name]["browser_download_url"],downloads/name,hashes[name])
    extract(downloads/"VRization-SteamVR-Windows-x64.zip",folder/"Windows")
    if not (folder/"Windows/VRization-SteamVR.exe").is_file():raise ValueError("No preview executable")
    metadata={"channel":"steamvr-experimental","tag":tag,"release":release["html_url"],"checksums":hashes}
    (folder/".vrization-steamvr-archive.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    return folder


def publish_latest(root,folder):
    latest=root/"latest";staging=root/(".preview-staging-"+uuid.uuid4().hex)
    if latest.exists() and not (latest/".vrization-steamvr-archive.json").is_file():raise ValueError("Unmanaged latest directory preserved")
    if any(path.resolve().parent!=root for path in (staging,latest)):raise ValueError("Archive path escaped preview directory")
    staging.mkdir();downloads=staging/"downloads";downloads.mkdir()
    metadata=json.loads((folder/".vrization-steamvr-archive.json").read_text(encoding="utf-8"))
    for name in sorted(ASSETS|{"SHA256SUMS.txt"}):
        target=downloads/name;shutil.copy2(folder/"downloads"/name,target)
        if name in ASSETS and hashlib.sha256(target.read_bytes()).hexdigest()!=metadata["checksums"][name]:raise ValueError("Preview changed while copying")
    extract(downloads/"VRization-SteamVR-Windows-x64.zip",staging/"Windows")
    launcher=('@echo off\r\nsetlocal\r\n'
        'if exist "%~dp0..\\..\\tools\\android-sdk\\platform-tools\\adb.exe" (\r\n'
        '  set "ANDROID_HOME=%~dp0..\\..\\tools\\android-sdk"\r\n'
        '  set "ANDROID_SDK_ROOT=%~dp0..\\..\\tools\\android-sdk"\r\n)\r\n'
        'start "" "%~dp0Windows\\VRization-SteamVR.exe"\r\nendlocal\r\n')
    (staging/"Start-SteamVR-Preview.bat").write_bytes(launcher.encode("ascii"))
    (staging/".vrization-steamvr-archive.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    if latest.exists():
        backup=root/("previous-latest-"+time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6])
        if backup.resolve().parent!=root:raise ValueError("Backup path escaped preview directory")
        latest.rename(backup)
    staging.rename(latest)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination",type=Path,required=True,help="Explicit separate SteamVR archive directory")
    parser.add_argument("--latest-tag",required=True)
    args=parser.parse_args();root=args.destination.expanduser().resolve()
    # The explicit channel subdirectory is required even for custom roots.
    if root.name!="steamvr-experimental":raise ValueError("Destination must end in steamvr-experimental; stable latest is protected")
    root.mkdir(parents=True,exist_ok=True)
    with fetch(f"https://api.github.com/repos/{REPO}/releases?per_page=100") as response:releases=json.load(response)
    selected=None
    for release in reversed(releases):
        if not release["draft"] and "steamvr" in release["tag_name"]:
            folder=prepare(root,release)
            if release["tag_name"]==args.latest_tag:selected=folder
    if selected is None:raise ValueError("Requested preview tag is not public")
    publish_latest(root,selected);print(f"Separate runnable preview and history: {root}")


if __name__=="__main__":main()
