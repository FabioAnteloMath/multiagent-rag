"""Unit tests for the ProviderRouter (fallback + circuit breaker).

We mock `ModelProviderFactory.create` to control which provider is
"called" and whether it succeeds. The tests assert:
  1. First provider in the chain is tried first
  2. On failure, the next provider is tried
  3. Quota exhaustion makes a provider skipped
  4. Circuit breaker opens after N failures and skips the provider
"""
import time
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.services.provider_router import (
    FAILURE_THRESHOLD,
    FAILURE_WINDOW_S,
    COOLDOWN_S,
    ProviderRouter,
)
from app.services.quota_tracker import QuotaExceeded, QuotaTracker


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _stub_provider(name: str, should_fail: bool, answer: str = "ok"):
    """Build a fake LLMProvider that records being called and returns / raises."""
    p = MagicMock()
    p.get_name.return_value = name
    if should_fail:
        p.generate_with_usage.side_effect = Exception(f"{name} blew up")
    else:
        p.generate_with_usage.return_value = (
            answer, {"provider": name, "model": "x", "total_tokens": 5},
        )
    return p


class TestFallbackBehavior:
    def test_first_provider_succeeds(self, db_session):
        with patch("app.services.provider_router.ModelProviderFactory.create") as mfc:
            mfc.side_effect = lambda provider, model: _stub_provider(provider, should_fail=False)
            router = ProviderRouter(db_session)
            answer, usage = router.ask(
                preferred="groq", model="llama-3.1-8b-instant", prompt="hi",
            )
            assert answer == "ok"
            assert usage["provider"] == "groq"
            # Only one provider was built (no fallback needed)
            assert mfc.call_count == 1

    def test_falls_back_on_failure(self, db_session):
        with patch("app.services.provider_router.ModelProviderFactory.create") as mfc:
            # groq fails, gemini succeeds
            def factory(provider, model):
                if provider == "groq":
                    return _stub_provider("groq", should_fail=True)
                return _stub_provider(provider, should_fail=False, answer=f"from {provider}")

            mfc.side_effect = factory
            router = ProviderRouter(db_session)
            answer, usage = router.ask(
                preferred="groq", model="llama-3.1-8b-instant", prompt="hi",
            )
            assert answer == "from gemini"
            assert usage["provider"] == "gemini"
            assert mfc.call_count == 2

    def test_all_providers_fail_raises_last_error(self, db_session):
        with patch("app.services.provider_router.ModelProviderFactory.create") as mfc:
            mfc.side_effect = lambda p, m: _stub_provider(p, should_fail=True)
            router = ProviderRouter(db_session)
            with pytest.raises(Exception) as exc:
                router.ask(preferred="groq", model="x", prompt="hi")
            assert "blew up" in str(exc.value)


class TestQuotaSkipping:
    def test_exhausted_provider_is_skipped(self, db_session, monkeypatch):
        # Mark groq as exhausted by filling its quota
        monkeypatch.setenv("QUOTA_GROQ_DAILY", "0")
        qt = QuotaTracker(db_session)
        # quota=0 means it's exhausted as soon as we check
        assert qt.is_exhausted("groq") is True

        with patch("app.services.provider_router.ModelProviderFactory.create") as mfc:
            mfc.side_effect = lambda p, m: _stub_provider(p, should_fail=False, answer=f"from {p}")
            router = ProviderRouter(db_session)
            answer, usage = router.ask(preferred="groq", model="x", prompt="hi")
            # Should skip groq and use the next available (gemini)
            assert usage["provider"] == "gemini"

    def test_all_exhausted_raises_quota_exceeded(self, db_session, monkeypatch):
        # Set every provider's quota to 0
        for prov in ["groq", "gemini", "minimax", "ollama"]:
            monkeypatch.setenv(f"QUOTA_{prov.upper()}_DAILY", "0")

        router = ProviderRouter(db_session)
        with pytest.raises(QuotaExceeded) as exc:
            router.ask(preferred="groq", model="x", prompt="hi")
        assert exc.value.status["exhausted"] is True


class TestCircuitBreaker:
    def test_circuit_opens_after_threshold(self, db_session):
        with patch("app.services.provider_router.ModelProviderFactory.create") as mfc:
            # All providers always fail
            mfc.side_effect = lambda p, m: _stub_provider(p, should_fail=True)
            router = ProviderRouter(db_session)

            # After FAILURE_THRESHOLD failures, groq's circuit should open
            for _ in range(FAILURE_THRESHOLD):
                try:
                    router.ask(preferred="groq", model="x", prompt="hi")
                except Exception:
                    pass

            assert router._is_open("groq") is True
            # And we should skip it
            assert "groq" not in [
                p for p in router.chain_status()["providers"] if not p["circuit_open"]
            ]

    def test_circuit_breaker_does_not_block_success(self, db_session):
        with patch("app.services.provider_router.ModelProviderFactory.create") as mfc:
            mfc.side_effect = lambda p, m: _stub_provider(p, should_fail=False)
            router = ProviderRouter(db_session)
            # Repeated successes should keep the circuit closed
            for _ in range(FAILURE_THRESHOLD * 2):
                router.ask(preferred="groq", model="x", prompt="hi")
            assert router._is_open("groq") is False


class TestUsageLogging:
    def test_records_successful_request(self, db_session):
        from app.models import UsageLog
        with patch("app.services.provider_router.ModelProviderFactory.create") as mfc:
            mfc.side_effect = lambda p, m: _stub_provider(p, should_fail=False)
            router = ProviderRouter(db_session)
            router.ask(preferred="groq", model="x", prompt="hi")
            rows = db_session.query(UsageLog).all()
            assert len(rows) == 1
            assert rows[0].provider == "groq"
            assert rows[0].success is True

    def test_records_failed_request_with_fallback_marker(self, db_session):
        from app.models import UsageLog
        with patch("app.services.provider_router.ModelProviderFactory.create") as mfc:
            def factory(p, m):
                if p == "groq":
                    return _stub_provider("groq", should_fail=True)
                return _stub_provider(p, should_fail=False)
            mfc.side_effect = factory
            router = ProviderRouter(db_session)
            router.ask(preferred="groq", model="x", prompt="hi")
            rows = db_session.query(UsageLog).all()
            # 1 row for the groq failure, 1 row for the gemini success
            assert len(rows) == 2
            assert any(r.provider == "groq" and r.success is False for r in rows)
            assert any(r.provider == "gemini" and r.success is True for r in rows)
