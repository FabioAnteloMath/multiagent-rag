"""Dynamic RAG agent - one instance per DB record.

Same interface as APISupportAgent / DatabaseAgent etc., but the entire config
(name, prompt, collection, model, temperature) is loaded from the Agent DB
record. Replaces the hardcoded agent classes at runtime.
"""
from __future__ import annotations
from typing import Optional

from app.agents.base_agent import BaseAgent, AgentResult
from app.models import Agent as AgentModel


class DynamicAgent(BaseAgent):
    """Agent instance backed by an Agent DB row."""

    def __init__(self, agent_row: AgentModel, collection_name: str, router_callable=None):
        self._row = agent_row
        category = (agent_row.specialty or agent_row.name or "agent").strip().lower()
        category = category.replace(" ", "_")
        super().__init__(
            name=agent_row.name or "Agent",
            category=category,
            collection_name=collection_name,
            provider=agent_row.provider or "minimax",
            model_name=agent_row.model_name or "MiniMax-M2.7",
            temperature=agent_row.temperature if agent_row.temperature is not None else 0.3,
            system_prompt=agent_row.system_prompt or "",
            guidelines=agent_row.guidelines or "",
            personality=agent_row.personality or "",
            response_format=agent_row.response_format or "",
            examples=agent_row.examples or "",
            router_callable=router_callable,
            is_fallback=bool(agent_row.is_fallback) if hasattr(agent_row, "is_fallback") else False,
        )

    @property
    def row(self) -> AgentModel:
        return self._row

    def execute(self, question: str) -> AgentResult:
        docs = self.search(question, top_k=4)

        if not docs:
            return AgentResult(
                answer=(
                    f"I did not find relevant information in the {self.collection_name} "
                    f"knowledge base. Try rephrasing your question or add more documents "
                    f"to this collection."
                ),
                sources=[],
                confidence=0.0,
                agent_name=self.name,
                category=self.category,
                thinking=f"No documents found in {self.collection_name} collection.",
            )

        context = self.format_context(docs)
        prompt = self.get_system_prompt(question, context)

        try:
            llm = self._get_llm()
            answer, usage = llm.generate_with_usage(user_prompt=prompt)
            tokens_used = usage.get("total_tokens", 0)
            model_used = usage.get("model", self.model_name)
            confidence = 0.8
        except Exception as e:
            return AgentResult(
                answer=f"Error processing response: {str(e)}",
                sources=[],
                confidence=0.0,
                agent_name=self.name,
                category=self.category,
                tokens_used=0,
                model_used=self.model_name,
                thinking=f"Error: {str(e)}",
            )

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
            thinking=f"Searching {self.collection_name} collection for: {question[:50]}...",
            model_used=model_used,
        )
