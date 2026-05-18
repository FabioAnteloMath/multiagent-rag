from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.core.database import init_db
from app.api.chat_routes import router as api_router
from app.api.routes.documents import router as documents_router
from app.api.routes.collections import router as collections_router
from app.api.routes.agents import router as agents_router

app = FastAPI(title="Multiagent RAG - Support Copilot", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(collections_router, prefix="/api")
app.include_router(agents_router, prefix="/api")

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