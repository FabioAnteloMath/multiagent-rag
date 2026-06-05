# Backend watchdog — keeps the FastAPI server alive across crashes
#
# Runs the backend in a loop with exponential backoff. Restarts the process
# as soon as it dies, max 30s between attempts. Catches transient Ollama
# network blips, model load failures, and other recoverable errors.
#
# Usage (normally called by start_dev_all.ps1, not directly):
#   pwsh scripts/watchdog_backend.ps1 -Python <path> -ProjectRoot <path> -LogFile <path> -WatchdogLog <path>

param(
    [Parameter(Mandatory = $true)] [string] $Python,
    [Parameter(Mandatory = $true)] [string] $ProjectRoot,
    [Parameter(Mandatory = $true)] [string] $LogFile,
    [Parameter(Mandatory = $true)] [string] $WatchdogLog
)

$BackendDir = Join-Path $ProjectRoot "backend"
$null = New-Item -ItemType Directory -Force -Path (Split-Path $LogFile -Parent)

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $ts = (Get-Date).ToString("HH:mm:ss")
    $line = "[$ts] $Message"
    Add-Content -Path $WatchdogLog -Value $line
    Write-Host $line -ForegroundColor $Color
}

$env:PYTHONPATH = $BackendDir
$BackoffSequence = @(3, 6, 12, 30)  # seconds; loops back to 3 after 30
$Attempt = 0
$Stop = $false

# Graceful shutdown on Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { $script:Stop = $true }

Write-Log "==> Watchdog starting. Backend dir: $BackendDir" Cyan
Write-Log "==> Python: $Python" Cyan
Write-Log "==> Backend log:  $LogFile" Cyan

while (-not $Stop) {
    $Backoff = $BackoffSequence[[Math]::Min($Attempt, $BackoffSequence.Count - 1)]
    Write-Log "[watchdog] launching uvicorn (attempt $($Attempt + 1))..." Green

    $Process = Start-Process -FilePath $Python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8011", "--log-level", "info" `
        -WorkingDirectory $BackendDir `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError  $LogFile `
        -PassThru -NoNewWindow

    $StartTime = Get-Date
    $ExitedCleanly = $Process.WaitForExit(60000)  # 60s grace, then check

    if (-not $ExitedCleanly) {
        # Still running — that's the happy path. Block until it dies or we get killed.
        Write-Log "[watchdog] backend running (pid $($Process.Id)). Waiting for exit..." Green
        $Process.WaitForExit() | Out-Null
    }

    $ExitCode = $Process.ExitCode
    $UptimeSec = [int]((Get-Date) - $StartTime).TotalSeconds

    if ($Stop) {
        Write-Log "[watchdog] stopping (pid $($Process.Id), exit $ExitCode)." Yellow
        break
    }

    if ($UptimeSec -gt 60) {
        # Survived longer than the grace window — count this as a healthy run.
        $Attempt = 0
    } else {
        $Attempt++
    }

    Write-Log "[watchdog] backend exited (code $ExitCode, uptime ${UptimeSec}s). Restarting in ${Backoff}s..." Yellow
    Start-Sleep -Seconds $Backoff
}

Write-Log "[watchdog] stopped." Yellow
