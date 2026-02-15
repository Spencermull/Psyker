# Build Psyker installer: PyInstaller (CLI + GUI) + Inno Setup (Psyker-Setup-X.Y.Z.exe)
# Requires: Python with [build,gui] deps, Inno Setup 6 (iscc.exe in PATH or standard location)
# Run from repo root.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $ProjectRoot "psyker.spec"))) {
    $ProjectRoot = Get-Location
}
Set-Location $ProjectRoot

Write-Host "Building Psyker installer (CLI + GUI)..." -ForegroundColor Cyan

# 1. Install deps (pip may warn about PATH; ignore for this script)
$ErrorActionPreference = "Continue"
python -m pip install -e ".[build,gui]" -q 2>&1 | Out-Null
$ErrorActionPreference = "Stop"

# 2. Build CLI EXE
Write-Host "`n[1/4] Building CLI EXE..." -ForegroundColor Yellow
python -m PyInstaller psyker.spec -y
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not (Test-Path (Join-Path $ProjectRoot "dist\Psyker\Psyker.exe"))) {
    Write-Error "Psyker.exe not found at dist/Psyker/"
}

# 3. Build GUI EXE
Write-Host "`n[2/4] Building GUI EXE..." -ForegroundColor Yellow
python -m PyInstaller psyker_gui.spec -y
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not (Test-Path (Join-Path $ProjectRoot "dist\PsykerGUI\PsykerGUI.exe"))) {
    Write-Error "PsykerGUI.exe not found at dist/PsykerGUI/"
}

# 4. Resolve Inno Setup compiler
$iscc = $null
if (Get-Command iscc -ErrorAction SilentlyContinue) {
    $iscc = "iscc"
} elseif (Test-Path "C:\Program Files\Inno Setup 6\ISCC.exe") {
    $iscc = "C:\Program Files\Inno Setup 6\ISCC.exe"
} elseif (Test-Path "C:\Program Files (x86)\Inno Setup 6\ISCC.exe") {
    $iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
}
if (-not $iscc) {
    Write-Host "Inno Setup not found. Installing via winget..." -ForegroundColor Yellow
    winget install JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    # winget returns non-zero if already installed; refresh PATH and retry
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    if (Get-Command iscc -ErrorAction SilentlyContinue) {
        $iscc = "iscc"
    } elseif (Test-Path "C:\Program Files\Inno Setup 6\ISCC.exe") {
        $iscc = "C:\Program Files\Inno Setup 6\ISCC.exe"
    } elseif (Test-Path "C:\Program Files (x86)\Inno Setup 6\ISCC.exe") {
        $iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    }
}
if (-not $iscc) {
    Write-Host ""
    Write-Host "Inno Setup is required. Install with:" -ForegroundColor Yellow
    Write-Host "  winget install JRSoftware.InnoSetup" -ForegroundColor Cyan
    Write-Host "Then close this terminal, open a NEW one, and run this script again." -ForegroundColor Yellow
    Write-Host "Or download from: https://jrsoftware.org/isinfo.php" -ForegroundColor Gray
    exit 1
}

# 5. Read version and build installer
$pyproject = Get-Content (Join-Path $ProjectRoot "pyproject.toml") -Raw
if ($pyproject -match 'version\s*=\s*"([^"]+)"') {
    $version = $Matches[1]
} else {
    $version = "0.1.0"
}

Write-Host "`n[3/4] Building installer (version $version)..." -ForegroundColor Yellow
$issPath = Join-Path $ProjectRoot "installer\Psyker.iss"
& $iscc /DMyAppVersion=$version $issPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$setupExe = Join-Path $ProjectRoot "dist\Psyker-Setup-$version.exe"
Write-Host "`n[4/4] Done." -ForegroundColor Green
Write-Host "Installer: $setupExe" -ForegroundColor Green
Write-Host "`nUser flow: download exe -> run -> Next -> Install -> Finish. Launches Psyker GUI by default." -ForegroundColor Gray
