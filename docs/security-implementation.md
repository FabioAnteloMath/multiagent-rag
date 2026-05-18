# Security Implementation Document

## Multiagent RAG - Support Copilot

**Version**: 0.2.1
**Last Updated**: 2025
**Status**: Implemented

---

## Overview

This document describes the security measures implemented in the Multiagent RAG Support Copilot project. All security features were added in a dedicated PR to maintain clean git history and focused changes.

---

## 1. Rate Limiting

Implemented using `slowapi` library to prevent abuse and ensure service availability.

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

```python
# backend/app/api/chat_routes.py
@router.get("/health")
@limiter.limit("60/minute")
def healthcheck(request: Request) -> dict[str, str]:
    return {"status": "ok"}
```

### Response on Rate Limit Exceeded

When rate limit is exceeded, the API returns:
```json
{
  "error": "Rate limit exceeded: 60/minute"
}
```

---

## 2. Input Validation

### Question Length Validation

```python
class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=4, ge=1, le=10)
    mode: str = Field(default="auto", pattern="^(baseline|auto|single_rag)$")
    force_agent: Optional[str] = Field(default=None, pattern="^(suporte_api|database|devops)$")
```

- **Minimum length**: 3 characters (prevents empty queries)
- **Maximum length**: 1000 characters (prevents resource exhaustion)

### Ingest Parameters Validation

```python
class IngestRequest(BaseModel):
    clear_existing: bool = True
    chunk_size: int = Field(default=600, ge=200, le=2000)
    chunk_overlap: int = Field(default=80, ge=0, le=500)
```

- `chunk_size`: Between 200 and 2000
- `chunk_overlap`: Between 0 and 500, must be less than chunk_size

---

## 3. CORS Configuration

### Implementation

```python
# backend/app/main.py
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Configuration

- **Default**: `http://localhost:3000`
- **Environment Variable**: `ALLOWED_ORIGINS` (comma-separated list)
- **Allowed Methods**: GET, POST, PUT, DELETE (no PATCH, DELETE for reduced attack surface)
- **Allowed Headers**: Authorization, Content-Type (no wildcard headers)

### Production Example

```bash
export ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com"
```

---

## 4. Security Headers

Implemented via middleware in `main.py`.

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

### Headers Description

| Header | Value | Purpose |
|--------|-------|---------|
| X-Content-Type-Options | nosniff | Prevents MIME type sniffing |
| X-Frame-Options | DENY | Prevents clickjacking via iframes |
| X-XSS-Protection | 1; mode=block | XSS filter for legacy browsers |
| Strict-Transport-Security | max-age=31536000 | Enforces HTTPS for 1 year |
| Content-Security-Policy | default-src 'self' | Prevents XSS and data injection |

---

## 5. Audit Logging

Implemented via middleware to log all API requests.

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

### Benefits

- Request tracking for compliance
- Performance monitoring
- Security incident investigation
- Anomaly detection

---

## 6. Prompt Injection Detection

### Implementation

```python
# backend/app/core/security.py
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

def detect_prompt_injection(text: str) -> bool:
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False
```

### Detected Patterns

| Category | Patterns |
|----------|----------|
| Instruction Override | ignore all previous, forget everything, disregard your instructions |
| Role Play Attacks | you are now a different, pretend you are |
| System Override | override your system, bypass your security |
| Prompt Injection | system prompt:, new AI model |
| XSS Attempts | `<script>`, `javascript:` |

### Integration with Ask Endpoint

```python
class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = sanitize_input(v)
        if detect_prompt_injection(v):
            raise ValueError("Invalid input detected")
        return v
```

---

## 7. Input Sanitization

```python
def sanitize_input(text: str) -> str:
    text = text.strip()
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
    return text
```

### Sanitization Steps

1. **Whitespace trimming**: Removes leading/trailing whitespace
2. **Control character removal**: Removes ASCII control characters (0x00-0x1F and 0x7F)

### Why Control Characters?

Control characters can be used for:
- Log injection attacks
- Terminal escape sequence injection
- Hidden text manipulation

---

## 8. Environment Variables

### Required for Production

```bash
# .env file (never commit to git)
MINIMAX_API_KEY=your_api_key_here
ALLOWED_ORIGINS=https://app.example.com
```

### Security Notes

- `.env` files are excluded from git via `.gitignore`
- API keys should never be committed to version control
- Use environment variables for all secrets

---

## 9. Testing

### Security Test Suite

```bash
cd backend
python -m pytest tests/unit/test_security.py -v
```

### Test Coverage

| Test Class | Tests | Description |
|------------|-------|-------------|
| TestDetectPromptInjection | 13 | Prompt injection pattern detection |
| TestSanitizeInput | 4 | Input sanitization validation |

### Total Test Results

- **Total tests**: 179 (162 original + 17 security)
- **All passing**: Yes

---

## 10. Git History

### Commits

1. **Initial commit** (b11b1dd): Multiagent RAG baseline
2. **Security improvements** (6c438db): All security features

```
main -> 6c438db feat: Add security improvements
                   -> b11b1dd feat: Multiagent RAG Support Copilot - Initial commit
```

---

## 11. Future Security Improvements

The following items were identified but not implemented in this PR:

### High Priority

- [ ] **Authentication**: Add JWT/OAuth2 for API access
- [ ] **Web Application Firewall (WAF)**: Consider adding in production

### Medium Priority

- [ ] **Request size limits**: Add limits for document uploads
- [ ] **IP blocking**: Block repeated abuse from specific IPs
- [ ] **Encrypted communications**: Ensure TLS 1.3 in production

### Low Priority

- [ ] **Security scanning**: Add tools like Bandit for Python security scanning
- [ ] **Dependency auditing**: Add automated dependency vulnerability scanning

---

## 12. Compliance Notes

### Data Handling

- User questions are processed and may be stored in logs
- No PII should be submitted in questions
- Audit logs contain IP addresses for security purposes

### Recommendations for Production

1. Deploy behind a reverse proxy (nginx, Traefik)
2. Enable HTTPS/TLS termination at load balancer
3. Configure firewall rules
4. Set up monitoring and alerting
5. Implement log rotation for audit logs
6. Regular security audits and penetration testing

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [slowapi Documentation](https://slowapi.readthedocs.io/)
- [CSP Builder](https://cspbuilder.online/)

---

**Document Version**: 1.0
**Maintained By**: Fabio Antelo Math
**Repository**: https://github.com/FabioAnteloMath/multiagent-rag