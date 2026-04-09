# NotingHill — run_dev.ps1
# Development mode: starts backend + Vite dev server with hot reload
# Usage: .\run_dev.ps1

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot
$BACKEND = "$ROOT\backend"
$FRONTEND = "$ROOT\frontend"
$VENV = "$ROOT\.venv"
$PYTHON = if ($env:PYTHON) { $env:PYTHON } else { "python" }

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          N O T I N G H I L L            ║" -ForegroundColor Cyan
Write-Host "║        Development Mode                  ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Python venv ───────────────────────────────────────────────────
if (-not (Test-Path "$VENV\Scripts\python.exe")) {
    Write-Host "[1/4] Creating Python virtual environment..." -ForegroundColor Yellow
    & $PYTHON -m venv $VENV
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Could not create venv. Is Python installed?" -ForegroundColor Red; exit 1 }
} else {
    Write-Host "[1/4] Virtual environment found ✓" -ForegroundColor Green
}

$VENV_PYTHON = "$VENV\Scripts\python.exe"
$VENV_PIP    = "$VENV\Scripts\pip.exe"

# ── Step 2: Install Python deps ───────────────────────────────────────────
Write-Host "[2/4] Installing Python dependencies..." -ForegroundColor Yellow
& $VENV_PIP install -r "$BACKEND\requirements.txt" --quiet
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: pip install failed." -ForegroundColor Red; exit 1 }
Write-Host "      Dependencies installed ✓" -ForegroundColor Green

# ── Step 3: Node deps ─────────────────────────────────────────────────────
if (-not (Test-Path "$FRONTEND\node_modules")) {
    Write-Host "[3/4] Installing Node.js dependencies (npm install)..." -ForegroundColor Yellow
    Push-Location $FRONTEND
    npm install --silent
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Host "ERROR: npm install failed." -ForegroundColor Red; exit 1 }
    Pop-Location
} else {
    Write-Host "[3/4] Node modules found ✓" -ForegroundColor Green
}

# ── Step 4: Start both servers ────────────────────────────────────────────
Write-Host "[4/4] Starting servers..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Backend  → http://127.0.0.1:7878" -ForegroundColor Cyan
Write-Host "  Frontend → http://127.0.0.1:5173  (Vite dev)" -ForegroundColor Cyan
Write-Host "  API Docs → http://127.0.0.1:7878/api/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press Ctrl+C to stop all servers" -ForegroundColor Gray
Write-Host ""

# Start backend in background
$backendJob = Start-Job -ScriptBlock {
    param($venvPy, $backendDir)
    Set-Location $backendDir
    & $venvPy -m uvicorn main:app --host 127.0.0.1 --port 7878 --reload
} -ArgumentList $VENV_PYTHON, $BACKEND

# Start frontend dev server in background
$frontendJob = Start-Job -ScriptBlock {
    param($frontendDir)
    Set-Location $frontendDir
    npm run dev
} -ArgumentList $FRONTEND

Write-Host "Both servers started. Streaming output..." -ForegroundColor Green
Write-Host ""

# Stream output from both jobs until Ctrl+C
try {
    while ($true) {
        Receive-Job -Job $backendJob  | ForEach-Object { Write-Host "[BACKEND]  $_" -ForegroundColor DarkCyan }
        Receive-Job -Job $frontendJob | ForEach-Object { Write-Host "[FRONTEND] $_" -ForegroundColor DarkGreen }
        Start-Sleep -Milliseconds 500
    }
} finally {
    Write-Host "`nStopping servers..." -ForegroundColor Yellow
    Stop-Job $backendJob, $frontendJob
    Remove-Job $backendJob, $frontendJob -Force
    Write-Host "Stopped." -ForegroundColor Gray
}
