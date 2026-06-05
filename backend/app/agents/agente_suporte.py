from app.agents.base_agent import BaseAgent, AgentResult


class APISupportAgent(BaseAgent):
    def __init__(
        self,
        provider: str = "minimax",
        model_name: str = "MiniMax-M2.7",
        temperature: float = 0.3,
        system_prompt: str = "",
        guidelines: str = "",
        personality: str = "",
        response_format: str = "",
        examples: str = ""
    ):
        super().__init__(
            name="API Support Agent",
            category="suporte_api",
            collection_name="SuporteAPI",
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            system_prompt=system_prompt or "You are an expert in API support and troubleshooting.",
            guidelines=guidelines,
            personality=personality,
            response_format=response_format,
            examples=examples
        )

    def execute(self, question: str) -> AgentResult:
        docs = self.search(question, top_k=4)

        if not docs:
            return AgentResult(
                answer="I did not find relevant information about API support in the knowledge base.",
                sources=[],
                confidence=0.0,
                agent_name=self.name,
                category=self.category,
                thinking="No documents found in SuporteAPI collection."
            )

        context = self.format_context(docs)
        prompt = self.get_system_prompt(question, context)

        try:
            llm = self._get_llm()
            thinking = f"Searching SuporteAPI collection for: {question[:50]}..."
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