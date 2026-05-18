from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.rag_pipeline import RagPipeline
from app.agents.master_agent import MasterAgent
from app.models import Agent

router = APIRouter()
pipeline = RagPipeline()


def get_master_agent(db: Session = Depends(get_db)) -> MasterAgent:
    """Create MasterAgent with current agent configurations from database."""
    agents_config = {}
    classifier_config = {}

    agents = db.query(Agent).filter(Agent.is_active == 1).all()
    for agent in agents:
        agent_key = agent.specialty.lower().replace(" ", "_") if agent.specialty else agent.name.lower().replace(" ", "_")
        if agent_key in ["suporte_api", "database", "devops", "general"]:
            agents_config[agent_key] = {
                "provider": agent.provider,
                "model_name": agent.model_name,
                "temperature": float(agent.temperature) if agent.temperature else 0.3,
                "system_prompt": agent.system_prompt or ""
            }
        elif agent_key == "classifier" or "classif" in agent_key:
            classifier_config = {
                "provider": agent.provider,
                "model_name": agent.model_name,
                "temperature": float(agent.temperature) if agent.temperature else 0.1,
            }

    if classifier_config:
        agents_config["classifier"] = classifier_config

    return MasterAgent(agent_configs=agents_config if agents_config else None)


class IngestRequest(BaseModel):
    clear_existing: bool = True
    chunk_size: int = Field(default=600, ge=200, le=2000)
    chunk_overlap: int = Field(default=80, ge=0, le=500)


class IngestResponse(BaseModel):
    files_indexed: int
    documents_loaded: int
    chunks_created: int
    collection_name: str
    vector_backend: str


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int = Field(default=4, ge=1, le=10)
    mode: str = Field(default="auto", pattern="^(baseline|auto|single_rag)$")
    force_agent: Optional[str] = Field(default=None, pattern="^(suporte_api|database|devops)$")


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    agent_used: list[str]
    steps: list[str]
    needs_clarifying: bool = False
    tokens_used: int = 0
    thinking: str = ""
    model_used: str = ""
    total_time_ms: float = 0.0
    confidence: float = 0.0
    collection_searched: Optional[str] = None


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ingest", response_model=IngestResponse)
def ingest_documents(payload: IngestRequest) -> IngestResponse:
    if payload.chunk_overlap >= payload.chunk_size:
        raise HTTPException(
            status_code=400,
            detail="chunk_overlap must be less than chunk_size.",
        )

    try:
        result = pipeline.ingest(
            clear_existing=payload.clear_existing,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap,
        )
        return IngestResponse(**result.__dict__)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    print(f"[API] ask_question called - mode: {payload.mode}, question: {payload.question[:50]}...")
    try:
        if payload.mode == "baseline":
            print("[API] Using baseline pipeline")
            result = pipeline.ask(question=payload.question, top_k=payload.top_k)
            print(f"[API] Baseline result: {result.answer[:50]}...")
            return AskResponse(
                answer=result.answer,
                sources=result.sources,
                agent_used=["baseline"],
                steps=[],
                collection_searched=None
            )
        elif payload.mode == "single_rag":
            print("[API] Using single_rag mode")
            master_agent = get_master_agent(db)
            result = master_agent.single_rag_ask(
                question=payload.question,
                force_agent=payload.force_agent
            )
            print(f"[API] single_rag result: {result.answer[:50]}...")
            return AskResponse(
                answer=result.answer,
                sources=result.sources,
                agent_used=result.agent_used,
                steps=result.steps,
                needs_clarifying=result.needs_clarifying,
                tokens_used=result.tokens_used,
                thinking=result.thinking,
                model_used=result.model_used,
                total_time_ms=result.total_time_ms,
                confidence=result.confidence,
                collection_searched=getattr(result, 'collection_searched', None)
            )
        else:
            print("[API] Using MasterAgent (auto)")
            master_agent = get_master_agent(db)
            result = master_agent.ask(
                question=payload.question,
                force_agent=payload.force_agent
            )
            print(f"[API] MasterAgent result: {result.answer[:50]}...")
            return AskResponse(
                answer=result.answer,
                sources=result.sources,
                agent_used=result.agent_used,
                steps=result.steps,
                needs_clarifying=result.needs_clarifying,
                tokens_used=result.tokens_used,
                thinking=result.thinking,
                model_used=result.model_used,
                total_time_ms=result.total_time_ms,
                confidence=result.confidence
            )
    except RuntimeError as exc:
        print(f"[API] RuntimeError: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        print(f"[API] Exception: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc