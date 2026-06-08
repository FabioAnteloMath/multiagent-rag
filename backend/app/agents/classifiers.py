"""Question classifiers - LLM-based with keyword fallback.

The classifier is category-agnostic: it accepts the set of valid categories
dynamically (from currently-registered agents) and uses them in the prompt.
"""
from app.services.llm_providers import AgentLLM
from typing import Optional


CATEGORY_DESCRIPTIONS = {
    "suporte_api": "HTTP errors, authentication, JWT, gateway, runbooks, API endpoints",
    "database": "postgres, mysql, redis, database issues, queries, slow queries",
    "devops": "deploy, rollback, CI/CD, infrastructure, kubernetes, monitoring, alerts",
    "general": "anything else, broad technical questions, fallback",
    "rag": "RAG, retrieval-augmented generation, embeddings, vector stores, chunking, "
            "retrieval, LLM orchestration, prompts, AI/ML engineering",
    "clarifying": "ambiguous question, need clarification",
}


def build_classify_prompt(valid_categories: set[str]) -> str:
    cats = sorted(valid_categories)
    lines = ["Classify this question into ONE of these categories:"]
    for c in cats:
        desc = CATEGORY_DESCRIPTIONS.get(c, c.replace("_", " "))
        lines.append(f"- {c}: {desc}")
    lines.append("")
    lines.append("Respond with ONLY the category name, nothing else.")
    lines.append("")
    lines.append("Question: {question}")
    lines.append("")
    lines.append("Category:")
    return "\n".join(lines)


CLASSIFY_TIMEOUT = 30


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
                max_tokens=30,
                router_callable=self._router_callable,
            )
        return self._llm

    def classify(self, question: str, valid_categories: Optional[set[str]] = None) -> list[str]:
        valid = valid_categories or {"suporte_api", "database", "devops", "general", "clarifying"}
        valid = valid | {"general", "clarifying"}
        try:
            llm = self._get_llm()
            prompt = build_classify_prompt(valid).format(question=question)
            response = llm.generate(user_prompt=prompt)

            import re
            text = re.sub(r"<[^>]+>", "", response).lower()
            text = text.strip()

            found = []
            for cat in valid:
                if cat in text:
                    found.append(cat)

            if not found:
                keyword_result = classify_by_keywords(question, valid_categories=valid)
                if keyword_result != ["general"]:
                    return keyword_result
                return ["general"]

            if found == ["general"]:
                keyword_result = classify_by_keywords(question, valid_categories=valid)
                if keyword_result != ["general"]:
                    return keyword_result

            return found

        except Exception as e:
            print(f"LLMClassifier error: {e}")
            return classify_by_keywords(question, valid_categories=valid)


class KeywordClassifier:
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
        matched = []

        for category, keywords in self.KEYWORD_MAP.items():
            if category not in valid:
                continue
            if any(kw in question_lower for kw in keywords):
                matched.append(category)

        return matched if matched else ["general"]


def classify_by_keywords(question: str, valid_categories: Optional[set[str]] = None) -> list[str]:
    classifier = KeywordClassifier()
    return classifier.classify(question, valid_categories=valid_categories)
