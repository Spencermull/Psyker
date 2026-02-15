# Build Psyker EXE via PyInstaller (dist/Psyker/)
# Requires: Python with [build] deps
# Run from repo root.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $ProjectRoot "psyker.spec"))) {
    $ProjectRoot = Get-Location
}
Set-Location $ProjectRoot

Write-Host "Building Psyker EXE..." -ForegroundColor Cyan

& python -m pip install -e ".[build]" -q 2>$null
& pyinstaller psyker.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$exePath = Join-Path $ProjectRoot "dist" "Psyker" "Psyker.exe"
if (-not (Test-Path $exePath)) {
    Write-Error "PyInstaller output not found at dist/Psyker/Psyker.exe"
}

Write-Host "`nDone. EXE: $exePath" -ForegroundColor Green
