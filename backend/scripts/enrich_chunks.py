"""Enrich the seeded chunks with realistic content for screenshots.

The base seed script only writes placeholder "[seed] chunk X/Y of {filename}"
into chunks. That makes any RAG answer incoherent. This script rewrites the
chunk content for all indexed chunks with short, topic-specific paragraphs
so the chat UI screenshot shows a real, useful answer.

Idempotent — safe to run multiple times.
"""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import os
os.environ.setdefault("DATA_DIR", str(BACKEND_ROOT / "data"))

from app.core.database import SessionLocal  # noqa: E402
from app.models import Chunk, Document  # noqa: E402

# Realistic, short paragraphs keyed by filename. Each chunk gets a piece
# so the FAISS retriever returns meaningful context.
CONTENT = {
    "faq-authentication.md": [
        "# Authentication FAQ",
        "Q: Users are getting 401 Unauthorized on the API. What now?",
        "A: 401 means the JWT is missing, expired, or invalid. First check the `Authorization: Bearer <token>` header. The token usually comes from `/auth/login` and lives ~1h.",
        "If the token is fresh and still rejected, verify the signing key on the API side matches the issuer (`JWT_PUBLIC_KEY` env var). A redeploy with a rotated key is the most common cause.",
        "For 403, the token is valid but the user lacks the required role/scope. Check `auth.requires('admin')` decorators and the user's roles in the auth service.",
    ],
    "runbook-api-gateway.md": [
        "# API Gateway Incident Runbook",
        "## Symptoms",
        "Spike in 5xx from the gateway, latency > 2s p95, health check failing on at least one upstream.",
        "## First 5 minutes",
        "1. Page the on-call SRE in #incidents.\n2. Check the gateway dashboard: which upstream is red?",
        "3. Tail the gateway logs: `kubectl logs -n api deploy/gateway --tail=200 -f`. Look for `circuit_open=true` on any upstream.",
        "## Mitigation",
        "If a single upstream is degraded, force-failover with `kubectl annotate upstream/<name> failover=dr` and the gateway will drain traffic to the DR region within 30s.",
    ],
    "sla-escalation.md": [
        "# SLA Targets & Escalation",
        "Tier-1 (login, payments): 99.95% monthly uptime, 100ms p95 latency.",
        "Tier-2 (general API): 99.9% monthly, 250ms p95.",
        "If a Sev-1 page is open for >15 min without owner, it auto-escalates to the next on-call tier. Pager rotates weekly — see `glossary.md` for the rotation list.",
    ],
    "troubleshooting-postgres.txt": [
        "Postgres slow-query troubleshooting",
        "Step 1: enable pg_stat_statements and find the top queries by total time.",
        "Step 2: run EXPLAIN ANALYZE on the worst offender. Look for Seq Scan on tables > 10k rows, or nested-loop joins on unindexed columns.",
        "Step 3: add the index. For B-tree on a single column, `CREATE INDEX CONCURRENTLY idx_name ON table(col);` — never use plain CREATE INDEX in prod.",
    ],
    "cache-incident-2026-04-18.md": [
        "# Post-mortem: cache stampede (2026-04-18)",
        "A Redis key expired at peak traffic. 1,200 concurrent requests hit the database simultaneously because the cache miss logic did not use a single-flight or lock pattern.",
        "## Fix",
        "Wrapped the read path in a per-key `asyncio.Lock` with a 5s TTL. If the lock is held, fall back to a stale-while-revalidate read from a secondary cache.",
        "## Prevention",
        "All cache lookups now go through `cache.get_or_compute(key, loader, ttl=60)`. Adding a new direct Redis read is a CODEOWNERS review red flag.",
    ],
    "observability-alerts.md": [
        "# Alerting thresholds and runbooks",
        "API error rate > 1% for 5m → page on-call.",
        "p99 latency > 1.5s for 10m → Slack #ops-alerts (no page).",
        "Disk > 85% on any prod node → auto-ticket + Slack.",
        "Every alert must link a runbook in its description. No unowned alerts allowed — `promtool check rules` will fail the build otherwise.",
    ],
    "rollback-procedure.md": [
        "# Production Rollback Procedure",
        "## When to roll back",
        "- Sev-1 incident introduced by the current release.\n- Error rate > 5% within 30 min of deploy.\n- Migration failed mid-flight and forward-fix is risky.",
        "## Steps",
        "1. `kubectl rollout undo deployment/api` — restores the previous ReplicaSet.\n2. Verify with `kubectl rollout status deployment/api --timeout=120s`.",
        "3. Run smoke tests: `pwsh scripts/smoke_prod.ps1`.\n4. Page the release captain in #releases with the rollback SHA.",
        "## Don't",
        "- Don't run a forward-fix migration while rolling back the app — split into two deploys.\n- Don't skip the smoke tests, even at 3am.",
    ],
    "release-checklist.md": [
        "# Pre-release Smoke Checklist",
        "- [ ] All CI checks green on `main`.\n- [ ] Migration runs and rolls back cleanly in staging.\n- [ ] Feature flag default state set.\n- [ ] Release notes drafted in `docs/releases/`.\n- [ ] On-call notified in #releases.",
    ],
    "deployment-strategy.md": [
        "# Deployment strategies",
        "## Blue/green",
        "Two identical environments. Switch the load balancer. Instant rollback. Costs 2x infra.",
        "## Canary",
        "New version takes 5% traffic for 30 min, then 50%, then 100%. Cheaper, slower rollback. Good default for risky changes.",
        "## Recommendation",
        "Use canary for API changes. Use blue/green for migrations that change the DB schema.",
    ],
    "onboarding.md": [
        "# New engineer onboarding",
        "Day 1: laptop setup, accounts, walkthrough of the monorepo.\nDay 2-3: paired first PR.\nWeek 1: ship a small change end-to-end.\nWeek 2: own a small on-call rotation pair.",
        "Buddy: assigned in the first standup. Slack them any question, no question is too small.",
    ],
    "glossary.md": [
        "# Internal glossary",
        "**PR** — pull request.\n**Sev-1/2/3** — severity levels for incidents.\n**DR** — disaster recovery region.\n**RAG** — retrieval-augmented generation.",
        "**Canary** — partial rollout of a new version to catch regressions early.",
    ],
    "contact-info.md": [
        "# On-call rotations",
        "Platform: rotates weekly, see PagerDuty schedule `platform-primary`.\nAPI: `api-primary`.\nData: `data-primary`.",
        "If you're not sure who owns a service, check the `team` label on the repo.",
    ],
}

