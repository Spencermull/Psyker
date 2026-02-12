# Build Psyker installer: PyInstaller (dist/Psyker/) + Inno Setup (Psyker-Setup-X.Y.Z.exe)
# Requires: Python with [build] deps, Inno Setup 6 (iscc.exe in PATH or standard location)
# Run from repo root.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $ProjectRoot "psyker.spec"))) {
    $ProjectRoot = Get-Location
}
Set-Location $ProjectRoot

Write-Host "Building Psyker installer (minimal user intervention)..." -ForegroundColor Cyan

# 1. Build PyInstaller output
Write-Host "`n[1/3] Running PyInstaller..." -ForegroundColor Yellow
& python -m pip install -e ".[build]" -q 2>$null
& pyinstaller psyker.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$distPsyker = Join-Path $ProjectRoot "dist" "Psyker"
if (-not (Test-Path (Join-Path $distPsyker "Psyker.exe"))) {
    Write-Error "PyInstaller output not found at dist/Psyker/Psyker.exe"
}

# 2. Resolve Inno Setup compiler
$iscc = $null
if (Get-Command iscc -ErrorAction SilentlyContinue) {
    $iscc = "iscc"
} elseif (Test-Path "C:\Program Files (x86)\Inno Setup 6\ISCC.exe") {
    $iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
} elseif (Test-Path "C:\Program Files\Inno Setup 6\ISCC.exe") {
    $iscc = "C:\Program Files\Inno Setup 6\ISCC.exe"
}
if (-not $iscc) {
    Write-Error "Inno Setup not found. Install from https://jrsoftware.org/isinfo.php and ensure iscc.exe is in PATH."
}

# 3. Read version from pyproject.toml and build installer
$pyproject = Get-Content (Join-Path $ProjectRoot "pyproject.toml") -Raw
if ($pyproject -match 'version\s*=\s*"([^"]+)"') {
    $version = $Matches[1]
} else {
    $version = "0.1.0"
}

Write-Host "`n[2/3] Building installer (version $version)..." -ForegroundColor Yellow
& $iscc /DMyAppVersion=$version (Join-Path $ProjectRoot "installer" "Psyker.iss")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$setupExe = Join-Path $ProjectRoot "dist" "Psyker-Setup-$version.exe"
Write-Host "`n[3/3] Done." -ForegroundColor Green
Write-Host "Installer: $setupExe" -ForegroundColor Green
Write-Host "`nUser flow: download exe -> run -> Next -> Install -> Finish. Sandbox pre-created." -ForegroundColor Gray
