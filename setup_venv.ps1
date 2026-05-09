# setup_venv.ps1
# Creates a Python 3.10 virtual environment for host-side tools (webcam streamer).
# Run this ONCE from the repo root in PowerShell:
#
#   cd path\to\ros1-child-safety-monitoring
#   .\setup_venv.ps1
#
# After setup, activate with:
#   .\.venv310\Scripts\Activate.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$VENV_DIR = ".venv310"
$REQUIRED_MAJOR = 3
$REQUIRED_MINOR = 10

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Child Safety Monitoring - Host Venv Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Find Python 3.10 ──────────────────────────────────────────────────────
Write-Host "[1/4] Looking for Python $REQUIRED_MAJOR.$REQUIRED_MINOR ..." -ForegroundColor Yellow

$pythonExe = $null

# Try py launcher first (Windows standard)
try {
    $ver = & py -3.10 --version 2>&1
    if ($ver -match "Python 3\.10") {
        $pythonExe = "py"
        $pythonArgs = @("-3.10")
        Write-Host "      Found via py launcher: $ver" -ForegroundColor Green
    }
} catch {}

# Fallback: scan PATH for python3.10 or python executables
if (-not $pythonExe) {
    foreach ($candidate in @("python3.10", "python3", "python")) {
        try {
            $ver = & $candidate --version 2>&1
            if ($ver -match "Python 3\.10") {
                $pythonExe = $candidate
                $pythonArgs = @()
                Write-Host "      Found on PATH: $ver" -ForegroundColor Green
                break
            }
        } catch {}
    }
}

if (-not $pythonExe) {
    Write-Host ""
    Write-Host "ERROR: Python 3.10 not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Install it with winget (run in PowerShell as Administrator):"
    Write-Host "  winget install --id Python.Python.3.10 --exact"
    Write-Host ""
    Write-Host "Or download from: https://www.python.org/downloads/release/python-31011/"
    Write-Host ""
    exit 1
}

# ── 2. Create virtual environment ────────────────────────────────────────────
Write-Host "[2/4] Creating virtual environment in '$VENV_DIR' ..." -ForegroundColor Yellow

if (Test-Path $VENV_DIR) {
    Write-Host "      '$VENV_DIR' already exists, skipping creation." -ForegroundColor DarkGray
} else {
    & $pythonExe @pythonArgs -m venv $VENV_DIR
    Write-Host "      Created." -ForegroundColor Green
}

$pipExe    = Join-Path $VENV_DIR "Scripts\pip.exe"
$pythonVenv = Join-Path $VENV_DIR "Scripts\python.exe"

# ── 3. Upgrade pip ───────────────────────────────────────────────────────────
Write-Host "[3/4] Upgrading pip ..." -ForegroundColor Yellow
& $pythonVenv -m pip install --upgrade pip --quiet
Write-Host "      Done." -ForegroundColor Green

# ── 4. Install host requirements ─────────────────────────────────────────────
Write-Host "[4/4] Installing host requirements from requirements_host.txt ..." -ForegroundColor Yellow

if (-not (Test-Path "requirements_host.txt")) {
    Write-Host "ERROR: requirements_host.txt not found." -ForegroundColor Red
    Write-Host "       Make sure you are running this from the repo root." -ForegroundColor Red
    exit 1
}

& $pipExe install -r requirements_host.txt

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Activate the environment:" -ForegroundColor Cyan
Write-Host "  .\.venv310\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Then run the webcam streamer:" -ForegroundColor Cyan
Write-Host "  python src\child_safety_monitoring\scripts\host_webcam_streamer.py --camera 0 --port 8090"
Write-Host ""

# Quick sanity check
Write-Host "Verifying installation ..." -ForegroundColor Yellow
& $pythonVenv -c "import cv2, numpy; print('  numpy :', numpy.__version__); print('  cv2   :', cv2.__version__); print('  All OK')"
Write-Host ""
