"""Question classifiers - LLM-based with keyword fallback.

The classifier is category-agnostic: it accepts the set of valid categories
dynamically (from currently-registered agents) and uses them in the prompt.

Returns a `ClassificationResult` with the chosen categories AND a transparent
breakdown of how the decision was made (LLM, keyword, fallback, etc.) so the
chat UI can show *why* a request landed on a given agent. That visibility is
what made us realise the previous version was silently routing to "general"
when the LLM guessed wrong.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json
import time
from typing import Optional

from app.services.llm_providers import AgentLLM


def _log_event(event: str, **fields) -> None:
    """Single-line JSON log for classification events. Same shape as master_agent."""
    payload = {"ts": round(time.time(), 3), "event": event, **fields}
    try:
        print("[routing] " + json.dumps(payload, ensure_ascii=False, default=str))
    except Exception:
        pass


CATEGORY_DESCRIPTIONS = {
    "suporte_api": "HTTP errors, authentication, JWT, gateway, runbooks, API endpoints",
    "database": "postgres, mysql, redis, database issues, queries, slow queries",
    "devops": "deploy, rollback, CI/CD, infrastructure, kubernetes, monitoring, alerts",
    "general": "anything else, broad technical questions, fallback",
    "rag": "RAG, retrieval-augmented generation, embeddings, vector stores, chunking, "
            "retrieval, LLM orchestration, prompts, AI/ML engineering",
    "clarifying": "ambiguous question, need clarification",
}


def build_classify_prompt(valid_categories: set[str], question: str) -> str:
    """Build the prompt sent to the LLM classifier.

    Asks for a JSON object with `category` + `confidence`. We extract that JSON
    on the response side; if the LLM can't produce one we degrade gracefully.
    """
    cats = sorted(valid_categories)
    lines = [
        "You classify a support question into ONE category.",
        "",
        "Valid categories (respond with EXACTLY one of these strings):",
    ]
    for c in cats:
        desc = CATEGORY_DESCRIPTIONS.get(c, c.replace("_", " "))
        lines.append(f"- {c}: {desc}")

    lines += [
        "",
        "Confidence guidelines:",
        "- 0.9-1.0: very clear match (e.g. question mentions terms from that area)",
        "- 0.6-0.8: likely match but ambiguous",
        "- 0.3-0.5: weak match",
        "- 0.0-0.2: do not pick this category",
        "",
        "If unsure, pick 'general' AND give confidence <= 0.4.",
        "",
        "Respond ONLY with JSON, no prose, no markdown:",
        '{"category": "<one of the categories above>", "confidence": <0.0-1.0>}',
        "",
        "Examples:",
        'Q: "Como faço rollback do último deploy?" -> {"category": "devops", "confidence": 0.95}',
        'Q: "Postgres está lento, o que faço?" -> {"category": "database", "confidence": 0.92}',
        'Q: "O que é RAG?" -> {"category": "rag", "confidence": 0.97}',
        'Q: "Como funciona o retrieval de embeddings?" -> {"category": "rag", "confidence": 0.93}',
        'Q: "Help" -> {"category": "general", "confidence": 0.2}',
        "",
        f"Question: {question}",
        "",
        "JSON:",
    ]
    return "\n".join(lines)


# Confidence below this triggers a keyword fallback to override the LLM choice.
LOW_CONFIDENCE_THRESHOLD = 0.6


@dataclass
class ClassificationResult:
    """Transparent record of how a question was routed to a category.

    Surfaced to the frontend via `AskResponse.thinking` so users can see
    why a request landed where it did. This is the visibility layer that
    made the silent 'general' fallback obvious in the first place.
    """
    chosen: list[str] = field(default_factory=list)
    via: str = "default"  # "llm" | "keyword" | "llm_override_keyword" | "default" | "clarifying"
    llm_category: Optional[str] = None
    llm_confidence: Optional[float] = None
    llm_raw: str = ""  # raw LLM response (helps debugging prompt issues)
    keyword_matches: list[str] = field(default_factory=list)
    fallback_used: bool = False
    reasoning: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# Backwards-compat: keeps the old name alive for any caller still using the
# raw `classify_by_keywords` shortcut. Kept at module level so external imports
# keep working without changes.
def classify_by_keywords(question: str, valid_categories: Optional[set[str]] = None) -> list[str]:
    """Return the list of categories whose keyword map matches the question."""
    classifier = KeywordClassifier()
    return classifier.classify(question, valid_categories=valid_categories)


def _parse_llm_json(response: str) -> tuple[Optional[str], Optional[float]]:
    """Extract {category, confidence} from an LLM response.

    Tolerant: accepts raw JSON, JSON wrapped in markdown fences, JSON
    surrounded by prose, and case-insensitive keys. Returns (None, None)
    when nothing usable is found so the caller can fall back.
    """
    import json
    import re

    text = (response or "").strip()
    # Strip code fences (```json ... ``` and ``` ... ```)
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    # Try the whole string first
    candidates = [text]
    # Then try to find a JSON object inside prose
    m = re.search(r"\{[^{}]*\}", text, flags=re.DOTALL)
    if m:
        candidates.append(m.group(0))

    for cand in candidates:
        cand = cand.strip()
        if not cand:
            continue
        try:
            obj = json.loads(cand)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        cat = obj.get("category") or obj.get("Category") or obj.get("CATEGORY")
        conf = obj.get("confidence") or obj.get("Confidence") or obj.get("CONFIDENCE")
        try:
            conf_val = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf_val = None
        if conf_val is not None:
            conf_val = max(0.0, min(1.0, conf_val))
        if isinstance(cat, str):
            cat = cat.strip()
        return (cat if cat else None, conf_val)

    return (None, None)


class LLMClassifier:
    def __init__(self, provider: str = "minimax", model_name: str = "MiniMax-M2.7", router_callable=None):
        self.provider = provider
        self.model_name = model_name
        self._router_callable = router_callable
        self._llm = None

    def _get_llm(self) -> AgentLLM:
        if self._llm is None:
            self._llm = AgentLLM(
                provider=self.provider,
                model_name=self.model_name,
                temperature=0.1,
                max_tokens=80,
                router_callable=self._router_callable,
            )
        return self._llm

    def classify(self, question: str, valid_categories: Optional[set[str]] = None) -> ClassificationResult:
        valid = valid_categories or {"suporte_api", "database", "devops", "general", "clarifying"}
        valid = set(valid) | {"general", "clarifying"}

        # Always run keyword matching first so we have a baseline even when
        # the LLM misbehaves.
        keyword_matches = KeywordClassifier().classify(question, valid_categories=valid)

        llm_cat: Optional[str] = None
        llm_conf: Optional[float] = None
        llm_raw: str = ""
        llm_error: Optional[str] = None

        try:
            llm = self._get_llm()
            prompt = build_classify_prompt(valid, question)
            llm_raw = llm.generate(user_prompt=prompt)
            llm_cat, llm_conf = _parse_llm_json(llm_raw)
        except Exception as e:
            llm_error = str(e)

        # Decision tree ---------------------------------------------------------
        chosen: list[str]
        via: str
        fallback_used = False
        reasoning: str

        # 1. The LLM produced something usable
        if llm_cat and llm_cat in valid and llm_conf is not None:
            # Low-confidence LLM answer: prefer keyword if keyword found something
            # more specific than 'general'. This is the override that fixes the
            # 'Hyde went to Generalist' case from the bug report.
            if llm_conf < LOW_CONFIDENCE_THRESHOLD and keyword_matches and keyword_matches != ["general"]:
                chosen = keyword_matches
                via = "llm_override_keyword"
                fallback_used = True
                reasoning = (
                    f"LLM picked '{llm_cat}' but confidence {llm_conf:.2f} "
                    f"was below {LOW_CONFIDENCE_THRESHOLD}; keyword matched "
                    f"{keyword_matches} and won."
                )
            elif llm_cat == "general" and keyword_matches and keyword_matches != ["general"]:
                # LLM gave up to 'general' but keyword has a real hit
                chosen = keyword_matches
                via = "llm_override_keyword"
                fallback_used = True
                reasoning = (
                    f"LLM said 'general' but keyword matched {keyword_matches}; "
                    f"preferring keyword to avoid silent fall-through."
                )
            else:
                chosen = [llm_cat]
                via = "llm"
                reasoning = f"LLM picked '{llm_cat}' with confidence {llm_conf:.2f}."

        # 2. The LLM response was malformed / empty / errored
        else:
            if keyword_matches and keyword_matches != ["general"]:
                chosen = keyword_matches
                via = "keyword"
                fallback_used = True
                if llm_error:
                    reasoning = f"LLM errored ({llm_error}); falling back to keyword match {keyword_matches}."
                else:
                    reasoning = (
                        f"LLM response unusable (raw: {llm_raw[:60]!r}); "
                        f"falling back to keyword match {keyword_matches}."
                    )
            else:
                chosen = ["general"]
                via = "default"
                fallback_used = True
                if llm_error:
                    reasoning = f"LLM errored ({llm_error}); no keyword hit; defaulting to general."
                else:
                    reasoning = (
                        f"LLM response unusable (raw: {llm_raw[:60]!r}); "
                        f"no keyword hit; defaulting to general."
                    )

        result = ClassificationResult(
            chosen=chosen,
            via=via,
            llm_category=llm_cat if llm_cat in valid else llm_cat,
            llm_confidence=llm_conf,
            llm_raw=llm_raw[:300] if llm_raw else "",
            keyword_matches=keyword_matches,
            fallback_used=fallback_used,
            reasoning=reasoning,
        )
        _log_event(
            "classify",
            question=question[:120],
            llm_category=result.llm_category,
            llm_confidence=result.llm_confidence,
            keyword_matches=result.keyword_matches,
            via=result.via,
            chosen=result.chosen,
            reasoning=result.reasoning,
        )
        return result


class KeywordClassifier:
    """Pure keyword-based fallback. Independent of LLM availability."""

    KEYWORD_MAP = {
        "suporte_api": [
            "401", "403", "500", "error", "gateway", "auth", "token",
            "authentication", "permission", "access", "jwt", "oauth",
            "runbook", "endpoint", "api", "http", "unauthorized", "forbidden"
        ],
        "database": [
            "postgres", "mysql", "redis", "database", "connection", "query",
            "slow", "timeout", "unavailable", "cache",
            "postgresql", "select", "insert", "update", "delete"
        ],
        "devops": [
            "deploy", "rollback", "release", "pipeline", "ci/cd",
            "kubernetes", "docker", "infrastructure", "monitoring",
            "alert", "smoke test", "build", "version"
        ],
        "rag": [
            "rag", "retrieval", "retrieval-augmented", "embedding", "vector",
            "vector store", "faiss", "chroma", "qdrant", "chunking", "chunk",
            "semantic search", "llm", "prompt", "hyde", "reranking", "rerank",
            "agent", "multi-agent", "langchain", "llamaindex", "openai",
            "anthropic", "claude", "gpt", "minimax", "transformer",
            "fine-tuning", "fine tuning", "in-context", "few-shot",
        ],
    }

    def classify(self, question: str, valid_categories: Optional[set[str]] = None) -> list[str]:
        valid = valid_categories or set(self.KEYWORD_MAP.keys()) | {"general", "clarifying"}
        question_lower = question.lower()
        matched: list[str] = []

        for category, keywords in self.KEYWORD_MAP.items():
            if category not in valid:
                continue
            if any(kw in question_lower for kw in keywords):
                matched.append(category)

        return matched if matched else ["general"]
