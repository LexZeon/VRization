# Original VRization build wrapper, MIT. No environment installer/driver registration.
[CmdletBinding()]
param(
    [string]$Python = 'python',
    [ValidateSet('Release','Debug')][string]$Configuration = 'Release',
    [switch]$Test,
    [switch]$FetchOnly
)
$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'build_steamvr_native.py'
$buildArgs = @($scriptPath, '--configuration', $Configuration)
if ($Test) { $buildArgs += '--test' }
if ($FetchOnly) { $buildArgs += '--fetch-only' }
& $Python @buildArgs
if ($LASTEXITCODE -ne 0) { throw "Native build failed with exit code $LASTEXITCODE" }
