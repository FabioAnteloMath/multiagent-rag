"""Master orchestrator that routes questions to specialized agents.

The agent roster is built externally (chat_routes loads DynamicAgent instances
from the DB) and passed in. MasterAgent no longer instantiates hardcoded
classes at startup - it works with whatever BaseAgent instances it receives.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Iterable
import json
import time

from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.classifiers import (
    LLMClassifier,
    ClassificationResult,
    classify_by_keywords,
)


def _log_event(event: str, **fields: Any) -> None:
    """Emit a single-line JSON log for routing decisions.

    Filter with:  tail -f backend-out.log | grep '"event"'
    """
    payload = {"ts": round(time.time(), 3), "event": event, **fields}
    try:
        print("[routing] " + json.dumps(payload, ensure_ascii=False, default=str))
    except Exception:
        # Never let logging break the request path.
        pass


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
    routing: Optional[Dict[str, Any]] = None  # ClassificationResult.to_dict()


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
        # Last classification result, kept for the response payload.
        # Reset at the start of every ask() / single_rag_ask() call.
        self.last_routing: Optional[ClassificationResult] = None

    def register_agent(self, agent: BaseAgent) -> None:
        self.agents[agent.category] = agent

    def valid_categories(self) -> set[str]:
        return set(self.agents.keys())

    def classify(self, question: str) -> list[str]:
        """Classify the question and store the full ClassificationResult.

        Returns just the chosen category list for backwards compatibility
        with callers that only need the decision. The richer result is on
        `self.last_routing` and gets attached to the AskResponse.
        """
        valid = self.valid_categories() | {"general", "clarifying"}
        if self.use_llm_classify:
            try:
                result = self.classifier.classify(question, valid_categories=valid)
            except Exception as e:
                print(f"LLM classify failed: {e}, using keyword fallback")
                keyword_matches = classify_by_keywords(question, valid_categories=valid)
                result = ClassificationResult(
                    chosen=keyword_matches,
                    via="keyword",
                    keyword_matches=keyword_matches,
                    fallback_used=True,
                    reasoning=f"LLM classifier threw {e!r}; keyword fallback used.",
                )
        else:
            keyword_matches = classify_by_keywords(question, valid_categories=valid)
            result = ClassificationResult(
                chosen=keyword_matches,
                via="keyword",
                keyword_matches=keyword_matches,
                reasoning="LLM classifier disabled (use_llm_classify=False).",
            )
        self.last_routing = result
        return result.chosen

    def needs_clarifying(self, categories: list[str]) -> bool:
        if not categories:
            return True
        if "clarifying" in categories:
            return True
        return False

    def _routing_dict(self) -> Optional[Dict[str, Any]]:
        """Snapshot the last routing decision as a plain dict for the API."""
        return self.last_routing.to_dict() if self.last_routing else None

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

    # ------------------------------------------------------------------
    # Specialist vs fallback separation
    # ------------------------------------------------------------------
    # An agent is a "specialist" if it has a focused collection to answer
    # domain questions. A "fallback" agent is only consulted when no
    # specialist matched. `is_fallback` is the explicit DB flag; agents
    # without a collection are implicitly fallbacks. This split is what
    # fixes the bug where the Generalist (with a generic glossary) was
    # answering RAG-specific questions just because the classifier said
    # "general".
    # ------------------------------------------------------------------

    def _specialists(self) -> Dict[str, BaseAgent]:
        return {
            cat: agent
            for cat, agent in self.agents.items()
            if not self._is_fallback_agent(agent)
        }

    def _fallbacks(self) -> Dict[str, BaseAgent]:
        return {
            cat: agent
            for cat, agent in self.agents.items()
            if self._is_fallback_agent(agent)
        }

    @staticmethod
    def _is_fallback_agent(agent: BaseAgent) -> bool:
        # Explicit flag wins. Agents without a collection are treated as
        # fallbacks too: a specialist that has nothing to search is useless
        # in the delegation path.
        if getattr(agent, "is_fallback", False):
            return True
        if not getattr(agent, "collection_name", None):
            return True
        return False

    def _discover_specialist(self, question: str, specialists: Dict[str, BaseAgent]) -> Optional[BaseAgent]:
        """Find the specialist most likely to answer this question.

        When the classifier can't decide (returns only fallbacks / generic),
        we run a cheap retrieval-only probe across every specialist: fetch
        the top-1 chunk from each one's collection and pick the one with the
        shortest FAISS distance to the query (highest similarity).

        This is the second routing layer that fixes silent fall-through to
        the Generalist: even if the LLM classifier said "general", if the
        RAG collection has Hyde and the Generalist's glossary doesn't, RAG
        wins.

        Returns the chosen specialist or None if none had any context.
        """
        if not specialists:
            return None

        def probe(agent: BaseAgent):
            try:
                # Lazy-load the FAISS index exactly like search() does
                if agent._vectorstore is None:
                    agent._vectorstore = agent._load_vectorstore()
                if agent._vectorstore is None:
                    return (agent.category, None, "no_index")
                # similarity_search_with_score returns [(doc, distance)].
                # FAISS distance: lower = more relevant.
                if hasattr(agent._vectorstore, "similarity_search_with_score"):
                    scored = agent._vectorstore.similarity_search_with_score(question, k=1)
                    if scored:
                        return (agent.category, float(scored[0][1]), None)
                    return (agent.category, None, "no_docs")
                # No scoring API: fall back to plain similarity_search and
                # treat any hit as a tie (sort by doc count below).
                docs = agent._vectorstore.similarity_search(question, k=1)
                if docs:
                    # Use a large distance so any scored specialist beats us.
                    return (agent.category, float("inf"), None)
                return (agent.category, None, "no_docs")
            except Exception as e:
                return (agent.category, None, str(e))

        with ThreadPoolExecutor(max_workers=min(4, len(specialists))) as executor:
            futures = {executor.submit(probe, a): a for a in specialists.values()}
            results = []
            raw: list[tuple[str, Optional[float], Optional[str]]] = []
            for fut in futures:
                cat, score, err = fut.result()
                raw.append((cat, score, err))
                if err or score is None:
                    continue
                results.append((cat, score))

        if not results:
            _log_event(
                "discovery",
                probed=[c for c, _, _ in raw],
                scores={c: s for c, s, _ in raw if s is not None},
                errors={c: e for c, _, e in raw if e},
                chosen=None,
            )
            return None

        # Lower distance wins. With inf as sentinel, any real score beats us.
        results.sort(key=lambda r: r[1])
        chosen_cat = results[0][0]
        _log_event(
            "discovery",
            probed=[c for c, _, _ in raw],
            scores={c: round(s, 4) if s is not None else None for c, s, _ in raw},
            errors={c: e for c, _, e in raw if e},
            chosen=chosen_cat,
        )
        return self.agents.get(chosen_cat)

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
            routing=self._routing_dict(),
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
                    routing=self._routing_dict(),
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
                    routing=self._routing_dict(),
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
                routing=self._routing_dict(),
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
            routing=self._routing_dict(),
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

        # Surface the classification on the response for transparency
        base_routing = self._routing_dict()
        thinking = f"Classifying: {question[:50]}... | categories={categories} | via={base_routing.get('via') if base_routing else 'n/a'}"

        if self.needs_clarifying(categories) and not self._fallbacks():
            elapsed_ms = (time.time() - start_time) * 1000
            return AskResponse(
                answer=ASK_CLARIFYING,
                sources=[],
                agent_used=["master"],
                steps=["classify", "clarifying"],
                tokens_used=0,
                thinking=thinking + " | No fallback agents available",
                total_time_ms=elapsed_ms,
                confidence=0.0,
                routing=base_routing,
            )

        specialists = self._specialists()
        fallbacks = self._fallbacks()

        # Decide which agents to call. The contract is:
        #   1. If the classifier identified a specific specialist, use it.
        #   2. Otherwise, run discovery across all specialists and use the
        #      one whose collection has the most relevant chunk.
        #   3. If discovery yields nothing, fall back to fallback agents.
        #   4. If we have neither, ask for clarification.
        classified_specialists = [c for c in categories if c in specialists]

        chosen: list[str] = []
        steps: list[str] = ["classify"]
        if classified_specialists:
            chosen = classified_specialists
            steps.append("classified_specialist")
            thinking += f" | specialist from classifier: {chosen}"
        elif specialists:
            discovered = self._discover_specialist(question, specialists)
            if discovered is not None:
                chosen = [discovered.category]
                steps.append("specialist_discovery")
                thinking += f" | specialist discovered: {chosen}"
                # Annotate routing so the UI can show this layer kicked in
                if base_routing:
                    base_routing["discovered"] = True
                    base_routing["reasoning"] = (
                        base_routing.get("reasoning", "")
                        + f" | Classifier did not pick a specialist; "
                          f"discovery picked '{discovered.category}' based on retrieval."
                    ).strip(" |")
            elif fallbacks:
                chosen = list(fallbacks.keys())
                steps.append("fallback")
                thinking += f" | no specialist matched; using fallback(s): {chosen}"
            else:
                chosen = []
                steps.append("no_match")
                thinking += " | no specialist matched and no fallback configured"
        elif fallbacks:
            chosen = list(fallbacks.keys())
            steps.append("fallback_only")
            thinking += f" | only fallback agents configured: {chosen}"

        if not chosen:
            elapsed_ms = (time.time() - start_time) * 1000
            return AskResponse(
                answer=ASK_CLARIFYING,
                sources=[],
                agent_used=["master"],
                steps=steps,
                tokens_used=0,
                thinking=thinking,
                total_time_ms=elapsed_ms,
                confidence=0.0,
                routing=base_routing,
            )

        results = self.delegate_parallel(question, chosen)
        response = self.aggregate(results)
        response.thinking = thinking + " | " + (response.thinking or "")
        response.total_time_ms = (time.time() - start_time) * 1000
        response.routing = base_routing
        response.steps = steps + response.steps

        _log_event(
            "ask_done",
            question=question[:120],
            chosen=chosen,
            agents_used=response.agent_used,
            via=base_routing.get("via") if base_routing else None,
            discovered=bool(base_routing.get("discovered")) if base_routing else False,
            total_time_ms=round(response.total_time_ms, 1),
            tokens=response.tokens_used,
        )

        return response
