# Start backend (with watchdog) + frontend together
#
# Usage: pwsh scripts/start_dev_all.ps1
#
# What it does:
#   1. Starts the backend in its own window with a watchdog that auto-restarts on crash
#   2. Starts the frontend (next dev) in its own window
#   3. Tails the watchdog log in this window so you can see everything
#
# Stop: Ctrl+C here, then close the two spawned windows.
#       Or use: pwsh scripts/dev_services.ps1 -Stop

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BackendDir  = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$LogDir      = Join-Path $BackendDir "logs"
$null = New-Item -ItemType Directory -Force -Path $LogDir

$BackendLog  = Join-Path $LogDir "backend.log"
$WatchdogLog = Join-Path $LogDir "watchdog.log"
$FrontendLog = Join-Path $LogDir "frontend.log"

function Get-VenvPython {
    $candidates = @(
        (Join-Path $ProjectRoot ".venv/Scripts/python.exe"),
        (Join-Path $BackendDir   "venv/Scripts/python.exe"),
    )
    foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
    throw "No virtualenv python found. Create .venv or backend/venv first."
}

$Python = Get-VenvPython

# --- Load .env (if any) so the backend picks up GROQ_API_KEY etc. ---
$envFile = Join-Path $BackendDir ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
        $k, $v = $_ -split '=', 2
        if ($k -and $v) {
            Set-Item -Path "Env:$($k.Trim())" -Value $v.Trim()
        }
    }
}

Write-Host "==> Using Python: $Python" -ForegroundColor Cyan
Write-Host "==> Project root: $ProjectRoot" -ForegroundColor Cyan
Write-Host "==> Logs:         $LogDir"     -ForegroundColor Cyan
Write-Host ""

# --- Start the watchdog (which starts the backend) ---
Write-Host "[+] Starting backend watchdog..." -ForegroundColor Green
$WatchdogScript = Join-Path $PSScriptRoot "watchdog_backend.ps1"
Start-Process -FilePath "pwsh" `
    -ArgumentList "-NoProfile", "-File", "`"$WatchdogScript`"", "-Python", "`"$Python`"", "-ProjectRoot", "`"$ProjectRoot`"", "-LogFile", "`"$BackendLog`"", "-WatchdogLog", "`"$WatchdogLog`"" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Normal

# --- Start the frontend ---
Write-Host "[+] Starting frontend (next dev)..." -ForegroundColor Green
Start-Process -FilePath "pwsh" `
    -ArgumentList "-NoProfile", "-Command", "Set-Location '$FrontendDir'; npm run dev 2>&1 | Tee-Object -FilePath '$FrontendLog'" `
    -WorkingDirectory $FrontendDir `
    -WindowStyle Normal

Write-Host ""
Write-Host "==> Both services starting in separate windows." -ForegroundColor Yellow
Write-Host "==> Backend log:   $BackendLog"   -ForegroundColor Yellow
Write-Host "==> Watchdog log:  $WatchdogLog"  -ForegroundColor Yellow
Write-Host "==> Frontend log:  $FrontendLog"  -ForegroundColor Yellow
Write-Host ""
Write-Host "==> Tailing watchdog log (Ctrl+C to stop tailing)..." -ForegroundColor Cyan
Write-Host ""

# Tail the watchdog log so the user sees backend status
Get-Content $WatchdogLog -Wait
