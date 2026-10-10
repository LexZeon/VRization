from pathlib import Path

base = Path(SPECPATH)
root = base.parent.parent
notices = [(str(root / name), '.') for name in ('LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md')]
notices.append((str(root / 'licenses'), 'licenses'))
a = Analysis([str(base / 'launcher.py')], pathex=[str(root / 'desktop/src'), str(base / 'python')],
             binaries=[], datas=notices, hiddenimports=['PIL.JpegImagePlugin'],
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['setuptools', 'pkg_resources', 'numpy', 'dxcam', 'comtypes'], noarchive=False)
a.binaries = [item for item in a.binaries if not (
    Path(item[0]).name.lower().startswith('api-ms-win-') or
    Path(item[0]).name.lower() == 'ucrtbase.dll' or
    Path(item[0]).name.lower().startswith('vcruntime140'))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='VRization-SteamVR',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
