"""Quota tracker — persistent daily request counters per provider.

Stores usage in the same SQLite database as the rest of the app (see
`app.models.UsageLog`). Counters are queried with a rolling 24h window
(UTC) so behaviour matches real billing windows — quota "resets" exactly
24h after the first request, not at midnight.

Configuration is read from environment variables so the limits can be
tuned without code changes:

    QUOTA_GROQ_DAILY          default 13000   (free tier: 14.4k → 10% margin)
    QUOTA_GEMINI_DAILY        default 1400    (free tier: 1500 → margin)
    QUOTA_MINIMAX_DAILY       default 5000    (set conservatively)
    QUOTA_OLLAMA_DAILY        default 999999  (local, effectively unlimited)
    QUOTA_WINDOW_HOURS        default 24
    QUOTA_ENABLED             default true
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import UsageLog


# Default limits — under each provider's published free tier.
DEFAULT_LIMITS: dict[str, int] = {
    "groq": 13_000,
    "gemini": 1_400,
    "minimax": 5_000,
    "ollama": 999_999,  # local; treat as unlimited
}


def _env_limit(provider: str) -> int:
    """Read QUOTA_<PROVIDER>_DAILY; fall back to DEFAULT_LIMITS or 1000."""
    key = f"QUOTA_{provider.upper()}_DAILY"
    val = os.getenv(key)
    if val and val.isdigit():
        return int(val)
    return DEFAULT_LIMITS.get(provider, 1_000)


def _window_hours() -> int:
    raw = os.getenv("QUOTA_WINDOW_HOURS", "24")
    try:
        return max(1, int(raw))
    except ValueError:
        return 24


def is_quota_enabled() -> bool:
    """Feature flag — set QUOTA_ENABLED=false to disable enforcement."""
    return os.getenv("QUOTA_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


class QuotaTracker:
    """Counts requests per provider inside a rolling time window.

    The window is per-provider, anchored at the oldest counted request.
    We approximate "24h rolling" with `created_at >= now - window_hours`
    — this is good enough for portfolio usage and avoids needing a
    separate metadata table.
    """

    def __init__(self, db: Session):
        self.db = db
        self.window = timedelta(hours=_window_hours())

    # ---- read path ----

    def count_in_window(self, provider: str) -> int:
        """How many requests have we made to this provider in the window?"""
        cutoff = datetime.utcnow() - self.window
        # Only count successful requests toward the quota — a 429 from
        # the upstream didn't consume our daily allowance (their limit
        # is separate). But we DO want to track failures for visibility.
        # For quota enforcement we count *all* attempts so abuse paths
        # can't hide behind a "failed" prefix.
        q = (
            self.db.query(func.count(UsageLog.id))
            .filter(UsageLog.provider == provider)
            .filter(UsageLog.created_at >= cutoff)
        )
        return int(q.scalar() or 0)

    def limit(self, provider: str) -> int:
        return _env_limit(provider)

    def remaining(self, provider: str) -> int:
        return max(0, self.limit(provider) - self.count_in_window(provider))

    def is_exhausted(self, provider: str) -> bool:
        if not is_quota_enabled():
            return False
        return self.count_in_window(provider) >= self.limit(provider)

    def status(self, provider: str) -> dict:
        """Snapshot for /api/usage."""
        used = self.count_in_window(provider)
        lim = self.limit(provider)
        return {
            "provider": provider,
            "used": used,
            "limit": lim,
            "remaining": max(0, lim - used),
            "exhausted": used >= lim,
            "window_hours": _window_hours(),
        }

    def all_status(self) -> list[dict]:
        return [self.status(p) for p in sorted(DEFAULT_LIMITS.keys())]

    # ---- write path ----

    def record(
        self,
        provider: str,
        model: str,
        *,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        success: bool = True,
        fallback_from: Optional[str] = None,
        error: str = "",
    ) -> UsageLog:
        """Append a usage row. Caller is responsible for `db.commit()`."""
        row = UsageLog(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            success=bool(success),
            fallback_from=fallback_from,
            error=error[:500] if error else "",
        )
        self.db.add(row)
        self.db.flush()  # populate row.id without committing
        return row


# ---------------------------------------------------------------------------
# Custom exception — caught by FastAPI handler and turned into HTTP 429
# ---------------------------------------------------------------------------

class QuotaExceeded(Exception):
    """Raised when a provider's quota is exhausted for the current window.

    Carries the provider name and the status dict so the API layer can
    return useful headers and a structured JSON body.
    """

    def __init__(self, provider: str, status: dict):
        self.provider = provider
        self.status = status
        super().__init__(f"Quota exceeded for provider '{provider}'")
