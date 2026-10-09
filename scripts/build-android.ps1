param([string]$JavaHome = $env:JAVA_HOME, [string]$AndroidHome = $env:ANDROID_HOME)
$ErrorActionPreference = 'Stop'
if (-not $JavaHome -or -not (Test-Path (Join-Path $JavaHome 'bin/java.exe'))) {
    throw 'Set JAVA_HOME to a JDK 17 installation (see docs/BUILD.md).'
}
if (-not $AndroidHome -or -not (Test-Path (Join-Path $AndroidHome 'platforms/android-35/android.jar'))) {
    throw 'Set ANDROID_HOME to an Android SDK containing platform 35 (see docs/BUILD.md).'
}
$env:JAVA_HOME = $JavaHome
$env:ANDROID_HOME = $AndroidHome
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $projectRoot 'android')
try {
    & ./gradlew.bat --no-daemon :vr-core:testDebugUnitTest :app:assembleDebug :app:lintDebug
    if ($LASTEXITCODE -ne 0) { throw 'Android verification/build failed' }
} finally { Pop-Location }
