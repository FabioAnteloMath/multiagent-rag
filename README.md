# Multiagent RAG — Support Copilot

> A production-ready Retrieval-Augmented Generation (RAG) system with intelligent multi-agent routing, dynamic agent management, and side-by-side model A/B testing.

[![Backend](https://img.shields.io/badge/backend-FastAPI-009688)](https://fastapi.tiangolo.com)
[![Frontend](https://img.shields.io/badge/frontend-Next.js%2016-black)](https://nextjs.org)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-Portfolio-lightgrey)](#license)
[![Security](https://img.shields.io/badge/security-OWASP%20Top%2010-blueviolet)](docs/security-implementation.md)

## What it does

Drop your support docs (PDF/MD/TXT) into the system, and **specialized AI agents** answer customer questions with citations. The orchestrator classifies the question, picks the right agent(s), retrieves relevant chunks from a per-collection FAISS index, and synthesizes an answer with full source attribution.

Three execution modes:

| Mode | Behavior | Best for |
|------|----------|----------|
| **Baseline** | Single FAISS index over all docs, direct LLM | Performance baseline, fallback |
| **Multi-Agent** | Classify → run all matching agents in parallel → aggregate | Cross-domain questions |
| **Single RAG** | Classify → run ONE best-matching agent → clean single answer | Production lookups |

Plus a **dynamic agent roster** (create, edit, activate, link to a collection) and a **multi-model A/B endpoint** to compare LLM providers on the same retrieval.

## Why this project

I built this to (a) learn multi-agent orchestration end-to-end, (b) study RAG retrieval quality with different chunking strategies, and (c) have a credible portfolio piece that demonstrates FastAPI, Next.js 16, FAISS, and four LLM providers in a real working system.

It started with 4 hardcoded agents. It evolved into a fully DB-driven agent roster, four LLM providers, an A/B benchmark against real models, and a CI pipeline that runs Security/Bandit/pip-audit on every push.

## Screenshots

```
coming soon — see docs/rag-pdf/rag-report.pdf for a deep-dive writeup
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend — Next.js 16 + React 19 + Tailwind 4                      │
│  /chat  /documents  /collections  /agents  /documents/[id]/chunks   │
└────────────────────────┬────────────────────────────────────────────┘
                         │  fetch (HTTP) — :8011/api
┌────────────────────────▼────────────────────────────────────────────┐
│  Backend — FastAPI + SQLAlchemy + SQLite                            │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │chat_     │  │routes/   │  │routes/   │  │routes/   │  │/ask/  │ │
│  │routes    │  │documents │  │collection│  │agents    │  │ab     │ │
│  │/ask      │  │CRUD+chunk│  │CRUD+merge│  │CRUD+stat │  │A/B    │ │
│  └─────┬────┘  └─────┬────┘  └────┬─────┘  └────┬─────┘  └───┬───┘ │
│        │              │            │             │            │     │
│  ┌─────▼──────────────▼────────────▼─────────────▼────────────▼────┐│
│  │ Services                                                       ││
│  │ ┌──────────┐ ┌──────────┐ ┌───────────────────────────────┐   ││
│  │ │rag_      │ │index_    │ │llm_providers                  │   ││
│  │ │pipeline  │ │manager   │ │┌──────┐┌──────┐┌─────┐┌──────┐│   ││
│  │ │(baseline)│ │(FAISS)   │ ││Ollama││MiniMa││Groq ││Gemini│   ││
│  │ └──────────┘ └──────────┘ │└──────┘└──────┘└─────┘└──────┘│   ││
│  │                            └───────────────────────────────┘   ││
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Agents — DB-driven roster                                    │  │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐                      │  │
│  │ │master_   │ │dynamic_  │ │base_     │                      │  │
│  │ │agent     │ │agent     │ │agent     │                      │  │
│  │ │(orchestr)│ │(1 per row│ │(abstract)│                      │  │
│  │ └──────────┘ └──────────┘ └──────────┘                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
  ┌─────────┐      ┌──────────┐     ┌──────────┐
  │ SQLite  │      │  FAISS   │     │ Source   │
  │ metadata│      │ vectors  │     │ docs/    │
  │ db/     │      │ per      │     │ *.pdf    │
  │         │      │collection│     │ *.md     │
  └─────────┘      └──────────┘     │ *.txt    │
                                    └──────────┘
```

## Quick start

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) Ollama for local LLMs — [install](https://ollama.ai) then `ollama pull llama3.2:3b`
- (Optional) API keys for MiniMax, Groq, or Gemini

### Option A — One command (Windows / PowerShell)

```powershell
# From project root
pwsh scripts/start_dev_all.ps1
```

This opens two windows: backend (with auto-restart watchdog) on `:8011`, frontend (Next.js dev) on `:3000`. Both log to `backend/logs/`.

Check status or stop everything:

```powershell
pwsh scripts/dev_services.ps1 -Status
pwsh scripts/dev_services.ps1 -Stop
```

### Option B — Manual

```bash
# Backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r backend/requirements.txt
copy backend\.env.example backend\.env    # then fill in keys
python run_server.py                     # listens on :8011

# Frontend (in another terminal)
cd frontend
npm install
npm run dev                              # listens on :3000
```

### Try it

Open <http://localhost:3000>:
1. **Documents** → upload a `.pdf`, `.md`, or `.txt` (or skip if you have docs in `data/docs/`)
2. **Collections** → create a collection, link your document to it
3. **Agents** → create an agent, set its provider/model, point it at the collection
4. **Chat** → ask a question, watch the orchestrator pick the right agent

API docs at <http://localhost:8011/docs>.

## LLM providers

The backend ships with four providers. Add a key to `backend/.env` for the ones you want to use — unset providers just won't be selectable in the UI.

| Provider | Cost | Setup | Notes |
|----------|------|-------|-------|
| **Ollama** (local) | Free | `ollama pull llama3.2:3b` | Default. No internet, no key, slower. |
| **MiniMax** (cloud) | Pay-as-you-go | `MINIMAX_API_KEY=...` | The primary cloud model in this project. |
| **Groq** (free tier) | Free up to ~30 req/min | `GROQ_API_KEY=...` | Ultra-fast inference (10× faster than MiniMax in benchmarks). |
| **Gemini** (free tier) | Free, rate-limited | `GEMINI_API_KEY=...` | Good for batch testing. |

See `backend/.env.example` for the full list and `backend/app/services/llm_providers.py` for per-model pricing.

## Agent management

Agents are stored in the `agents` table — no code changes to add or modify one. Each agent has:

- **Identity**: name, specialty (used as routing category), system prompt, guidelines, personality, response format, examples
- **Model**: provider, model name, temperature
- **Target**: linked to a collection (FAISS index)
- **State**: `is_active` toggle (deactivated agents are skipped by the orchestrator)

The **Agents** page in the UI lets you do all of this with provider catalog dropdowns (no need to type model names), live prompt editing with the `Make concise` button (auto-rewrites long prompts to be terser), and provider brand badges (Ollama / MiniMax / Groq / Gemini).

## A/B endpoint

`POST /api/ask/ab` runs the **same retrieval** through N models and returns them side-by-side with latency, tokens, and estimated cost.

```bash
curl -X POST http://localhost:8011/api/ask/ab \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the rollback procedure?",
    "top_k": 3,
    "agent_category": "devops",
    "models": [
      {"provider": "groq", "model_name": "llama-3.1-8b-instant"},
      {"provider": "minimax", "model_name": "MiniMax-M2.7"},
      {"provider": "ollama", "model_name": "llama3.2:3b"}
    ]
  }'
```

A real-world benchmark against 4 models lives at [`docs/ab-benchmark/ab-test-report-v2.pdf`](docs/ab-benchmark/ab-test-report-v2.pdf).

## LLM quota + fallback (free-tier protection)

Every LLM call goes through `ProviderRouter`, which enforces three layers of protection so the deployed demo never goes over the free tier of any provider:

1. **Per-provider rolling 24h quota** — counts requests in the `usage_log` table. When the daily limit is reached, that provider is skipped for the rest of the window.
2. **Per-IP rate limit** — `slowapi` caps `/api/ask` at 30 req/min. Bot scrapers can't burn the quota.
3. **Automatic fallback** — when the preferred provider fails (rate limit, network, 5xx) or is over quota, the router walks `FALLBACK_CHAIN` (default: `groq → gemini → minimax → ollama`) until one succeeds.
4. **Circuit breaker** — if a provider returns 5+ failures in 60s the router stops calling it for 5 minutes. Prevents cascading timeouts.

| Provider | Free tier | Default daily limit | Margin |
|----------|-----------|---------------------|--------|
| Groq | 14.4k req/day | 13,000 | ~10% |
| Gemini | 1,500 req/day | 1,400 | ~7% |
| MiniMax | varies | 5,000 (configurable) | — |
| Ollama | unlimited (local) | 999,999 | — |

If every provider is exhausted, `/api/ask` returns **HTTP 429** with `Retry-After: 3600` and a structured body describing the exhausted provider.

### Visibility

`GET /api/usage` returns the live snapshot:

```json
{
  "enabled": true,
  "providers": {
    "chain": ["groq", "gemini", "minimax", "ollama"],
    "providers": [
      { "provider": "groq",   "used": 47,    "limit": 13000,  "remaining": 12953, "exhausted": false, "window_hours": 24 },
      { "provider": "gemini", "used": 0,     "limit": 1400,   "remaining": 1400,  "exhausted": false, "window_hours": 24 },
      { "provider": "minimax","used": 0,     "limit": 5000,   "remaining": 5000,  "exhausted": false, "window_hours": 24 },
      { "provider": "ollama", "used": 0,     "limit": 999999, "remaining": 999999,"exhausted": false, "window_hours": 24 }
    ]
  },
  "totals": { "rows_logged": 47 }
}
```

A provider row can also carry `"circuit_open": true, "circuit_open_for_s": 287` if the breaker is open.

### Configuration (env vars)

```bash
QUOTA_ENABLED=true
QUOTA_GROQ_DAILY=13000
QUOTA_GEMINI_DAILY=1400
QUOTA_MINIMAX_DAILY=5000
QUOTA_OLLAMA_DAILY=999999
QUOTA_WINDOW_HOURS=24
FALLBACK_CHAIN=groq,gemini,minimax,ollama
```

### When a fallback happens

The A/B endpoint reflects the actually-served provider:

```json
{ "provider": "gemini", "model_name": "gemini-1.5-flash",
  "answer": "...", "sources": ["..."], "latency_ms": 1234, ... }
```

The first `ABModelSpec` said `"provider": "groq"`, but the response shows `"provider": "gemini"` — meaning Groq failed and the router fell back. The `latency_ms` and `total_tokens` reflect the *actual* call, not the requested one.

## Security

OWASP Top 10 hardening is baked in (see [`docs/security-implementation.md`](docs/security-implementation.md) for the full audit):

| Layer | Mechanism |
|-------|-----------|
| **Rate limiting** | slowapi: 60/min health, 10/min ingest, 30/min ask |
| **Input validation** | Pydantic with min/max length, prompt-injection pattern matching (30+ regexes in EN/PT/ES) |
| **CORS** | Whitelist via `ALLOWED_ORIGINS` env var |
| **Security headers** | CSP, HSTS, X-Frame-Options, X-Content-Type-Options, XSS-Protection |
| **Audit logging** | Middleware logs every `/api/*` request with IP, method, status, duration |
| **Dependency scanning** | GitHub Actions runs Safety + Bandit + pip-audit on every push, Dependabot weekly |

## Project structure

```
multiagent-rag/
├── backend/                       # FastAPI + SQLAlchemy + SQLite
│   ├── app/
│   │   ├── api/
│   │   │   ├── chat_routes.py          # /api/ask, /api/ask/ab, /api/health
│   │   │   └── routes/
│   │   │       ├── documents.py        # Document CRUD + chunks + upload
│   │   │       ├── collections.py      # Collection CRUD + merge
│   │   │       └── agents.py           # Agent CRUD + stats
│   │   ├── agents/
│   │   │   ├── master_agent.py         # Orchestrator (parallel delegation)
│   │   │   ├── base_agent.py           # Abstract base
│   │   │   ├── dynamic_agent.py        # DB-driven agent instance
│   │   │   ├── classifiers.py          # LLM + keyword classifiers
│   │   │   └── __init__.py
│   │   ├── core/
│   │   │   ├── database.py             # SQLite session
│   │   │   ├── security.py             # Middleware (rate limit, headers)
│   │   │   └── security_service.py     # Prompt injection detection
│   │   ├── models/document.py          # SQLAlchemy models
│   │   └── services/
│   │       ├── llm_providers.py        # Ollama / MiniMax / Groq / Gemini
│   │       ├── rag_pipeline.py         # Baseline RAG
│   │       └── index_manager.py        # FAISS build/load
│   ├── tests/                          # 7 test files (unit + integration + e2e)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                      # Next.js 16 + React 19 + Tailwind 4
│   ├── app/
│   │   ├── chat/page.tsx                # Chat UI with mode selector
│   │   ├── documents/page.tsx           # Document list + upload
│   │   ├── documents/[id]/chunks/       # Chunk viewer with pagination + search
│   │   ├── collections/page.tsx
│   │   ├── agents/page.tsx              # Agent management (catalog + editor)
│   │   ├── page.tsx                     # Landing
│   │   ├── layout.tsx
│   │   └── globals.css
│   └── lib/api.ts                       # Typed API client
├── scripts/                       # PowerShell dev helpers
│   ├── start_dev_all.ps1                # Start everything
│   ├── watchdog_backend.ps1             # Auto-restart backend
│   ├── dev_services.ps1                 # Status / stop
│   └── README.md
├── data/                          # SQLite + FAISS + source docs (gitignored)
├── docs/                          # Architecture, security, A/B benchmark
│   ├── rag-pdf/rag-report.pdf
│   ├── ab-benchmark/ab-test-report-v2.pdf
│   ├── security-implementation.md
│   ├── milvus-rag-*.md
│   └── ...
├── .github/workflows/security.yml # Safety / Bandit / pip-audit
├── run_server.py                  # Backend launcher
├── import_docs.py                 # Idempotent import of existing data/docs/
└── README.md
```

## API endpoints

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/health` | Health check |
| `POST` | `/api/ask` | Ask a question (`mode`: baseline / auto / single_rag) |
| `POST` | `/api/ask/ab` | Multi-model A/B comparison |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/documents` | List documents |
| `POST` | `/api/documents/upload` | Upload a file |
| `PUT`  | `/api/documents/{id}` | Update (e.g. move to a collection) |
| `DELETE` | `/api/documents/{id}` | Delete |
| `GET`  | `/api/documents/{id}/chunks` | List chunks (with pagination) |
| `POST` | `/api/documents/{id}/chunks` | Add chunk |
| `PUT`  | `/api/documents/{id}/chunks/{cid}` | Edit chunk |
| `DELETE` | `/api/documents/{id}/chunks/{cid}` | Delete chunk |
| `POST` | `/api/documents/{id}/reindex` | Rebuild FAISS index |
| `POST` | `/api/documents/rebuild-all-indexes` | Rebuild all |

### Collections

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/collections` | List |
| `POST` | `/api/collections` | Create |
| `PUT`  | `/api/collections/{id}` | Update |
| `DELETE` | `/api/collections/{id}` | Delete |
| `POST` | `/api/collections/merge` | Merge two |
| `GET`  | `/api/collections/{id}/documents` | List docs in collection |

### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/agents` | List (active + inactive) |
| `POST` | `/api/agents` | Create |
| `GET`  | `/api/agents/{id}` | Get one |
| `PUT`  | `/api/agents/{id}` | Update |
| `DELETE` | `/api/agents/{id}` | Delete |
| `PUT`  | `/api/agents/{id}/collection/{cid}` | Link to a collection |
| `GET`  | `/api/agents/{id}/stats` | Usage stats |

### Quota & usage

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/usage` | Current quota per provider + circuit-breaker state |

## Development

### Running tests

```bash
cd backend
python -m pytest tests/ -v
```

Unit tests cover agents, classifiers, LLM providers, security. Integration tests cover the orchestrator. E2E tests run against a live FastAPI instance.

### Adding a new LLM provider

1. Subclass `LLMProvider` in `backend/app/services/llm_providers.py`
2. Register it in `ModelProviderFactory.PROVIDERS`
3. Add the model list to `PROVIDER_CATALOG` in `frontend/lib/api.ts`

The UI will pick it up automatically.

### Adding a new agent at runtime

You don't need to touch code. Use the **Agents** page in the UI, or:

```bash
curl -X POST http://localhost:8011/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Postgres Tuning Agent",
    "specialty": "postgres",
    "collection_id": "<your-collection-uuid>",
    "provider": "groq",
    "model_name": "llama-3.1-8b-instant",
    "temperature": 0.2,
    "system_prompt": "You are a Postgres performance expert. Always reference EXPLAIN plans.",
    "guidelines": "Cite the exact query from the user's question when possible.",
    "personality": "Direct, no fluff, tables preferred over prose."
  }'
```

The new agent is immediately routable.

## Deploy (free tier)

The repo ships ready-to-deploy configs for **Vercel** (frontend) and **Fly.io** (backend). Both free tiers, total cost **$0/month**, no sleep.

| | What | Config |
|---|---|---|
| Frontend | Vercel (Next.js, global CDN, 100GB bandwidth) | `frontend/vercel.json` |
| Backend | Fly.io (FastAPI + FAISS, 3 shared VMs, 3GB volume) | `backend/fly.toml` + `backend/Dockerfile` |
| Data | Fly persistent volume (`/data` → SQLite + FAISS) | mounted in `fly.toml` |

**One-time setup (~10 min):**

```powershell
# Backend
cd backend
fly auth signup
fly volumes create rag_data --size 1
fly launch --no-deploy                  # uses the fly.toml in this repo
fly secrets set GROQ_API_KEY="gsk_..."  # or any provider
fly deploy

# Frontend
cd ../frontend
vercel login
vercel env add NEXT_PUBLIC_API_URL production   # paste: https://<app>.fly.dev/api
vercel --prod
```

After both deploys, lock CORS:

```powershell
cd ../backend
fly secrets set ALLOWED_ORIGINS="https://<your-app>.vercel.app"
```

Full step-by-step, troubleshooting, and scaling notes: see **[DEPLOY.md](DEPLOY.md)**.

## License

This project is for portfolio and study purposes. See [LICENSE](LICENSE) if present.
