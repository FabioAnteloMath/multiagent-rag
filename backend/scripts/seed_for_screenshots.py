"""Seed script for capturing demo screenshots.

Creates a realistic dataset for the multiagent-rag UI:
- 4 collections (SuporteAPI, Database, DevOps, General)
- 12 documents (3 per collection)
- 5 agents (one per collection + a generalist + a rag specialist)
- 30 usage_log rows spread across providers (with 2 failures to
  exercise the circuit-breaker UI)

This is a development-only helper. It is invoked manually before
taking screenshots, and is not part of the deployed app.

Usage:
    cd backend
    python scripts/seed_for_screenshots.py
"""
import os
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Use a project-local DB so we don't clobber any real one.
os.environ.setdefault("DATA_DIR", str(BACKEND_ROOT / "data"))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Agent, Chunk, Collection, Document, ProcessingLog, UsageLog  # noqa: E402


def reset_db():
    db_path = BACKEND_ROOT / "data" / "db" / "multiagent_rag.db"
    if db_path.exists():
        db_path.unlink()
    Base.metadata.create_all(bind=engine)


def seed_collections(db) -> dict[str, str]:
    rows = [
        Collection(name="SuporteAPI", description="API, gateway, JWT, runbooks",
                   is_default=True),
        Collection(name="Database", description="Postgres, Redis, slow queries, indexes",
                   is_default=False),
        Collection(name="DevOps", description="CI/CD, deploy, rollback, monitoring",
                   is_default=False),
        Collection(name="General", description="Cross-team knowledge base and FAQs",
                   is_default=False),
    ]
    db.add_all(rows)
    db.commit()
    return {c.name: c.id for c in db.query(Collection).all()}


def seed_documents(db, col_ids: dict[str, str]) -> None:
    plan = [
        ("SuporteAPI", "faq-authentication.md", "FAQ for 401/403 JWT and gateway errors", "md"),
        ("SuporteAPI", "runbook-api-gateway.md", "Step-by-step gateway incident runbook", "md"),
        ("SuporteAPI", "sla-escalation.md", "SLA targets and escalation policy", "md"),
        ("Database", "troubleshooting-postgres.txt", "Postgres slow query troubleshooting", "txt"),
        ("Database", "cache-incident-2026-04-18.md", "Post-mortem: cache stampede incident", "md"),
        ("Database", "observability-alerts.md", "Alerting thresholds and runbooks", "md"),
        ("DevOps", "rollback-procedure.md", "How to roll back a deploy in production", "md"),
        ("DevOps", "release-checklist.md", "Pre-release smoke test checklist", "md"),
        ("DevOps", "deployment-strategy.md", "Blue/green vs canary deploy guide", "md"),
        ("General", "onboarding.md", "New engineer onboarding walkthrough", "md"),
        ("General", "glossary.md", "Internal acronyms and terms", "md"),
        ("General", "contact-info.md", "How to reach each on-call rotation", "md"),
    ]
    for col_name, fname, desc, ftype in plan:
        doc = Document(
            filename=fname,
            file_type=ftype,
            file_size=random.randint(800, 6000),
            file_path=f"data/docs/{fname}",
            status="indexed",
            collection_id=col_ids[col_name],
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        n_chunks = random.randint(4, 9)
        for i in range(n_chunks):
            db.add(Chunk(
                document_id=doc.id,
                content=f"[seed] chunk {i+1}/{n_chunks} of {fname}",
                chunk_index=i,
                embedding_status="indexed",
                chunk_id=str(i),
            ))
        db.add(ProcessingLog(
            document_id=doc.id, status="completed",
            message=f"{n_chunks} chunks criados e indexados",
        ))
    db.commit()


def seed_agents(db, col_ids: dict[str, str]) -> None:
    plans = [
        # name, specialty, collection, provider, model, temperature, active
        ("API Support Agent", "suporte_api", "SuporteAPI",
         "groq", "llama-3.1-8b-instant", 0.2, True),
        ("Database Agent", "database", "Database",
         "minimax", "MiniMax-M2.7", 0.3, True),
        ("DevOps Agent", "devops", "DevOps",
         "minimax", "MiniMax-M2.7", 0.3, True),
        ("Generalist Agent", "general", "General",
         "ollama", "llama3.2:3b", 0.4, True),
        ("RAG Specialist (paused)", "rag", None,
         "gemini", "gemini-2.5-flash", 0.1, False),
    ]
    for name, spec, col, prov, model, temp, active in plans:
        db.add(Agent(
            name=name,
            specialty=spec,
            system_prompt=(
                f"You are a specialist in {spec}. Answer using only the "
                "provided context. Cite sources when relevant."
            ),
            guidelines="Be concise. Use code blocks for commands.",
            personality="Direct, technical, no fluff.",
            response_format="Markdown with code blocks.",
            examples="",
            collection_id=col_ids.get(col) if col else None,
            provider=prov,
            model_name=model,
            temperature=temp,
            is_active=active,
        ))
    db.commit()


def seed_usage(db) -> None:
    """Simulate ~30 calls spread across the day so /api/usage
    shows real numbers and a couple of failed calls to exercise
    the circuit-breaker banner.
    """
    random.seed(42)
    now = datetime.utcnow()
    providers = [
        ("groq", "llama-3.1-8b-instant", 0.92, 13000),
        ("gemini", "gemini-2.5-flash", 0.05, 1400),
        ("minimax", "MiniMax-M2.7", 0.02, 5000),
        ("ollama", "llama3.2:3b", 0.01, 999_999),
    ]
    rows = []
    for i in range(32):
        prov, model, fail_rate, _ = providers[i % len(providers)]
        success = random.random() > fail_rate
        rows.append(UsageLog(
            provider=prov,
            model=model,
            prompt_tokens=random.randint(200, 1500),
            completion_tokens=random.randint(80, 600),
            total_tokens=0,  # set below
            success=success,
            error="" if success else "rate limit (429)",
            created_at=now - timedelta(minutes=random.randint(1, 1200)),
        ))
    for r in rows:
        r.total_tokens = r.prompt_tokens + r.completion_tokens
    db.add_all(rows)
    db.commit()


def main() -> None:
    print("[seed] resetting database...")
    reset_db()
    db = SessionLocal()
    try:
        print("[seed] collections...")
        col_ids = seed_collections(db)
        print(f"          {len(col_ids)} collections created")
        print("[seed] documents + chunks...")
        seed_documents(db, col_ids)
        n_docs = db.query(Document).count()
        n_chunks = db.query(Chunk).count()
        print(f"          {n_docs} documents / {n_chunks} chunks")
        print("[seed] agents...")
        seed_agents(db, col_ids)
        n_agents = db.query(Agent).count()
        print(f"          {n_agents} agents")
        print("[seed] usage_log rows...")
        seed_usage(db)
        n_logs = db.query(UsageLog).count()
        print(f"          {n_logs} usage rows")
        print("[seed] done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
