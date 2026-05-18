from app.agents.base_agent import BaseAgent, AgentResult


class DevOpsAgent(BaseAgent):
    def __init__(
        self,
        provider: str = "ollama",
        model_name: str = "llama3.2:3b",
        temperature: float = 0.3,
        system_prompt: str = ""
    ):
        super().__init__(
            name="DevOps Agent",
            category="devops",
            collection_name="DevOps",
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt or "You are an expert in DevOps, CI/CD, and infrastructure."
        )

    def execute(self, question: str) -> AgentResult:
        docs = self.search(question, top_k=4)

        if not docs:
            return AgentResult(
                answer="I did not find relevant information about DevOps in the knowledge base.",
                sources=[],
                confidence=0.0,
                agent_name=self.name,
                category=self.category,
                thinking="No documents found in DevOps collection."
            )

        context = self.format_context(docs)
        prompt = self.get_system_prompt(question, context)

        try:
            llm = self._get_llm()
            thinking = f"Searching DevOps collection for: {question[:50]}..."
            answer, usage = llm.generate_with_usage(user_prompt=prompt)
            tokens_used = usage.get("total_tokens", 0)
            model_used = usage.get("model", self.model_name)
            confidence = 0.9
        except Exception as e:
            answer = f"Error processing response: {str(e)}"
            confidence = 0.0
            tokens_used = 0
            model_used = self.model_name
            thinking = f"Error: {str(e)}"

        sources = []
        for doc in docs:
            source = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page")
            if page is not None:
                sources.append(f"{source}#page={int(page) + 1}")
            else:
                sources.append(source)

        return AgentResult(
            answer=answer,
            sources=sources,
            confidence=confidence,
            agent_name=self.name,
            category=self.category,
            tokens_used=tokens_used,
            thinking=thinking,
            model_used=model_used
        )