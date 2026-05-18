from app.services.llm_providers import AgentLLM

CLASSIFY_PROMPT = """Analyze the question and identify ALL relevant knowledge areas.

Available areas:
- suporte_api: HTTP errors (401, 403, 500), authentication, JWT, gateway, runbooks
- database: postgres, mysql, redis, database, connections, queries, cache
- devops: deploy, rollback, CI/CD, monitoring, infrastructure, release

Rules:
- A question can belong to MULTIPLE areas
- If no area is clearly relevant, return "general"
- If the question is too ambiguous or confusing, return "clarifying"
- Respond ONLY with the list of categories separated by commas, no explanations

Question: {question}

Categories (separated by commas):"""

CLASSIFY_TIMEOUT = 30


class LLMClassifier:
    def __init__(self, provider: str = "ollama", model_name: str = "llama3.2:3b"):
        self.provider = provider
        self.model_name = model_name
        self._llm = None

    def _get_llm(self) -> AgentLLM:
        if self._llm is None:
            self._llm = AgentLLM(
                provider=self.provider,
                model_name=self.model_name,
                temperature=0.1,
                max_tokens=30
            )
        return self._llm

    def classify(self, question: str) -> list[str]:
        try:
            llm = self._get_llm()
            response = llm.generate(
                user_prompt=CLASSIFY_PROMPT.format(question=question)
            )
            text = response.strip().lower()

            valid = {"suporte_api", "database", "devops", "general", "clarifying"}
            categories = [c.strip() for c in text.split(",") if c.strip() in valid]

            if not categories:
                return ["general"]

            return categories

        except Exception as e:
            print(f"LLMClassifier error: {e}")
            return classify_by_keywords(question)


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
        ]
    }

    def classify(self, question: str) -> list[str]:
        question_lower = question.lower()
        matched = []

        for category, keywords in self.KEYWORD_MAP.items():
            if any(kw in question_lower for kw in keywords):
                matched.append(category)

        return matched if matched else ["general"]


def classify_by_keywords(question: str) -> list[str]:
    classifier = KeywordClassifier()
    return classifier.classify(question)