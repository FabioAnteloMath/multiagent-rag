# Multiagent RAG - Support Copilot

A production-ready Retrieval-Augmented Generation (RAG) system with intelligent multi-agent routing for technical support.

[![Tests](https://img.shields.io/badge/tests-179%20passed-green)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-69%25-yellow)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/next.js-16.2-black)](https://nextjs.org)

## Overview

**Support Copilot** is an AI-powered technical support system that uses specialized agents to answer questions about support documentation. It combines RAG (Retrieval-Augmented Generation) with intelligent routing to direct questions to the most relevant specialized agent.

### Key Features

- **Multi-Agent Architecture**: 4 specialized agents (API Support, Database, DevOps, General)
- **Intelligent Routing**: LLM-based classification with keyword fallback
- **Multiple Modes**: Baseline (simple RAG), Auto (parallel multi-agent), Single RAG (single agent)
- **Vector Search**: FAISS for efficient similarity search
- **Dual LLM Support**: Ollama (local/free) or MiniMax (cloud/paid)
- **Comprehensive Testing**: 179 tests with 69% code coverage

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                        │
│   /chat    /documents    /collections    /agents    /chunks       │
└─────────────────────────────────┬───────────────────────────────┘
                                  │ HTTP :8011/api
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI + Python)                   │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │ chat_routes │  │  documents  │  │ collections │  │ agents  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    SERVICES LAYER                        │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │   │
│  │  │  RagPipeline │  │IndexManager │  │  LLM Providers   │  │   │
│  │  └──────────────┘  └──────────────┘  │  (Ollama/MiniMax)│  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      AGENTS LAYER                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────┐  │   │
│  │  │MasterAgent│  │  BaseAgent │  │ Classifier │  │ 4     │  │   │
│  │  │  (orchestr)│  │  (abstract)│  │ (LLM/KW)   │  │Special│  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └───────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                              │
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │   SQLite    │  │    FAISS    │  │        Documents           │ │
│  │  (metadata) │  │  (vectors) │  │   (data/docs/)             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Modes of Operation

| Mode | Description | Use Case |
|------|-------------|----------|
| **baseline** | Simple RAG with single FAISS index + Ollama | Performance comparison, fallback |
| **auto** (MasterAgent) | Classify → Execute ALL matching agents in parallel → Aggregate | Questions that may span multiple areas |
| **single_rag** | Classify → Execute ONE primary agent → Single answer | Cleaner answers, faster execution, lower cost |

## Project Structure

```
multiagent-rag/
├── backend/                    # FastAPI Python backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── chat_routes.py      # /ask, /ingest, /health
│   │   │   └── routes/
│   │   │       ├── documents.py    # Document CRUD + chunks
│   │   │       ├── collections.py  # Collection management
│   │   │       └── agents.py       # Agent management
│   │   ├── agents/
│   │   │   ├── master_agent.py    # Orchestrator
│   │   │   ├── base_agent.py       # Abstract base
│   │   │   ├── classifiers.py      # LLM + Keyword classifiers
│   │   │   ├── agente_suporte.py   # API Support agent
│   │   │   ├── agente_database.py  # Database agent
│   │   │   ├── agente_devops.py    # DevOps agent
│   │   │   └── agente_generalista.py # General agent
│   │   ├── core/
│   │   │   ├── database.py         # SQLite connection
│   │   │   └── security.py         # Rate limiting, prompt injection
│   │   ├── models/
│   │   │   └── document.py         # SQLAlchemy models
│   │   └── services/
│   │       ├── llm_providers.py    # Ollama, MiniMax providers
│   │       ├── rag_pipeline.py    # Baseline RAG
│   │       └── index_manager.py    # Index management
│   └── tests/                    # Test suite (162 tests)
│       ├── unit/
│       ├── integration/
│       └── e2e/
├── frontend/                   # Next.js 14 React frontend
│   ├── app/
│   │   ├── chat/
│   │   ├── documents/
│   │   ├── collections/
│   │   ├── agents/
│   │   └── chunks/
│   └── lib/
│       └── api.ts
├── data/
│   ├── docs/                  # Source documents (.pdf, .md, .txt)
│   ├── faiss/                 # FAISS indexes per collection
│   │   ├── SuporteAPI/
│   │   ├── Database/
│   │   ├── DevOps/
│   │   └── General/
│   └── db/                    # SQLite database
└── docs/                      # Architecture docs
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama (for local LLM) or MiniMax API key (for cloud)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8011
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the frontend
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8011/docs
- **Health Check**: http://localhost:8011/api/health

## Usage

### 1. Ingest Documents

Place `.pdf`, `.md`, or `.txt` files in `data/docs/`, then:

```bash
curl -X POST http://localhost:8011/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"clear_existing": true, "chunk_size": 600, "chunk_overlap": 80}'
```

### 2. Ask Questions

```bash
# Single RAG mode (recommended for clean answers)
curl -X POST http://localhost:8011/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the criteria to abort a release?", "mode": "single_rag"}'

# Auto mode (parallel multi-agent)
curl -X POST http://localhost:8011/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How to fix 401 error?", "mode": "auto"}'

# Baseline mode (simple RAG)
curl -X POST http://localhost:8011/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How to fix 401 error?", "mode": "baseline"}'
```

### 3. Response Format

```json
{
  "answer": "The criteria to abort a release are:...",
  "sources": ["DevOps/release_criteria.md"],
  "agent_used": ["DevOps Agent"],
  "steps": ["route", "search", "generate"],
  "tokens_used": 150,
  "thinking": "Routing: What are the criteria...",
  "model_used": "MiniMax-M2.7",
  "total_time_ms": 1250.5,
  "confidence": 0.9,
  "collection_searched": "DevOps"
}
```

## Configuration

### LLM Providers

**Ollama (Local)**
```bash
# Install Ollama and pull model
ollama pull llama3.2:3b
```

**MiniMax (Cloud)** - Add to `backend/.env`:
```
MINIMAX_API_KEY=your_api_key_here
```

### Agent Configuration

Agents are configured via the database. Access the Agents page in the frontend to:
- Select provider (ollama/minimax)
- Set model name and temperature
- Customize system prompt
- Assign to collections

## Testing

```bash
cd backend

# Run all tests
python -m pytest tests/ -v

# Run unit tests only (fast)
python -m pytest tests/unit tests/integration -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing

# Generate HTML coverage report
python -m pytest tests/ --cov=app --cov-report=html
```

### Test Coverage

| Component | Coverage |
|-----------|----------|
| Agents | 77-100% |
| Classifiers | 92% |
| LLM Providers | 89% |
| MasterAgent | 97% |
| **Total** | **69%** |

**179 tests** covering unit, integration, and E2E scenarios.

## API Endpoints

### Chat Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/ingest` | Ingest documents |
| POST | `/api/ask` | Ask question (baseline/auto/single_rag) |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/documents` | List all documents |
| POST | `/api/documents/upload` | Upload document |
| DELETE | `/api/documents/{id}` | Delete document |
| POST | `/api/documents/{id}/process` | Process document |
| POST | `/api/documents/{id}/reindex` | Rebuild index |

### Collections

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/collections` | List collections |
| POST | `/api/collections` | Create collection |
| PUT | `/api/collections/{id}` | Update collection |
| DELETE | `/api/collections/{id}` | Delete collection |

### Agents

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents` | List agents |
| POST | `/api/agents` | Create agent |
| PUT | `/api/agents/{id}` | Update agent |
| DELETE | `/api/agents/{id}` | Delete agent |

## Specialized Agents

| Agent | Collection | Knowledge Area |
|-------|-----------|---------------|
| **API Support Agent** | SuporteAPI | HTTP errors (401, 403, 500), authentication, JWT, gateway |
| **Database Agent** | Database | PostgreSQL, MySQL, Redis, queries, cache |
| **DevOps Agent** | DevOps | Deploy, rollback, CI/CD, monitoring, Kubernetes |
| **Generalist Agent** | General | General questions, fallback |

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + SQLAlchemy + SQLite |
| Frontend | Next.js 14 + Tailwind CSS + TypeScript |
| Vector DB | FAISS (local, CPU) |
| LLM | Ollama (local) or MiniMax (cloud) |
| Embeddings | all-MiniLM-L6-v2 |
| Testing | pytest + pytest-cov |

## Security

Implemented security measures following OWASP Top 10 guidelines:

| Feature | Implementation |
|---------|---------------|
| **Rate Limiting** | slowapi: 60/min (health), 10/min (ingest), 30/min (ask) |
| **Input Validation** | max_length=1000 on question, Pydantic validation |
| **CORS** | Restrictive via `ALLOWED_ORIGINS` env var |
| **Security Headers** | X-Content-Type-Options, X-Frame-Options, XSS-protection, HSTS, CSP |
| **Audit Logging** | Middleware logs all API requests with IP, method, status, duration |
| **Prompt Injection** | 30 regex patterns (EN/PT/ES) for common injection attempts |
| **Input Sanitization** | Control character removal, whitespace trimming |
| **A06 - Vulnerable Components** | GitHub Actions: Safety, Bandit, pip-audit + Dependabot |

### Security Auditing

```bash
# Install tools
pip install safety bandit pip-audit

# Run all scans locally
safety check --file backend/requirements.txt
bandit -r backend/app
pip-audit --file backend/requirements.txt
```

### CI/CD Security Pipeline

The project includes automated security scanning via GitHub Actions:

| Scanner | Purpose | Frequency |
|---------|---------|-----------|
| **Safety** | Check requirements.txt for CVEs | Every push |
| **Bandit** | Static analysis for Python security | Every push |
| **pip-audit** | Scan installed packages for vulnerabilities | Every push |
| **Dependabot** | Automated dependency updates | Weekly |

### Environment Variables

```bash
# .env file (never commit to git)
MINIMAX_API_KEY=your_api_key_here
ALLOWED_ORIGINS=https://app.example.com  # Comma-separated
```

### Rate Limit Response

When rate limit is exceeded:
```json
{"error": "Rate limit exceeded: 30/minute"}
```

For detailed documentation, see [docs/security-implementation.md](docs/security-implementation.md).

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is for portfolio purposes. See LICENSE file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [LangChain](https://langchain.dev/) - LLM application framework
- [FAISS](https://faiss.ai/) - Efficient similarity search
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [Next.js](https://nextjs.org/) - React framework