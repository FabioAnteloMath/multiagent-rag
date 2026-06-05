# Dev scripts

PowerShell scripts for local development on Windows.

| Script | What it does |
|---|---|
| `start_dev_all.ps1` | Starts backend (with watchdog) + frontend in separate windows, tails the watchdog log. One command, all services up. |
| `watchdog_backend.ps1` | Loops the FastAPI server, restarting it on crash with exponential backoff (3s → 30s). Don't run this directly — use `start_dev_all.ps1`. |
| `dev_services.ps1` | `-Status` lists running dev processes and listening ports. `-Stop` kills them all. |

## Typical workflow

```powershell
# Terminal 1 — start everything
pwsh scripts/start_dev_all.ps1

# Terminal 2 — check status
pwsh scripts/dev_services.ps1 -Status

# When done — stop everything
pwsh scripts/dev_services.ps1 -Stop
```

## Why a watchdog?

`uvicorn` doesn't auto-restart on unhandled errors (e.g. Ollama network blip, model load
failure). Without a watchdog, the backend silently dies and the frontend starts returning
`Failed to fetch`. The watchdog catches that, restarts in 3s, and keeps the dev loop smooth.

Logs go to `backend/logs/`:
- `backend.log` — uvicorn stdout/stderr
- `watchdog.log` — restart events with timestamps
- `frontend.log` — next dev output (tailed in the frontend window directly)
