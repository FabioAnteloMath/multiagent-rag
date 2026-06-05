param(
    [switch] $Stop,
    [switch] $Status
)

# Manage the dev backend + frontend processes without leaving orphans.
# Use: pwsh scripts/dev_services.ps1 -Status
#      pwsh scripts/dev_services.ps1 -Stop

$ErrorActionPreference = "SilentlyContinue"

function Get-PwshProcesses {
    Get-CimInstance Win32_Process -Filter "Name = 'pwsh.exe'" |
        Where-Object {
            $_.CommandLine -match 'watchdog_backend\.ps1' -or
            $_.CommandLine -match 'next dev' -or
            $_.CommandLine -match 'uvicorn app\.main'
        } |
        Select-Object ProcessId, @{n='Cmd';e={ $_.CommandLine.Substring(0, [Math]::Min(120, $_.CommandLine.Length)) }}
}

if ($Status) {
    Write-Host "=== Dev Services ===" -ForegroundColor Cyan
    $procs = Get-PwshProcesses
    if (-not $procs) {
        Write-Host "  (no dev services running)" -ForegroundColor DarkGray
    } else {
        $procs | Format-Table -AutoSize
    }

    Write-Host "`n=== Port 8011 (backend) ===" -ForegroundColor Cyan
    $p8011 = Get-NetTCPConnection -LocalPort 8011 -State Listen -ErrorAction SilentlyContinue
    if ($p8011) {
        $p8011 | Select-Object LocalAddress, LocalPort, State, OwningProcess | Format-Table -AutoSize
    } else {
        Write-Host "  (not listening)" -ForegroundColor DarkGray
    }

    Write-Host "`n=== Port 3000 (frontend) ===" -ForegroundColor Cyan
    $p3000 = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
    if ($p3000) {
        $p3000 | Select-Object LocalAddress, LocalPort, State, OwningProcess | Format-Table -AutoSize
    } else {
        Write-Host "  (not listening)" -ForegroundColor DarkGray
    }
    exit 0
}

if ($Stop) {
    Write-Host "==> Stopping dev services..." -ForegroundColor Yellow
    $killed = 0
    Get-PwshProcesses | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }
    Write-Host "==> Killed $killed process(es)." -ForegroundColor Green
    exit 0
}

Write-Host "Usage:" -ForegroundColor Cyan
Write-Host "  pwsh scripts/dev_services.ps1 -Status   # show running services"
Write-Host "  pwsh scripts/dev_services.ps1 -Stop     # stop all dev services"
