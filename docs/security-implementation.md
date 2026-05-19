# Security Implementation Document

## Multiagent RAG - Support Copilot

**Version**: 0.3.0
**Last Updated**: 2025
**Status**: Implemented

---

## Overview

This document describes the security measures implemented in the Multiagent RAG Support Copilot project.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    chat_routes.py (API)                          │
│  AskRequest.validate_question()                                   │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SecurityService                               │
│  ┌─────────────────┐  ┌────────────────┐  ┌───────────────┐  │
│  │  SecurityCache   │  │ Pattern Match  │  │ MiniMax-Text- │  │
│  │  (LRU, TTL)     │  │ (11 patterns)  │  │ 01 (LLM)      │  │
│  └─────────────────┘  └────────────────┘  └───────────────┘  │
│                                                                  │
│  check(text) → sanitize → pattern_match ──┐                     │
│                                          ↓                       │
│                           if pattern detected → BLOCK             │
│                           else → LLM classification → BLOCK/ALLOW │
└─────────────────────────────────────────────────────────────────┘
```

### Flow

1. **Input arrives** → `sanitize_input()` removes control chars
2. **Pattern Match** → Fast regex check (11 patterns)
3. **If detected** → Block immediately (confidence: 0.95)
4. **If clean** → MiniMax-Text-01 LLM classification
5. **Result cached** → LRU cache with TTL for performance

### Graceful Degradation

```
LLM Available + Clean Pattern?
├── YES → MiniMax-Text-01 classification (2s timeout)
│         └── Timeout? → Allow (confidence: 0.7)
└── NO  → Pattern-match only mode (confidence: 0.7)
```

---

## 1. SecurityService (Core)

### Features

| Feature | Description |
|---------|-------------|
| **Two-layer detection** | Pattern match (fast) + LLM classification (accurate) |
| **Async support** | `async check()` for non-blocking operations |
| **Timeout** | 2s max for LLM calls (prevents slow-doS) |
| **LRU Cache** | 1000 entries, 5min TTL, ~50ms avg lookup |
| **Graceful degradation** | LLM fail → pattern-match fallback |
| **Singleton pattern** | `get_security_service()` for DI |

### Configuration

```python
SecurityService(
    provider="minimax",           # LLM provider
    model_name="MiniMax-Text-01", # Fast, cheap model
    temperature=0.0,              # Deterministic
    timeout_seconds=2.0,         # Max LLM wait
    llm_enabled=True             # Disable for testing
)
```

### MiniMax-Text-01

| Aspect | Value |
|--------|-------|
| **Role** | Security classification (binary) |
| **Speed** | ~200-500ms |
| **Cost** | $0.001/1K tokens (very cheap) |
| **Temperature** | 0.0 (deterministic) |
| **Max tokens** | 10 (just INJECTION/SAFE) |

### SecurityCheckResult

```python
@dataclass
class SecurityCheckResult:
    is_safe: bool                    # Final verdict
    method: str                      # "pattern_match" or "llm_classification"
    confidence: float               # 0.7 (pattern-only) or 0.85 (LLM)
    processing_time_ms: float       # For monitoring
    attack_type: Optional[str]       # "instruction_override", "xss", etc.
    raw_response: Optional[str]      # LLM raw response for debugging
```

### Attack Types

| Type | Example Pattern |
|------|----------------|
| `instruction_override` | "ignore all previous", "disregard your instructions" |
| `memory_override` | "forget everything" |
| `role_play_attack` | "you are now a different", "pretend you are" |
| `system_override` | "override your system" |
| `security_bypass` | "bypass your security" |
| `prompt_injection` | "system prompt:" |
| `model_impersonation` | "new AI model" |
| `xss` | `<script>` |
| `protocol_injection` | `javascript:` |

---

## 2. SecurityCache

In-memory LRU cache for security check results.

```python
class SecurityCache:
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self._cache = {}
        self._timestamps = {}
        self._max_size = max_size
        self._ttl = ttl_seconds
