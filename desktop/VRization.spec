# Build from the desktop directory: python -m PyInstaller VRization.spec
from pathlib import Path

base = Path(SPECPATH)
notices = [(str(base.parent / item), '.') for item in
           ('LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md') if (base.parent / item).exists()]
if (base.parent / 'licenses').is_dir():
    notices.append((str(base.parent / 'licenses'), 'licenses'))
a = Analysis([str(base / 'launcher.py')], pathex=[str(base / 'src')],
             binaries=[], datas=notices, hiddenimports=['PIL.JpegImagePlugin'],
             hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['setuptools', 'pkg_resources'], noarchive=False)
# Windows 10/11 provide the UCRT and API-set forwarders. VC++ runtime is an
# explicit Microsoft-installed prerequisite rather than a redistributed DLL.
# A broad development PATH can otherwise copy unrelated SDK runtime files.
a.binaries = [item for item in a.binaries if not (
    Path(item[0]).name.lower().startswith('api-ms-win-') or
    Path(item[0]).name.lower() == 'ucrtbase.dll' or
    Path(item[0]).name.lower().startswith('vcruntime140'))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='VRization-Host',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