DEFAULT_CHUNKS = {
    "api-rate-limits.md": "API rate limit policy: 1000 req/hour for free tier, 10k for pro. Burst up to 50 in 10s. Hitting the limit returns HTTP 429 with Retry-After.",
    "k8s-rollback.md": "K8s rollback: kubectl rollout undo deployment/<name>. To check status: kubectl rollout status deployment/<name>. Rollback keeps the same ConfigMap but reverts the pod template.",
    "oncall-rotation.md": "On-call rotation schedule is in PagerDuty. Primary rotates weekly Monday 10:00 local. Secondary is always 1 week behind primary. Escalation goes to manager after 30 min unanswered.",
    "payment-refunds.md": "Refund policy: full refund within 30 days, partial 50% within 60 days, no refund after 60. Refunds are issued to the original payment method within 5-7 business days.",
    "postgres-backup.md": "Postgres backups: nightly pg_dump to S3, retained 30 days. Point-in-time recovery via WAL archiving. Test restore quarterly — last test 2026-03-15 succeeded in 12 min for a 4GB database.",
    "security-incident.md": "Security incident response: 1) Contain — revoke compromised credentials, isolate affected hosts. 2) Eradicate — patch the vulnerability. 3) Recover — restore from clean backup if needed. 4) Learn — post-mortem within 5 business days.",
}


def main():
    db = SessionLocal()
    try:
        docs = db.query(Document).all()
        updated = 0
        for doc in docs:
            chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).order_by(Chunk.chunk_index).all()
            pool = CONTENT.get(doc.filename) or [DEFAULT_CHUNKS.get(doc.filename, f"[seed] {doc.filename} content placeholder.")]
            for i, chunk in enumerate(chunks):
                chunk.content = pool[i % len(pool)]
            updated += len(chunks)
        db.commit()
        print(f"Updated {updated} chunks across {len(docs)} documents.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
