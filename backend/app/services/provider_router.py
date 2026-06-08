"""Provider router — fallback chain + circuit breaker.

The router sits between the caller (e.g. master_agent) and the
LLMProvider implementations. It tries the requested provider first; on
failure (rate limit, network, 5xx) it walks a configured fallback chain
and counts every attempt in the QuotaTracker.

Circuit breaker: if a provider returns >= 5 failures within 60 seconds
the router stops trying it for 5 minutes. This prevents a doomed
provider (e.g. expired key) from making every request slow before the
fallback kicks in.

Quota guard: before each attempt, asks QuotaTracker if the provider is
exhausted. If yes, skip it. This is what protects the free tier.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.services.llm_providers import (
    GeminiProvider,
    GroqProvider,
    LLMProvider,
    MiniMaxProvider,
    ModelProviderFactory,
    OllamaProvider,
)
from app.services.quota_tracker import QuotaTracker, QuotaExceeded


# Provider priority: cheapest + fastest first, local as the safety net.
# Override with FALLBACK_CHAIN env var (comma-separated provider names).
DEFAULT_CHAIN: list[str] = ["groq", "gemini", "minimax", "ollama"]


def _fallback_chain() -> list[str]:
    raw = os.getenv("FALLBACK_CHAIN")
    if raw:
        return [p.strip() for p in raw.split(",") if p.strip()]
    return list(DEFAULT_CHAIN)


# Circuit breaker thresholds
FAILURE_THRESHOLD = 5        # failures inside the window
FAILURE_WINDOW_S = 60        # rolling window in seconds
COOLDOWN_S = 5 * 60          # 5 minutes open


class CircuitOpen(Exception):
    """Raised internally when a provider's circuit is open and we skip it."""

    def __init__(self, provider: str, until_ts: float):
        self.provider = provider
        self.until_ts = until_ts
        super().__init__(f"Circuit open for '{provider}' until {until_ts}")


class ProviderRouter:
    """Tries providers in fallback order, returns first success.

    Usage:
        router = ProviderRouter(db)
        answer, usage = router.ask(
            preferred="groq",
            model="llama-3.1-8b-instant",
            prompt="...",
            temperature=0.3,
        )
    """

    def __init__(self, db: Session):
        self.db = db
        self.quota = QuotaTracker(db)
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._open_until: dict[str, float] = {}

    # ---- circuit breaker ----

    def _record_failure(self, provider: str) -> None:
        now = time.time()
        dq = self._failures[provider]
        dq.append(now)
        # drop entries outside the window
        cutoff = now - FAILURE_WINDOW_S
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= FAILURE_THRESHOLD:
            self._open_until[provider] = now + COOLDOWN_S
            print(f"[router] circuit OPEN for '{provider}' for {COOLDOWN_S}s after {len(dq)} failures")

    def _record_success(self, provider: str) -> None:
        # clear failures on success so the breaker resets
        self._failures.pop(provider, None)
        self._open_until.pop(provider, None)

    def _is_open(self, provider: str) -> bool:
        until = self._open_until.get(provider)
        if until is None:
            return False
        if time.time() >= until:
            # cooldown expired, close the circuit
            self._open_until.pop(provider, None)
            self._failures.pop(provider, None)
            return False
        return True

    def _circuit_remaining(self, provider: str) -> int:
        until = self._open_until.get(provider)
        if not until:
            return 0
        return max(0, int(until - time.time()))

    # ---- provider construction ----

    @staticmethod
    def _build(provider: str, model: str) -> LLMProvider:
        return ModelProviderFactory.create(provider, model)

    # ---- public API ----

    def ask(
        self,
        preferred: str,
        model: str,
        prompt: str,
        **gen_kwargs,
    ) -> Tuple[str, dict]:
        """Try `preferred` first, then walk the fallback chain.

        Returns (answer, usage_dict) on success.
        Raises QuotaExceeded if every provider is exhausted.
        Raises the last underlying error if every provider fails for
        non-quota reasons (network, bad key, etc).
        """
        chain = _fallback_chain()
        # Reorder so the requested provider is tried first
        if preferred in chain:
            chain = [preferred] + [p for p in chain if p != preferred]
        elif preferred:
            chain = [preferred] + chain

        last_error: Optional[Exception] = None
        fallback_origin: Optional[str] = None

        for idx, provider in enumerate(chain):
            # Skip providers whose quota is exhausted
            if self.quota.is_exhausted(provider):
                print(f"[router] skip '{provider}' — quota exhausted")
                continue

            # Skip providers whose circuit is open
            if self._is_open(provider):
                rem = self._circuit_remaining(provider)
                print(f"[router] skip '{provider}' — circuit open ({rem}s remaining)")
                continue

            # Second-and-later attempts are fallbacks — record the
            # provider we *would have preferred* in fallback_from.
            if idx > 0 and fallback_origin is None:
                fallback_origin = preferred

            try:
                llm = self._build(provider, model)
                answer, usage = llm.generate_with_usage(prompt=prompt, **gen_kwargs)
            except Exception as exc:  # network, 4xx, 5xx, value error
                last_error = exc
                self._record_failure(provider)
                self.quota.record(
                    provider=provider,
                    model=model,
                    fallback_from=fallback_origin,
                    success=False,
                    error=str(exc)[:500],
                )
                self.db.commit()
                print(f"[router] '{provider}' failed: {exc.__class__.__name__}: {str(exc)[:120]}")
                continue

            # success
            self._record_success(provider)
            self.quota.record(
                provider=provider,
                model=model,
                prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                completion_tokens=int(usage.get("completion_tokens", 0) or 0),
                success=True,
                fallback_from=fallback_origin,
            )
            self.db.commit()
            return answer, usage

        # ---- exhausted every provider ----
        # Differentiate "quota exhausted" from "all failed for other reasons"
        all_exhausted = all(self.quota.is_exhausted(p) for p in chain)
        if all_exhausted:
            # pick the first provider as the canonical "you hit your limit"
            first = chain[0] if chain else preferred
            raise QuotaExceeded(first, self.quota.status(first))

        # all failed for non-quota reasons
        assert last_error is not None
        raise last_error

    # ---- visibility ----

    def chain_status(self) -> dict:
        """Snapshot for /api/usage: which providers are usable right now?"""
        chain = _fallback_chain()
        out = []
        for p in chain:
            s = self.quota.status(p)
            s["circuit_open"] = self._is_open(p)
            if s["circuit_open"]:
                s["circuit_open_for_s"] = self._circuit_remaining(p)
            out.append(s)
        return {
            "chain": [s["provider"] for s in out],
            "providers": out,
        }
