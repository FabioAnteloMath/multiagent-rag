"""Unit tests for the quota tracker.

We use an in-memory SQLite session to avoid touching the real `data/`
directory. This keeps the tests fast and self-contained.
"""
import os
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import UsageLog
from app.services.provider_router import _fallback_chain
from app.services.quota_tracker import (
    DEFAULT_LIMITS,
    QuotaTracker,
    is_quota_enabled,
)


# In-memory SQLite for tests
@pytest.fixture
def db_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestQuotaCounter:
    def test_starts_at_zero(self, db_session):
        qt = QuotaTracker(db_session)
        assert qt.count_in_window("groq") == 0
        assert qt.remaining("groq") == qt.limit("groq")

    def test_increments_on_record(self, db_session):
        qt = QuotaTracker(db_session)
        for i in range(5):
            qt.record(provider="groq", model="llama-3.1-8b-instant")
        db_session.commit()
        assert qt.count_in_window("groq") == 5
        assert qt.remaining("groq") == qt.limit("groq") - 5

    def test_ignores_old_records(self, db_session):
        qt = QuotaTracker(db_session)
        # Insert 3 rows with old timestamps (outside window)
        for i in range(3):
            row = UsageLog(
                provider="groq", model="x",
                created_at=datetime.utcnow() - timedelta(hours=48),
            )
            db_session.add(row)
        db_session.commit()
        assert qt.count_in_window("groq") == 0

    def test_exhausted(self, db_session, monkeypatch):
        # Set a tiny limit for fast test
        monkeypatch.setenv("QUOTA_GROQ_DAILY", "3")
        qt = QuotaTracker(db_session)
        for i in range(3):
            qt.record(provider="groq", model="x")
        db_session.commit()
        assert qt.is_exhausted("groq") is True
        assert qt.remaining("groq") == 0

    def test_not_exhausted_below_limit(self, db_session, monkeypatch):
        monkeypatch.setenv("QUOTA_GROQ_DAILY", "10")
        qt = QuotaTracker(db_session)
        for i in range(5):
            qt.record(provider="groq", model="x")
        db_session.commit()
        assert qt.is_exhausted("groq") is False
        assert qt.remaining("groq") == 5


class TestQuotaStatus:
    def test_status_shape(self, db_session):
        qt = QuotaTracker(db_session)
        s = qt.status("groq")
        assert s["provider"] == "groq"
        assert s["used"] == 0
        assert s["limit"] > 0
        assert s["remaining"] == s["limit"]
        assert s["exhausted"] is False
        assert s["window_hours"] == 24

    def test_all_status_lists_all_providers(self, db_session):
        qt = QuotaTracker(db_session)
        statuses = qt.all_status()
        providers = {s["provider"] for s in statuses}
        # Default limits include all 4 providers
        assert {"groq", "gemini", "minimax", "ollama"} <= providers


class TestQuotaFeatureFlag:
    def test_disabled_does_not_block(self, db_session, monkeypatch):
        monkeypatch.setenv("QUOTA_ENABLED", "false")
        monkeypatch.setenv("QUOTA_GROQ_DAILY", "2")
        qt = QuotaTracker(db_session)
        for i in range(10):
            qt.record(provider="groq", model="x")
        db_session.commit()
        assert qt.count_in_window("groq") == 10  # still counted
        assert qt.is_exhausted("groq") is False  # but not enforced
        assert is_quota_enabled() is False


class TestFallbackChain:
    def test_default_chain(self, monkeypatch):
        monkeypatch.delenv("FALLBACK_CHAIN", raising=False)
        assert _fallback_chain() == ["groq", "gemini", "minimax", "ollama"]

    def test_custom_chain(self, monkeypatch):
        monkeypatch.setenv("FALLBACK_CHAIN", "ollama,groq")
        assert _fallback_chain() == ["ollama", "groq"]


class TestDefaultLimits:
    def test_groq_under_free_tier(self):
        # Groq free tier is 14.4k; default should be safely under
        assert DEFAULT_LIMITS["groq"] <= 14_400
        assert DEFAULT_LIMITS["groq"] >= 10_000  # not pathologically low

    def test_gemini_under_free_tier(self):
        # Gemini free tier ~1500/day
        assert DEFAULT_LIMITS["gemini"] <= 1_500
        assert DEFAULT_LIMITS["gemini"] >= 1_000

    def test_ollama_high(self):
        assert DEFAULT_LIMITS["ollama"] >= 100_000
