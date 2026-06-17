from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security_service import get_security_service
from app.services.rag_pipeline import RagPipeline
from app.services.provider_router import ProviderRouter
from app.services.quota_tracker import QuotaExceeded
from app.agents.master_agent import MasterAgent
from app.agents.dynamic_agent import DynamicAgent
from app.models import Agent, Collection

router = APIRouter()
pipeline = RagPipeline()

limiter = Limiter(key_func=get_remote_address)


def get_master_agent(db: Session = Depends(get_db)) -> MasterAgent:
    """Create MasterAgent with the current roster of active agents from the DB.

    Each active Agent row is wrapped in a DynamicAgent that uses the agent's
    own provider/model/prompt/collection. Agents without a collection are
    skipped (they would have no FAISS index to search).

    A ProviderRouter is built once and shared across all agents so every
    LLM call goes through the same quota + fallback machinery.
    """
    agents_dict: dict[str, "DynamicAgent"] = {}
    classifier_provider = "minimax"
    classifier_model = "MiniMax-M2.7"

    # Build the router once. The router's `ask` method is a plain
    # callable that AgentLLM can use as `router_callable`. This
    # indirection lets the agent stay decoupled from SQLAlchemy.
    router = ProviderRouter(db)
    router_callable = router.ask

    rows = db.query(Agent).filter(Agent.is_active == True).all()
    for row in rows:
        # Classifier row: special case - used to configure the LLM classifier
        if (row.specialty or "").strip().lower() == "classifier" or "classif" in (row.name or "").lower():
            classifier_provider = row.provider or classifier_provider
            classifier_model = row.model_name or classifier_model
            continue

        if not row.collection_id:
            # Skip agents with no collection - they can't search anything
            continue

        col = db.query(Collection).filter(Collection.id == row.collection_id).first()
        if not col:
            continue

        try:
            agent = DynamicAgent(agent_row=row, collection_name=col.name, router_callable=router_callable)
        except Exception as e:
            print(f"[get_master_agent] failed to build agent '{row.name}': {e}")
            continue

        # If two agents map to the same category, keep the first and log
        if agent.category in agents_dict:
            print(f"[get_master_agent] duplicate category '{agent.category}', keeping first")
            continue
        agents_dict[agent.category] = agent

    return MasterAgent(
        agents=agents_dict,
        classifier_provider=classifier_provider,
        classifier_model=classifier_model,
        router_callable=router_callable,
    )


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
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=4, ge=1, le=10)
    mode: str = Field(default="auto", pattern="^(baseline|auto|single_rag)$")
    # force_agent accepts any non-empty string (matches an agent's category or specialty).
    # Kept as a plain Optional[str] because agents are DB-driven and have no fixed list.
    force_agent: Optional[str] = Field(default=None, min_length=1, max_length=64)

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        security = get_security_service()
        result = security.check_sync(v)
        if not result.is_safe:
            raise ValueError("Invalid input detected")
        return v


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
    # Transparency into *how* the question was routed. Lets the UI show
    # "via keyword match (hyde)" instead of just the chosen agent name.
    routing: Optional[dict] = None


@router.get("/health")
@limiter.limit("60/minute")
def healthcheck(request: Request) -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit("10/minute")
def ingest_documents(request: Request, payload: IngestRequest) -> IngestResponse:
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
@limiter.limit("30/minute")
def ask_question(request: Request, payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
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
                collection_searched=getattr(result, 'collection_searched', None),
                routing=getattr(result, 'routing', None),
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
                confidence=result.confidence,
                routing=result.routing,
            )
    except RuntimeError as exc:
        print(f"[API] RuntimeError: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except QuotaExceeded as qe:
        # Every provider is exhausted for the rolling 24h window.
        # 429 lets clients back off intelligently.
        print(f"[API] QuotaExceeded: {qe}")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "All provider quotas exhausted",
                "provider": qe.provider,
                "status": qe.status,
            },
            headers={
                "Retry-After": "3600",
                "X-Quota-Remaining": "0",
            },
        ) from qe
    except Exception as exc:
        print(f"[API] Exception: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ============================================================================
# A/B Test endpoint - same question, multiple models, side-by-side
# ============================================================================


class ABModelSpec(BaseModel):
    provider: str
    model_name: str
    temperature: float = 0.3
    max_tokens: int = 2000
    top_p: float = 0.9
    system_prompt: Optional[str] = None  # override; if null uses the agent's prompt


class ABTestRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=3, ge=1, le=10)
    agent_category: Optional[str] = None  # e.g. "rag", "suporte_api"
    collection_name: Optional[str] = None  # direct override
    models: list[ABModelSpec] = Field(min_length=1, max_length=6)

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        security = get_security_service()
        result = security.check_sync(v)
        if not result.is_safe:
            raise ValueError("Invalid input detected")
        return v


class ABModelResult(BaseModel):
    provider: str
    model_name: str
    temperature: float
    answer: str
    sources: list[str]
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    model_loaded: bool
    error: Optional[str] = None
    raw_usage: dict = Field(default_factory=dict)


class ABTestResponse(BaseModel):
    question: str
    collection_used: str
    retrieval_chunks: int
    context_chars: int
    system_prompt_used: str
    results: list[ABModelResult]
    timestamp: str
    total_elapsed_ms: float


