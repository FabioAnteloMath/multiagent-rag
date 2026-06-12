"""
Unit tests for agent modules.

After the cleanup that removed the hardcoded APISupportAgent /
DatabaseAgent / DevOpsAgent / GeneralistAgent classes, only
`BaseAgent` (abstract) and `DynamicAgent` (DB-backed) remain. The
tests below cover both, with the same kind of mocks conftest.py
already uses (no real DB, no real LLM, no real FAISS).
"""
import pytest
from unittest.mock import Mock, patch

from app.agents.base_agent import AgentResult, BaseAgent
from app.agents.dynamic_agent import DynamicAgent


# ============================================================================
# Helpers
# ============================================================================

def _make_agent_row(**overrides) -> Mock:
    """Build a Mock that quacks like a SQLAlchemy Agent row."""
    defaults = dict(
        name="API Support Agent",
        specialty="suporte_api",
        system_prompt="You are an API support expert.",
        guidelines="Cite the error code when relevant.",
        personality="Direct and concise.",
        response_format="Markdown with code blocks.",
        examples="Q: 401?\nA: Check the JWT.",
        provider="ollama",
        model_name="llama3.2:3b",
        temperature="0.3",
    )
    defaults.update(overrides)
    row = Mock()
    for k, v in defaults.items():
        setattr(row, k, v)
    return row


# ============================================================================
# Test: AgentResult dataclass
# ============================================================================

class TestAgentResult:
    """Unit tests for the AgentResult dataclass."""

    @pytest.mark.unit
    def test_required_fields(self):
        result = AgentResult(
            answer="x", sources=["a.md"], confidence=0.9,
            agent_name="A", category="c",
        )
        assert result.answer == "x"
        assert result.sources == ["a.md"]
        assert result.confidence == 0.9
        assert result.agent_name == "A"
        assert result.category == "c"

    @pytest.mark.unit
    def test_defaults(self):
        result = AgentResult(
            answer="x", sources=[], confidence=0.0,
            agent_name="A", category="c",
        )
        assert result.tokens_used == 0
        assert result.thinking == ""
        assert result.model_used == ""

    @pytest.mark.unit
    def test_optional_fields_override(self):
        result = AgentResult(
            answer="x", sources=[], confidence=0.5,
            agent_name="A", category="c",
            tokens_used=42, thinking="t", model_used="m",
        )
        assert result.tokens_used == 42
        assert result.thinking == "t"
        assert result.model_used == "m"


# ============================================================================
# Test: BaseAgent — behavior shared by every concrete agent
# ============================================================================

class _ConcreteAgent(BaseAgent):
    """Minimal BaseAgent subclass for exercising the abstract base."""

    def execute(self, question: str) -> AgentResult:  # pragma: no cover
        return AgentResult(
            answer=question, sources=[], confidence=0.0,
            agent_name=self.name, category=self.category,
        )


