# Deploy Guide — Vercel + Fly.io (free tier)

This project is structured to deploy as two independent services:

```
┌─────────────────────────────────┐         ┌──────────────────────────────────┐
│  Vercel (free)                  │         │  Fly.io (free)                   │
│  Next.js frontend               │  HTTPS  │  FastAPI backend + FAISS + SQLite│
│  https://<app>.vercel.app       │ ──────► │  https://<app>.fly.dev           │
└─────────────────────────────────┘         └──────────────────────────────────┘
                                                     │
                                                     ▼
                                            ┌────────────────┐
                                            │  LLM providers │
                                            │  Groq / Gemini │
                                            │  MiniMax / Ollama│
                                            └────────────────┘
```

Total cost: **$0/month** (within free tier limits).

---

## Prerequisites

- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) — `winget install Fly.Fly` on Windows
- [Vercel CLI](https://vercel.com/docs/cli) — `npm i -g vercel`
- A Fly.io account (free, no card required for the free tier)
- A Vercel account (sign in with GitHub)
- API keys for **at least one** LLM provider (Groq recommended — fastest + generous free tier)

---

## Part 1 — Deploy the backend on Fly.io

### 1.1 — Sign in

```powershell
fly auth signup      # or: fly auth login
```

### 1.2 — Create the persistent volume

The volume stores SQLite (`data/db/`) and FAISS indexes (`data/faiss/`) so they survive redeploys.

```powershell
cd backend
fly volumes create rag_data --size 1
```

This gives you **1 GB of free persistent storage** (Fly free tier includes 3 GB total).

### 1.3 — Create the app (first time only)

```powershell
fly launch --no-deploy
```

When prompted:
- **App name**: `multiagent-rag` (or anything — change `app` in `fly.toml` to match)
- **Region**: pick `gru` (São Paulo) for low latency from Brazil
- **Postgres**: No
- **Redis**: No
- **Deploy now**: No (we'll set secrets first)

`fly launch` will reuse the `fly.toml` already in the repo.

### 1.4 — Set secrets (NEVER commit these)

```powershell
fly secrets set `
  MINIMAX_API_KEY="sk-..." `
  GROQ_API_KEY="gsk_..." `
  GEMINI_API_KEY="AIza..." `
  OLLAMA_BASE_URL="https://your-tunnel.trycloudflare.com" `
  DEFAULT_LLM_PROVIDER="groq" `
  DEFAULT_LLM_MODEL="llama-3.1-8b-instant"
```

> The default provider/model variables aren't strictly required — the app will fall back to Ollama or fail loudly. Set them if you want a specific default.

### 1.5 — Allow your Vercel origin (CORS)

After Part 2 you'll get a Vercel URL like `https://multiagent-rag.vercel.app`. Then:

```powershell
fly secrets set ALLOWED_ORIGINS="https://multiagent-rag.vercel.app,https://multiagent-rag-*.vercel.app"
```

For local dev you can also include `http://localhost:3000`.

### 1.6 — Deploy

```powershell
fly deploy
```

First deploy takes ~3-5 min (building wheels for `faiss-cpu` and `sentence-transformers`). Subsequent deploys use cached layers and finish in ~30s.

### 1.7 — Smoke test

```powershell
fly status
fly open
# In browser, visit: https://<your-app>.fly.dev/api/info
# You should see JSON with the endpoint list
```

Check logs if something's wrong:

```powershell
fly logs --tail
```

---

## Part 2 — Deploy the frontend on Vercel

### 2.1 — Sign in

```powershell
cd ../frontend
vercel login
```

### 2.2 — Set the environment variable

```powershell
vercel env add NEXT_PUBLIC_API_URL production
# paste: https://<your-fly-app>.fly.dev/api
```

Also set it for `preview` and `development` if you want PR previews to talk to the real backend.

### 2.3 — Deploy

```powershell
vercel              # preview deploy
vercel --prod       # production deploy
```

Vercel auto-detects Next.js. Build takes ~1-2 min. Free tier includes automatic HTTPS, global CDN, and 100 GB bandwidth/month.

### 2.4 — Lock the backend to that origin

Go back to the Fly side and tighten CORS now that you know the exact Vercel URL:

```powershell
cd ../backend
fly secrets set ALLOWED_ORIGINS="https://multiagent-rag.vercel.app"
```

---

## Part 3 — Verify end-to-end

1. Open `https://<your-app>.vercel.app` in an incognito window
2. Upload a small PDF in the Documents tab
3. Ask a question in the Chat tab
4. Open the Fly dashboard (`https://fly.io/apps/<your-app>`) — you should see request metrics

---

## Useful commands

```powershell
# Fly
fly logs --tail              # stream backend logs
fly ssh console              # open a shell in the running container
fly status                   # check health
fly deploy                   # redeploy after a code change
fly secrets list             # see all configured secrets (values hidden)
fly volumes list             # see storage

# Vercel
vercel ls                    # list deployments
vercel logs <deployment-url> # stream frontend logs
vercel env ls                # list env vars
```

---

## Free-tier limits & scaling up

| Resource | Free limit | When to upgrade |
|----------|------------|-----------------|
| Fly VMs | 3 shared-cpu-1x 256MB VMs | Need more than 1 always-on instance |
| Fly volumes | 3 GB total | More than ~10k document chunks |
| Fly bandwidth | 100 GB/month out | High traffic (>1k unique visitors/day) |
| Vercel | 100 GB bandwidth, 1000 build-min/day | Need more deploys or heavy SSR |
| Groq | 30 req/min, 14.4k req/day | If your demo gets popular |
| Gemini | 60 req/min | Burst traffic |

If you outgrow free tier, the next step is **Hetzner** (€3.79/month, full VPS, you control everything). See `docs/deploy-hetzner.md` (TODO if you want me to write this).

---

## Troubleshooting

**"Build failed: Cannot find faiss"** — Run `fly deploy --remote-only` (forces remote build, not local Docker).

**"CORS error in browser"** — Your `ALLOWED_ORIGINS` doesn't include the Vercel URL. Re-run step 1.5.

**"404 on /api/ask from Vercel"** — Your `NEXT_PUBLIC_API_URL` is wrong. Run `vercel env ls` and redeploy.

**"Backend restarts constantly"** — Check `fly logs`. Often OOM (out of memory). Bump `memory = "512mb"` in `fly.toml`.

**"First request is slow"** — Normal. The HuggingFace embedding model loads on first request. After that it's fast.

**"Data disappeared after redeploy"** — The volume mount is missing. Check `[mounts]` in `fly.toml` and `fly volumes list`.

---

## Local dev vs production

| | Local (PowerShell) | Production (Fly + Vercel) |
|---|---|---|
| Backend start | `pwsh scripts/start_dev_all.ps1` | `fly deploy` |
| Frontend start | (same script) | `vercel --prod` |
| Data location | `<project>/data/` | Fly volume `/data` |
| API URL | `http://localhost:8011/api` | `https://<app>.fly.dev/api` |
| LLM keys | `backend/.env` | `fly secrets set ...` |

The app reads `DATA_DIR` env var to switch between local and volume-backed storage.