@router.post("/ask/ab", response_model=ABTestResponse)
@limiter.limit("10/minute")
def ask_ab_test(
    request: Request,
    payload: ABTestRequest,
    db: Session = Depends(get_db),
) -> ABTestResponse:
    """A/B test: same question + same retrieval, multiple models side-by-side.

    Returns each model's answer, latency, token usage, and estimated cost.
    Use to compare prompt flexibility, response quality, and speed across providers.
    """
    from app.agents.dynamic_agent import DynamicAgent
    from app.services.llm_providers import ModelProviderFactory
    import time
    from datetime import datetime

    t_start = time.time()
    print(f"[AB] start | question={payload.question[:50]!r} | models={len(payload.models)}")

    # 1. Resolve which collection to use
    collection_name = payload.collection_name
    system_prompt_override = None

    if not collection_name and payload.agent_category:
        agent_row = (
            db.query(Agent)
            .filter(Agent.is_active == True)
            .filter(Agent.specialty == payload.agent_category)
            .first()
        )
        if not agent_row:
            raise HTTPException(
                status_code=404,
                detail=f"No active agent found for category '{payload.agent_category}'",
            )
        col = db.query(Collection).filter(Collection.id == agent_row.collection_id).first()
        if not col:
            raise HTTPException(
                status_code=400,
                detail=f"Agent '{payload.agent_category}' has no linked collection",
            )
        collection_name = col.name
        system_prompt_override = (
            agent_row.system_prompt
            + (f"\n\nGuidelines:\n{agent_row.guidelines}" if agent_row.guidelines else "")
            + (f"\n\nPersonality: {agent_row.personality}" if agent_row.personality else "")
        )

    if not collection_name:
        raise HTTPException(
            status_code=400,
            detail="Must provide either 'agent_category' or 'collection_name'",
        )

    # 2. Single retrieval - same chunks for all models
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    from pathlib import Path

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
    )
    project_root = Path(__file__).resolve().parents[3]
    index_dir = project_root / "data" / "faiss" / collection_name
    index_file = index_dir / "index.faiss"
    if not index_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No FAISS index for collection '{collection_name}'",
        )
    vectorstore = FAISS.load_local(
        str(index_dir), embeddings, allow_dangerous_deserialization=True,
    )
    docs = vectorstore.similarity_search(payload.question, k=payload.top_k)

    context = "\n\n---\n\n".join([d.page_content for d in docs])
    sources = []
    for d in docs:
        src = d.metadata.get("source", "unknown")
        sources.append(src)
    sources = sorted(set(sources))

    # 3. Build the prompt - same template for all models
    base_system = system_prompt_override or (
        "You are a helpful assistant. Use ONLY the provided context to answer. "
        "If the answer isn't in the context, say so clearly."
    )
    full_prompt = (
        f"{base_system}\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {payload.question}\n\n"
        f"Answer:"
    )

    # 4. Run each model — wrapped in the ProviderRouter for fallback + quota tracking
    router_svc = ProviderRouter(db)
    results: list[ABModelResult] = []
    for spec in payload.models:
        t0 = time.time()
        spec_sys = spec.system_prompt or base_system
        if spec.system_prompt:
            spec_prompt = f"{spec.system_prompt}\n\nContext:\n{context}\n\nQuestion: {payload.question}\n\nAnswer:"
        else:
            spec_prompt = full_prompt

        try:
            # The router tries the requested provider first, then walks
            # the fallback chain. Quota tracking + circuit breaker apply.
            answer, usage = router_svc.ask(
                preferred=spec.provider,
                model=spec.model_name,
                prompt=spec_prompt,
                temperature=spec.temperature,
                max_tokens=spec.max_tokens,
                top_p=spec.top_p,
            )
            latency_ms = (time.time() - t0) * 1000

            # The actual provider that ended up serving the request may
            # differ from spec.provider if a fallback happened.
            served_provider = usage.get("provider", spec.provider)
            served_model = usage.get("model", spec.model_name)
            fell_back = served_provider != spec.provider

            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0) or (prompt_tokens + completion_tokens)

            # Estimate cost using the actually-served provider's pricing
            cost = 0.0
            try:
                llm_for_cost = ModelProviderFactory.create(served_provider, served_model)
                if hasattr(llm_for_cost, "estimate_cost"):
                    cost = llm_for_cost.estimate_cost(prompt_tokens, completion_tokens)
            except Exception:
                pass

            results.append(ABModelResult(
                provider=served_provider,
                model_name=served_model,
                temperature=spec.temperature,
                answer=answer,
                sources=sources,
                latency_ms=round(latency_ms, 1),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=round(cost, 6),
                model_loaded=True,
                raw_usage=usage,
            ))
            tag = f" (fallback from {spec.provider})" if fell_back else ""
            print(f"[AB]   {served_provider}:{served_model}{tag} ok | {latency_ms:.0f}ms | {total_tokens} tok")
        except QuotaExceeded as qe:
            # Whole request is short-circuited because every provider is
            # exhausted — return 429 with structured info.
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "All provider quotas exhausted",
                    "provider": qe.provider,
                    "status": qe.status,
                },
                headers={
                    "Retry-After": "3600",
                    "X-Quota-Remaining": "0",
                },
            ) from qe
        except Exception as e:
            latency_ms = (time.time() - t0) * 1000
            results.append(ABModelResult(
                provider=spec.provider,
                model_name=spec.model_name,
                temperature=spec.temperature,
                answer="",
                sources=[],
                latency_ms=round(latency_ms, 1),
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.0,
                model_loaded=False,
                error=str(e),
            ))
            print(f"[AB]   {spec.provider}:{spec.model_name} FAILED | {e}")

    total_ms = (time.time() - t_start) * 1000
    return ABTestResponse(
        question=payload.question,
        collection_used=collection_name,
        retrieval_chunks=len(docs),
        context_chars=len(context),
        system_prompt_used=base_system[:200] + ("..." if len(base_system) > 200 else ""),
        results=results,
        timestamp=datetime.utcnow().isoformat(),
        total_elapsed_ms=round(total_ms, 1),
    )