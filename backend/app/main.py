from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import time

from app.core.database import init_db
from app.api.chat_routes import router as api_router
from app.api.routes.documents import router as documents_router
from app.api.routes.collections import router as collections_router
from app.api.routes.agents import router as agents_router
from app.api.routes.usage import router as usage_router

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Multiagent RAG - Support Copilot",
    version="0.2.0",
    description="AI-powered technical support system with multi-agent routing"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response

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

app.include_router(api_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(collections_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(usage_router, prefix="/api")

ui_dir = os.path.join(os.path.dirname(__file__), "ui")
if os.path.exists(ui_dir):
    app.mount("/static", StaticFiles(directory=ui_dir), name="static")

@app.on_event("startup")
def startup_event():
    init_db()
    print("Database initialized")

@app.get("/")
def root():
    index_path = os.path.join(ui_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "API is running. Access /docs for API documentation."}

@app.get("/api/info")
def api_info():
    return {
        "name": "Multiagent RAG - Support Copilot",
        "version": "0.2.0",
        "endpoints": {
            "documents": "/api/documents",
            "collections": "/api/collections",
            "agents": "/api/agents",
            "chat": "/api/ask"
        }
    }