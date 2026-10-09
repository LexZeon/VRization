param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $projectRoot 'desktop')
try {
    & $Python -m pip install -r requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Runtime installation failed' }
    & $Python -m pip install 'pytest==9.1.1' 'pytest-asyncio==1.4.0' 'pyinstaller==6.22.3' 'packaging==26.3'
    if ($LASTEXITCODE -ne 0) { throw 'Build tool installation failed' }
    & $Python ../scripts/collect_licenses.py
    if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
    & $Python -m pip install --no-deps -e .
    & $Python -m pytest
    if ($LASTEXITCODE -ne 0) { throw 'Desktop tests failed' }
    & $Python -m PyInstaller --noconfirm VRization.spec
    if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed' }
} finally { Pop-Location }