```

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `max_size` | 1000 | Max cached entries (prevents memory bloat) |
| `ttl_seconds` | 300 | Time-to-live (5 min, balances freshness vs perf) |

### Cache Key

```python
def _make_key(self, text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
```

SHA256 truncated to 16 chars - fast, collision-resistant.

---

## 3. Rate Limiting

Implemented using `slowapi` library to prevent abuse.

### Configuration

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `GET /api/health` | 60/minute | High availability needed |
| `POST /api/ingest` | 10/minute | Resource intensive operation |
| `POST /api/ask` | 30/minute | LLM calls are costly |

### Implementation

```python
# backend/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

### Rate Limit Response

```json
{"error": "Rate limit exceeded: 30/minute"}
```

---

## 4. Input Validation

### AskRequest Validation

```python
class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=4, ge=1, le=10)
    mode: str = Field(default="auto", pattern="^(baseline|auto|single_rag)$")
```

| Field | Validation | Purpose |
|-------|------------|---------|
| `question` | min=3, max=1000 | Prevents empty/long queries |
| `top_k` | ge=1, le=10 | Bounds search depth |
| `mode` | enum | Restricts to valid modes |

### IngestRequest Validation

```python
class IngestRequest(BaseModel):
    chunk_size: int = Field(default=600, ge=200, le=2000)
    chunk_overlap: int = Field(default=80, ge=0, le=500)
```

---

## 5. CORS Configuration

```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

| Setting | Value | Security Benefit |
|---------|-------|-----------------|
| `allow_methods` | Limited to CRUD | Reduces attack surface |
| `allow_headers` | Only auth headers | Prevents header injection |
| `allow_credentials` | True | Allows JWT cookies |

---

## 6. Security Headers

```python
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

| Header | Value | Protection |
|--------|-------|-----------|
| X-Content-Type-Options | nosniff | Prevents MIME sniffing |
| X-Frame-Options | DENY | Prevents clickjacking |
| X-XSS-Protection | 1; mode=block | XSS filter (legacy) |
| Strict-Transport-Security | max-age=1year | Enforces HTTPS |
| Content-Security-Policy | default-src 'self' | XSS prevention |

---

## 7. Audit Logging

```python
@app.middleware("http")
async def audit_logging_middleware(request: Request, call_next):
    start_time = time.time()
    client_ip = get_remote_address(request)
    method = request.method
    path = request.url.path

    if path.startswith("/api/"):
        print(f"[AUDIT] {client_ip} {method} {path} - Start")

    response = await call_next(request)

    if path.startswith("/api/"):
        duration = (time.time() - start_time) * 1000
        status_code = response.status_code
        print(f"[AUDIT] {client_ip} {method} {path} - {status_code} - {duration:.2f}ms")

    return response
```

### Log Format

```
[AUDIT] 192.168.1.100 POST /api/ask - Start
[AUDIT] 192.168.1.100 POST /api/ask - 200 - 1523.45ms
```

---

## 8. Prompt Injection Patterns

```python
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+all\s+previous", re.IGNORECASE),
    re.compile(r"forget\s+everything", re.IGNORECASE),
    re.compile(r"disregard\s+your\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+(different|new)", re.IGNORECASE),
    re.compile(r"pretend\s+you\s+are", re.IGNORECASE),
    re.compile(r"override\s+your\s+system", re.IGNORECASE),
    re.compile(r"bypass\s+your\s+security", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*:", re.IGNORECASE),
    re.compile(r"new\s+AI\s+model", re.IGNORECASE),
    re.compile(r"<\s*script\s*>", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
]
```

All patterns use `re.IGNORECASE` for case-insensitive matching.

---

## 9. Environment Variables

```bash
# .env file (never commit to git)
MINIMAX_API_KEY=your_api_key_here
ALLOWED_ORIGINS=https://app.example.com
```

---

## 10. Testing

```bash
cd backend
python -m pytest tests/unit/test_security_service.py -v
```

### Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| TestSecurityCache | 3 | PASSED |
| TestSecurityServicePatterns | 8 | PASSED |
| TestSecurityServiceCheckSync | 3 | PASSED |
| TestSecurityServiceSingleton | 2 | PASSED |
| TestSecurityServiceAsync | 2 | PASSED |
| TestInjectionPatterns | 2 | PASSED |
| **Total** | **20** | **ALL PASSED** |

---

## 11. A06 - Vulnerable Components

### GitHub Actions Security Workflow

```yaml
# .github/workflows/security.yml
name: Security Audit
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly
```

### Scans Performed

| Tool | Purpose | Frequency |
|------|---------|-----------|
| **Safety** | Check requirements.txt for known CVEs | Every push |
| **Bandit** | Static analysis for Python security issues | Every push |
| **pip-audit** | Scan installed packages for vulnerabilities | Every push |

### Dependabot Configuration

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
```

### Local Security Audit

```bash
# Install tools
pip install safety bandit pip-audit

# Run all scans
safety check --file backend/requirements.txt
bandit -r backend/app
pip-audit --file backend/requirements.txt
```

### OWASP Category Mapping

- **A06:2021 - Vulnerable and Outdated Components**
- Mitigation: Automated scanning + Dependabot updates

---

## 12. Future Improvements

### High Priority

- [x] **Vulnerable Components**: Add automated CVE scanning (DONE)
- [ ] **Authentication**: Add JWT/OAuth2 for API access
- [ ] **Output filtering**: Validate LLM responses for leaks

### Medium Priority

- [ ] **IP blocking**: Auto-block repeated abuse
- [ ] **Metrics**: Prometheus metrics for monitoring
- [ ] **Alerting**: Webhook on security events

### Low Priority

- [x] **Security scanning**: Add Bandit for Python (DONE)
- [x] **Dependency audit**: Automated CVE scanning (DONE)

---

**Document Version**: 1.1
**Repository**: https://github.com/FabioAnteloMath/multiagent-rag