class TestBaseAgent:
    """Unit tests for BaseAgent's concrete helpers."""

    @pytest.mark.unit
    def test_format_context_empty(self):
        agent = _ConcreteAgent(name="A", category="c", collection_name="C")
        assert agent.format_context([]) == "I did not find relevant context."

    @pytest.mark.unit
    def test_format_context_joins_with_double_newline(self):
        agent = _ConcreteAgent(name="A", category="c", collection_name="C")
        d1 = Mock(page_content="alpha")
        d2 = Mock(page_content="beta")
        assert agent.format_context([d1, d2]) == "alpha\n\nbeta"

    @pytest.mark.unit
    def test_format_context_ignores_metadata(self):
        agent = _ConcreteAgent(name="A", category="c", collection_name="C")
        d = Mock(page_content="body", metadata={"source": "ignored"})
        assert agent.format_context([d]) == "body"

    @pytest.mark.unit
    def test_get_system_prompt_uses_custom_system_prompt_when_set(self):
        """When a system_prompt is provided, it replaces the name/category fallback."""
        agent = _ConcreteAgent(
            name="API Agent", category="suporte_api",
            collection_name="SuporteAPI",
            system_prompt="You are helpful.",
        )
        prompt = agent.get_system_prompt("Why 401?", "JWT missing")
        assert "You are helpful." in prompt
        assert "Why 401?" in prompt
        assert "JWT missing" in prompt
        # When the agent has a custom system_prompt, the default
        # "You are <name>, a specialist in <category>." is NOT injected.
        assert "specialist" not in prompt

    @pytest.mark.unit
    def test_get_system_prompt_falls_back_when_empty(self):
        agent = _ConcreteAgent(
            name="Fallback Agent", category="general",
            collection_name="General",
        )
        prompt = agent.get_system_prompt("Q", "C")
        # The default fallback is "You are <name>, a specialist in <category>."
        assert "Fallback Agent" in prompt
        assert "specialist" in prompt
        assert "general" in prompt

    @pytest.mark.unit
    def test_get_system_prompt_includes_optional_sections(self):
        agent = _ConcreteAgent(
            name="A", category="c", collection_name="C",
            system_prompt="sys",
            guidelines="g line",
            personality="p line",
            response_format="f line",
            examples="e line",
        )
        prompt = agent.get_system_prompt("Q", "C")
        assert "Guidelines:\ng line" in prompt
        assert "Personality: p line" in prompt
        assert "Response Format: f line" in prompt
        assert "Examples:\ne line" in prompt

    @pytest.mark.unit
    def test_search_returns_empty_when_vectorstore_is_none(self):
        agent = _ConcreteAgent(name="A", category="c", collection_name="C")
        agent._vectorstore = None
        with patch.object(agent, "_load_vectorstore", return_value=None):
            assert agent.search("q") == []

    @pytest.mark.unit
    def test_search_uses_default_top_k(self):
        agent = _ConcreteAgent(name="A", category="c", collection_name="C")
        store = Mock()
        store.similarity_search.return_value = []
        agent._vectorstore = store
        agent.search("q")
        store.similarity_search.assert_called_once_with("q", k=4)

    @pytest.mark.unit
    def test_search_respects_custom_top_k(self):
        agent = _ConcreteAgent(name="A", category="c", collection_name="C")
        store = Mock()
        store.similarity_search.return_value = []
        agent._vectorstore = store
        agent.search("q", top_k=7)
        store.similarity_search.assert_called_once_with("q", k=7)

    @pytest.mark.unit
    def test_refresh_vectorstore_clears_cache(self):
        agent = _ConcreteAgent(name="A", category="c", collection_name="C")
        agent._vectorstore = Mock()
        with patch.object(agent, "_load_vectorstore", return_value=None):
            agent.refresh_vectorstore()
        assert agent._vectorstore is None

    @pytest.mark.unit
    def test_setters_persist_fields(self):
        agent = _ConcreteAgent(name="A", category="c", collection_name="C")
        agent.set_guidelines("new g")
        agent.set_personality("new p")
        agent.set_response_format("new f")
        agent.set_examples("new e")
        assert agent._guidelines == "new g"
        assert agent._personality == "new p"
        assert agent._response_format == "new f"
        assert agent._examples == "new e"


# ============================================================================
# Test: DynamicAgent — the only concrete agent we ship now
# ============================================================================

class TestDynamicAgentConstruction:
    """DynamicAgent should read all config from the DB row."""

    @pytest.mark.unit
    def test_uses_row_name_and_uncategorized_defaults(self):
        row = _make_agent_row()
        agent = DynamicAgent(agent_row=row, collection_name="SuporteAPI")
        assert agent.name == "API Support Agent"
        assert agent.category == "suporte_api"
        assert agent.collection_name == "SuporteAPI"
        assert agent.provider == "ollama"
        assert agent.model_name == "llama3.2:3b"
        assert agent.temperature == 0.3

    @pytest.mark.unit
    def test_falls_back_when_name_blank(self):
        row = _make_agent_row(name="", specialty="db")
        agent = DynamicAgent(agent_row=row, collection_name="Database")
        assert agent.name == "Agent"
        assert agent.category == "db"

    @pytest.mark.unit
    def test_falls_back_when_specialty_blank(self):
        row = _make_agent_row(name="My Agent", specialty="")
        agent = DynamicAgent(agent_row=row, collection_name="C")
        assert agent.category == "my_agent"  # name normalized, spaces -> _

    @pytest.mark.unit
    def test_category_normalizes_spaces_and_case(self):
        row = _make_agent_row(specialty="API Support")
        agent = DynamicAgent(agent_row=row, collection_name="C")
        assert agent.category == "api_support"

    @pytest.mark.unit
    def test_provider_and_model_defaults(self):
        row = _make_agent_row(provider="", model_name="")
        agent = DynamicAgent(agent_row=row, collection_name="C")
        assert agent.provider == "minimax"
        assert agent.model_name == "MiniMax-M2.7"

    @pytest.mark.unit
    def test_temperature_parsed_from_string(self):
        row = _make_agent_row(temperature="0.7")
        agent = DynamicAgent(agent_row=row, collection_name="C")
        assert agent.temperature == 0.7
        assert isinstance(agent.temperature, float)

    @pytest.mark.unit
    def test_temperature_default_when_blank(self):
        row = _make_agent_row(temperature="")
        agent = DynamicAgent(agent_row=row, collection_name="C")
        assert agent.temperature == 0.3

    @pytest.mark.unit
    def test_row_property_returns_original(self):
        row = _make_agent_row()
        agent = DynamicAgent(agent_row=row, collection_name="C")
        assert agent.row is row


