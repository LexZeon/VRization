"""Package the locally verified binaries without publishing credentials or keys."""
from pathlib import Path
import hashlib
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "release"
OUT.mkdir(parents=True, exist_ok=True)


def add_tree(archive, path, name=None):
    if path.is_dir():
        for file in sorted(path.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(ROOT).as_posix())
    else:
        archive.write(path, name or path.relative_to(ROOT).as_posix())


with zipfile.ZipFile(OUT / "VRization-Windows-x64.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    add_tree(archive, ROOT / "desktop/dist/VRization-Host.exe", "VRization-Host.exe")
    archive.writestr("Start-on-second-monitor.bat", '@echo off\r\nstart "" "%~dp0VRization-Host.exe" --monitor 2\r\n')
    for name in ("README.md", "README.en.md", "LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "docs", "licenses"):
        add_tree(archive, ROOT / name)
shutil.copyfile(ROOT / "android/app/build/outputs/apk/debug/app-debug.apk", OUT / "VRization-Android-debug.apk")
shutil.copyfile(ROOT / "android/vr-core/build/outputs/aar/vr-core-release.aar", OUT / "VRization-vr-core-alpha.aar")
with zipfile.ZipFile(OUT / "VRization-Licenses.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for name in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "licenses"):
        add_tree(archive, ROOT / name)
files = sorted(path for path in OUT.iterdir() if path.name != "SHA256SUMS.txt")
(OUT / "SHA256SUMS.txt").write_text("".join(
    f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in files), encoding="utf-8")
for path in files:
    print(f"{path.name}: {path.stat().st_size:,} bytes")
