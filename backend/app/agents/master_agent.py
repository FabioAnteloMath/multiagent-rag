"""Master orchestrator that routes questions to specialized agents.

The agent roster is built externally (chat_routes loads DynamicAgent instances
from the DB) and passed in. MasterAgent no longer instantiates hardcoded
classes at startup - it works with whatever BaseAgent instances it receives.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Optional, Dict, Any, Iterable
import time

from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.classifiers import LLMClassifier, classify_by_keywords


ASK_CLARIFYING = """I could not clearly identify the knowledge area needed to answer your question.

Please be more specific about the problem you are facing.

Examples:
- "How to resolve 401 error on gateway?" (specific)
- "Deploy failed with timeout" (specific)
- "Postgres database is slow" (specific)

Avoid very generic questions like just "help" or "problem"."""


@dataclass
class AskResponse:
    answer: str
    sources: list[str]
    agent_used: list[str]
    steps: list[str]
    needs_clarifying: bool = False
    tokens_used: int = 0
    thinking: str = ""
    model_used: str = ""
    total_time_ms: float = 0.0
    confidence: float = 0.0
    collection_searched: str = ""


class MasterAgent:
    def __init__(
        self,
        agents: Optional[Dict[str, BaseAgent]] = None,
        classifier_provider: str = "minimax",
        classifier_model: str = "MiniMax-M2.7",
        router_callable=None,
    ):
        self.agents: Dict[str, BaseAgent] = agents or {}
        self.classifier = LLMClassifier(
            provider=classifier_provider,
            model_name=classifier_model,
            router_callable=router_callable,
        )
        self.use_llm_classify = True
        self.agent_timeout = 180

    def register_agent(self, agent: BaseAgent) -> None:
        self.agents[agent.category] = agent

    def valid_categories(self) -> set[str]:
        return set(self.agents.keys())

    def classify(self, question: str) -> list[str]:
        valid = self.valid_categories() | {"general", "clarifying"}
        if self.use_llm_classify:
            try:
                return self.classifier.classify(question, valid_categories=valid)
            except Exception as e:
                print(f"LLM classify failed: {e}, using keyword fallback")
                return classify_by_keywords(question, valid_categories=valid)
        return classify_by_keywords(question, valid_categories=valid)

    def needs_clarifying(self, categories: list[str]) -> bool:
        if not categories:
            return True
        if "clarifying" in categories:
            return True
        return False

    def delegate_parallel(self, question: str, categories: list[str]) -> dict:
        results = {}
        valid_categories = [c for c in categories if c in self.agents]
        if not valid_categories:
            if "general" in self.agents:
                valid_categories = ["general"]
            else:
                # Fall back to the first available agent
                valid_categories = [next(iter(self.agents))] if self.agents else []

        if not valid_categories:
            return results

        with ThreadPoolExecutor(max_workers=min(4, len(valid_categories))) as executor:
            futures = {
                cat: executor.submit(self.agents[cat].execute, question)
                for cat in valid_categories
            }

            for cat, future in futures.items():
                try:
                    results[cat] = future.result(timeout=self.agent_timeout)
                except FuturesTimeoutError:
                    results[cat] = AgentResult(
                        answer="Agent response timed out. Please try again.",
                        sources=[],
                        confidence=0.0,
                        agent_name=self.agents[cat].name,
                        category=cat,
                    )
                except Exception as e:
                    results[cat] = AgentResult(
                        answer=f"Agent error: {str(e)}",
                        sources=[],
                        confidence=0.0,
                        agent_name=self.agents[cat].name,
                        category=cat,
                    )

        return results

    def aggregate(self, results: dict) -> AskResponse:
        answers = []
        all_sources = []
        agents_used = []
        total_tokens = 0
        thinking_parts = []
        model_used = ""
        confidence_sum = 0
        confidence_count = 0

        no_info_phrases = [
            "did not find relevant information",
            "could not find relevant information",
            "no documents found",
            "não encontrei informações",
            "não foi possível obter resposta dos agentes",
            "timed out",
            "agent error",
            "error processing response",
            "i did not find relevant information",
        ]

        for cat, result in results.items():
            is_no_info = any(phrase.lower() in result.answer.lower() for phrase in no_info_phrases)
            if result.answer and not is_no_info:
                answers.append(result.answer)
                all_sources.extend(result.sources)
                agents_used.append(result.agent_name)
                total_tokens += result.tokens_used
                if result.thinking:
                    thinking_parts.append(f"{result.agent_name}: {result.thinking}")
                if result.model_used:
                    model_used = result.model_used
                confidence_sum += result.confidence
                confidence_count += 1

        if not answers:
            return AskResponse(
                answer="No agent found relevant information in their knowledge base. Please try rephrasing your question.",
                sources=[],
                agent_used=["MasterAgent"],
                steps=["classify", "delegate_parallel", "aggregate"],
                tokens_used=total_tokens,
                thinking="No agents returned relevant answers.",
                model_used=model_used,
            )

        avg_confidence = confidence_sum / confidence_count if confidence_count > 0 else 0
        final_answer = "\n\n---\n\n".join(answers)

        return AskResponse(
            answer=final_answer,
            sources=sorted(set(all_sources)),
            agent_used=agents_used,
            steps=["classify", "delegate_parallel", "aggregate"],
            tokens_used=total_tokens,
            thinking=" | ".join(thinking_parts) if thinking_parts else "Multiple agents responded",
            model_used=model_used,
            confidence=avg_confidence,
        )

    def single_rag_ask(self, question: str, force_agent: Optional[str] = None) -> AskResponse:
        start_time = time.time()

        if force_agent and force_agent in self.agents:
            primary_agent = self.agents[force_agent]
            thinking = f"Force agent: {force_agent}"
        else:
            thinking = f"Routing: {question[:50]}..."
            categories = self.classify(question)

            if self.needs_clarifying(categories):
                return AskResponse(
                    answer=ASK_CLARIFYING,
                    sources=[],
                    agent_used=["Router"],
                    steps=["classify", "clarifying"],
                    tokens_used=0,
                    thinking=thinking + " | Question too ambiguous",
                    total_time_ms=(time.time() - start_time) * 1000,
                    confidence=0.0,
                )

            primary = None
            for cat in categories:
                if cat in self.agents:
                    primary = cat
                    break
            if not primary:
                primary = "general" if "general" in self.agents else (next(iter(self.agents)) if self.agents else None)

            if not primary:
                return AskResponse(
                    answer="No agents are configured. Create an agent and link it to a collection before asking.",
                    sources=[],
                    agent_used=["MasterAgent"],
                    steps=["classify", "no_agents"],
                    tokens_used=0,
                    thinking="No agents available",
                    total_time_ms=(time.time() - start_time) * 1000,
                    confidence=0.0,
                )

            primary_agent = self.agents[primary]
            thinking += f" | Selected: {primary}"

        docs = primary_agent.search(question, top_k=4)

        if not docs:
            elapsed_ms = (time.time() - start_time) * 1000
            return AskResponse(
                answer=f"No relevant information found in {primary_agent.collection_name} collection. Try rephrasing or ask about a different topic.",
                sources=[],
                agent_used=[primary_agent.name],
                steps=["route", "search", "no_match"],
                tokens_used=0,
                thinking=thinking + f" | No docs found in {primary_agent.collection_name}",
                total_time_ms=elapsed_ms,
                confidence=0.0,
                collection_searched=primary_agent.collection_name,
            )

        context = primary_agent.format_context(docs)
        prompt = primary_agent.get_system_prompt(question, context)

        try:
            llm = primary_agent._get_llm()
            answer, usage = llm.generate_with_usage(user_prompt=prompt)
            tokens_used = usage.get("total_tokens", 0)
            model_used = usage.get("model", primary_agent.model_name)
            confidence = 0.9
        except Exception as e:
            answer = f"Error generating response: {str(e)}"
            confidence = 0.0
            tokens_used = 0
            model_used = primary_agent.model_name

        sources = []
        for doc in docs:
            source = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page")
            if page is not None:
                sources.append(f"{source}#page={int(page) + 1}")
            else:
                sources.append(source)

        elapsed_ms = (time.time() - start_time) * 1000

        return AskResponse(
            answer=answer,
            sources=sorted(set(sources)),
            agent_used=[primary_agent.name],
            steps=["route", "search", "generate"],
            tokens_used=tokens_used,
            thinking=thinking,
            model_used=model_used,
            total_time_ms=elapsed_ms,
            confidence=confidence,
            collection_searched=primary_agent.collection_name,
        )

    def ask(self, question: str, force_agent: Optional[str] = None) -> AskResponse:
        start_time = time.time()

        if force_agent and force_agent in self.agents:
            result = self.agents[force_agent].execute(question)
            elapsed_ms = (time.time() - start_time) * 1000
            return AskResponse(
                answer=result.answer,
                sources=result.sources,
                agent_used=[result.agent_name],
                steps=["direct", force_agent],
                tokens_used=result.tokens_used,
                thinking=result.thinking or f"Direct call to {force_agent}",
                model_used=result.model_used or "",
                total_time_ms=elapsed_ms,
                confidence=result.confidence,
            )

        categories = self.classify(question)

        if self.needs_clarifying(categories):
            elapsed_ms = (time.time() - start_time) * 1000
            return AskResponse(
                answer=ASK_CLARIFYING,
                sources=[],
                agent_used=["master"],
                steps=["classify", "clarifying"],
                tokens_used=0,
                thinking=f"Classifying: {question[:50]}... | Ambiguous categories: {categories}",
                total_time_ms=elapsed_ms,
                confidence=0.0,
            )

        valid_categories = [c for c in categories if c in self.agents]
        if not valid_categories:
            valid_categories = ["general"] if "general" in self.agents else (
                [next(iter(self.agents))] if self.agents else []
            )

        if not valid_categories:
            return AskResponse(
                answer="No agents are configured.",
                sources=[],
                agent_used=["master"],
                steps=["classify", "no_agents"],
                tokens_used=0,
                confidence=0.0,
                total_time_ms=(time.time() - start_time) * 1000,
            )

        results = self.delegate_parallel(question, valid_categories)
        response = self.aggregate(results)
        response.thinking = f"Classifying: {question[:50]}... | Categories: {categories} | " + (response.thinking or "")
        response.total_time_ms = (time.time() - start_time) * 1000

        return response