class TestDynamicAgentExecute:
    """DynamicAgent.execute: no-docs path, success path, error path."""

    @pytest.mark.unit
    def test_execute_no_docs_returns_zero_confidence(self):
        agent = DynamicAgent(
            agent_row=_make_agent_row(), collection_name="SuporteAPI",
        )
        with patch.object(agent, "search", return_value=[]):
            result = agent.execute("anything")
        assert result.confidence == 0.0
        assert result.sources == []
        assert "SuporteAPI" in result.answer
        assert result.category == "suporte_api"
        assert result.agent_name == "API Support Agent"

    @pytest.mark.unit
    def test_execute_success_builds_page_aware_sources(self):
        agent = DynamicAgent(
            agent_row=_make_agent_row(), collection_name="SuporteAPI",
        )

        doc = Mock()
        doc.page_content = "401 means unauthorized"
        doc.metadata = {"source": "auth.md", "page": 2}

        llm = Mock()
        llm.generate_with_usage.return_value = (
            "Check the JWT token.",
            {"total_tokens": 30, "model": "llama3.2:3b"},
        )

        with patch.object(agent, "search", return_value=[doc]):
            with patch.object(agent, "_get_llm", return_value=llm):
                result = agent.execute("what about 401?")

        assert result.answer == "Check the JWT token."
        assert result.confidence == 0.8
        assert result.tokens_used == 30
        assert result.model_used == "llama3.2:3b"
        # page is 0-indexed in storage, 1-indexed in display
        assert "auth.md#page=3" in result.sources

    @pytest.mark.unit
    def test_execute_success_source_without_page(self):
        agent = DynamicAgent(
            agent_row=_make_agent_row(), collection_name="C",
        )

        doc = Mock()
        doc.page_content = "body"
        doc.metadata = {"source": "doc.md"}  # no page

        llm = Mock()
        llm.generate_with_usage.return_value = (
            "ok", {"total_tokens": 5, "model": "m"},
        )

        with patch.object(agent, "search", return_value=[doc]):
            with patch.object(agent, "_get_llm", return_value=llm):
                result = agent.execute("q")
        assert result.sources == ["doc.md"]

    @pytest.mark.unit
    def test_execute_llm_error_returns_safe_error_result(self):
        agent = DynamicAgent(
            agent_row=_make_agent_row(), collection_name="C",
        )

        doc = Mock()
        doc.page_content = "body"
        doc.metadata = {"source": "doc.md"}

        llm = Mock()
        llm.generate_with_usage.side_effect = RuntimeError("provider down")

        with patch.object(agent, "search", return_value=[doc]):
            with patch.object(agent, "_get_llm", return_value=llm):
                result = agent.execute("q")

        assert result.confidence == 0.0
        assert result.tokens_used == 0
        assert "provider down" in result.answer
        assert result.sources == []

    @pytest.mark.unit
    def test_execute_thinking_truncates_long_questions(self):
        agent = DynamicAgent(
            agent_row=_make_agent_row(), collection_name="C",
        )
        long_q = "x" * 200

        doc = Mock()
        doc.page_content = "body"
        doc.metadata = {"source": "doc.md"}

        llm = Mock()
        llm.generate_with_usage.return_value = (
            "ok", {"total_tokens": 5, "model": "m"},
        )

        with patch.object(agent, "search", return_value=[doc]):
            with patch.object(agent, "_get_llm", return_value=llm):
                result = agent.execute(long_q)
        # thinking shows first 50 chars max
        assert "x" * 50 in result.thinking
        assert "x" * 51 not in result.thinking

    @pytest.mark.unit
    def test_execute_multiple_docs_collects_all_sources(self):
        agent = DynamicAgent(
            agent_row=_make_agent_row(), collection_name="C",
        )
        docs = [
            Mock(page_content="a", metadata={"source": "a.md", "page": 0}),
            Mock(page_content="b", metadata={"source": "b.md", "page": 1}),
            Mock(page_content="c", metadata={"source": "c.md"}),
        ]
        llm = Mock()
        llm.generate_with_usage.return_value = (
            "ok", {"total_tokens": 5, "model": "m"},
        )
        with patch.object(agent, "search", return_value=docs):
            with patch.object(agent, "_get_llm", return_value=llm):
                result = agent.execute("q")
        assert "a.md#page=1" in result.sources
        assert "b.md#page=2" in result.sources
        assert "c.md" in result.sources
        assert len(result.sources) == 3
