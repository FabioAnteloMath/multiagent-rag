"""GET /api/usage — current quota + circuit-breaker status.

Read-only. Returns the live snapshot of:
  - how many requests each provider has served in the rolling window
  - how many remain
  - whether the circuit breaker is open
  - which provider is the next fallback in the chain

No auth in the portfolio build; if you deploy this for real, gate it
behind an admin token.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import UsageLog
from app.services.provider_router import ProviderRouter
from app.services.quota_tracker import QuotaTracker, is_quota_enabled


router = APIRouter()


@router.get("/usage")
def get_usage(db: Session = Depends(get_db)) -> dict:
    quota = QuotaTracker(db)
    router_svc = ProviderRouter(db)
    return {
        "enabled": is_quota_enabled(),
        "providers": router_svc.chain_status(),
        "totals": {
            "rows_logged": db.query(func.count(UsageLog.id)).scalar() or 0,
        },
    }
