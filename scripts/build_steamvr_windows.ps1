param([string]$Python = 'python', [switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if (-not $SkipInstall) {
        & $Python -m pip install -r desktop/requirements-lock.txt
        if ($LASTEXITCODE -ne 0) { throw 'Runtime dependencies failed' }
        & $Python -m pip install 'pytest==9.1.1' 'pytest-asyncio==1.4.0' 'pyinstaller==6.22.3' 'packaging==26.3'
        if ($LASTEXITCODE -ne 0) { throw 'Build dependencies failed' }
    }
    $env:PYTHONPATH = "$(Join-Path $projectRoot 'desktop/src');$(Join-Path $projectRoot 'experimental/steamvr/python')"
    & $Python -m pytest desktop/tests experimental/steamvr/tests -q
    if ($LASTEXITCODE -ne 0) { throw 'Host or preview tests failed' }
    & $Python scripts/collect_licenses.py
    if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
    & $Python -m PyInstaller --noconfirm --distpath artifacts/steamvr/windows-dist --workpath artifacts/steamvr/windows-build experimental/steamvr/VRization-SteamVR.spec
    if ($LASTEXITCODE -ne 0) { throw 'Preview freeze failed' }
} finally { Pop-Location }
