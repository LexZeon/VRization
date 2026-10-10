"""Package the separate preview without changing or replacing stable assets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
from package_release import check_document_links
from build_steamvr_native import COMMIT,PINS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"artifacts/steamvr/release"


def tracked_files():
    names=subprocess.check_output(["git","ls-files","-z"],cwd=ROOT).decode().split("\0")
    return [ROOT/name for name in names if name and (ROOT/name).is_file()]


def docs(archive):
    for path in tracked_files():
        name=path.relative_to(ROOT).as_posix()
        if path.suffix==".md" or name in {"LICENSE","NOTICE"} or name.startswith(("licenses/","docs/","examples/","experimental/steamvr/")) or name=="desktop/requirements-lock.txt":
            archive.write(path,name)


def windows():
    native=ROOT/"artifacts/steamvr/native-bundle"
    required=("native/VRization-SteamVR-Mirror.exe","native/VRization-SteamVR-Overlay.exe",
              "native/VRization-SteamVR-IPC.dll","native/openvr_api.dll",
              "drivers/vrization_phone/bin/win64/driver_vrization_phone.dll",
              "drivers/vrization_phone/driver.vrdrivermanifest",
              "drivers/vrization_phone/resources/settings/default.vrsettings",
              "native/licenses/OpenVR-LICENSE.txt","native/licenses/VRization-MIT.txt",
              "native/README.md","native/licenses/README.md","native-build-report.json")
    for name in required:
        if not (native/name).is_file():raise FileNotFoundError(f"Incomplete native bundle: {name}")
    report=json.loads((native/"native-build-report.json").read_text(encoding="utf-8"))
    if report.get("sdkCommit")!=COMMIT or report.get("sdkPins")!=PINS or report.get("ctestExecuted") is not True or report.get("configuration")!="Release":
        raise ValueError("Native bundle needs a passing Release build of the pinned SDK")
    for name in required[:-1]:
        if report.get("files",{}).get(name)!=hashlib.sha256((native/name).read_bytes()).hexdigest():
            raise ValueError(f"Native report does not match {name}")
    for name,pin in (("native/openvr_api.dll",PINS["bin/win64/openvr_api.dll"]),("native/licenses/OpenVR-LICENSE.txt",PINS["LICENSE"])):
        if hashlib.sha256((native/name).read_bytes()).hexdigest()!=pin:raise ValueError("Upstream binary/license changed")
    binaries={path.relative_to(native).as_posix() for path in native.rglob("*") if path.suffix.lower() in {".dll",".exe",".lib"}}
    if binaries!={name for name in required if Path(name).suffix in {".dll",".exe"}}:raise ValueError("Unexpected native binary; preserve and review the bundle")
    executable=ROOT/"artifacts/steamvr/windows-dist/VRization-SteamVR.exe"
    if not executable.is_file():raise FileNotFoundError("Build the separate Windows preview first")
    archive_path=OUT/"VRization-SteamVR-Windows-x64.zip"
    with zipfile.ZipFile(archive_path,"w",zipfile.ZIP_DEFLATED) as archive:
        archive.write(executable,executable.name)
        for file in sorted(native.rglob("*")):
            if file.is_file():archive.write(file,file.relative_to(native).as_posix())
        launcher=('@echo off\r\nsetlocal\r\n'
                  'if exist "%~dp0tools\\android-sdk\\platform-tools\\adb.exe" (\r\n'
                  '  set "ANDROID_HOME=%~dp0tools\\android-sdk"\r\n'
                  '  set "ANDROID_SDK_ROOT=%~dp0tools\\android-sdk"\r\n)\r\n'
                  'start "" "%~dp0VRization-SteamVR.exe"{args}\r\nendlocal\r\n')
        archive.writestr("Start-SteamVR-Preview.bat",launcher.format(args=""))
        archive.writestr("Start-SteamVR-Preview-second-monitor.bat",launcher.format(args=" --monitor 2"))
        docs(archive)
    check_document_links(archive_path)


def android():
    apk=ROOT/"android/steamvr-app/build/outputs/apk/steamvr/debug/steamvr-app-steamvr-debug.apk"
    aar=ROOT/"android/vr-core/build/outputs/aar/vr-core-debug.aar"
    shutil.copyfile(apk,OUT/"VRization-SteamVR-Android-debug.apk")
    shutil.copyfile(aar,OUT/"VRization-SteamVR-vr-core.aar")


def source():
    path=OUT/"VRization-SteamVR-iOS-source.zip"
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as archive:
        for file in tracked_files():archive.write(file,file.relative_to(ROOT).as_posix())
    check_document_links(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows-only",action="store_true")
    parser.add_argument("--android-only",action="store_true")
    parser.add_argument("--source-only",action="store_true")
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    if args.windows_only:windows()
    elif args.android_only:android()
    elif args.source_only:source()
    else:
        windows();android();source()
        shutil.copyfile(ROOT/"artifacts/ios-steamvr/VRization-SteamVR-iOS-Simulator.zip",OUT/"VRization-SteamVR-iOS-Simulator.zip")
        with zipfile.ZipFile(OUT/"VRization-SteamVR-Licenses.zip","w",zipfile.ZIP_DEFLATED) as archive:docs(archive)
        check_document_links(OUT/"VRization-SteamVR-Licenses.zip")
        files=sorted(path for path in OUT.iterdir() if path.is_file() and path.name!="SHA256SUMS.txt")
        (OUT/"SHA256SUMS.txt").write_text("".join(hashlib.sha256(path.read_bytes()).hexdigest()+"  "+path.name+"\n" for path in files),encoding="utf-8")
        print(json.dumps({path.name:path.stat().st_size for path in files},indent=2))


if __name__=="__main__":main()
