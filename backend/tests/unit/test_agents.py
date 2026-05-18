"""
Unit tests for agent modules.
Tests BaseAgent, specialized agents (APISupportAgent, DatabaseAgent, DevOpsAgent, GeneralistAgent).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path

from app.agents.base_agent import BaseAgent, AgentResult
from app.agents.agente_suporte import APISupportAgent
from app.agents.agente_database import DatabaseAgent
from app.agents.agente_devops import DevOpsAgent
from app.agents.agente_generalista import GeneralistAgent


# ============================================================================
# Test: AgentResult Dataclass
# ============================================================================

class TestAgentResult:
    """Unit tests for AgentResult dataclass"""

    @pytest.mark.unit
    def test_agent_result_creation(self):
        """AgentResult should be created with required fields"""
        result = AgentResult(
            answer="Test answer",
            sources=["doc1.md"],
            confidence=0.9,
            agent_name="TestAgent",
            category="test"
        )
        assert result.answer == "Test answer"
        assert result.sources == ["doc1.md"]
        assert result.confidence == 0.9
        assert result.agent_name == "TestAgent"
        assert result.category == "test"

    @pytest.mark.unit
    def test_agent_result_defaults(self):
        """AgentResult should have correct defaults"""
        result = AgentResult(
            answer="Test",
            sources=[],
            confidence=0.0,
            agent_name="Test",
            category="test"
        )
        assert result.tokens_used == 0
        assert result.thinking == ""
        assert result.model_used == ""

    @pytest.mark.unit
    def test_agent_result_with_optional_fields(self):
        """AgentResult should accept optional fields"""
        result = AgentResult(
            answer="Test",
            sources=["doc.md"],
            confidence=0.85,
            agent_name="Test",
            category="test",
            tokens_used=150,
            thinking="Processing...",
            model_used="llama3.2:3b"
        )
        assert result.tokens_used == 150
        assert result.thinking == "Processing..."
        assert result.model_used == "llama3.2:3b"


# ============================================================================
# Test: BaseAgent - format_context
# ============================================================================

class TestBaseAgentFormatContext:
    """Unit tests for BaseAgent.format_context()"""

    @pytest.mark.unit
    def test_format_context_empty_docs(self):
        """format_context should return 'no relevant context' for empty docs"""
        agent = APISupportAgent()
        result = agent.format_context([])
        assert result == "I did not find relevant context."

    @pytest.mark.unit
    def test_format_context_single_doc(self):
        """format_context should join single doc content"""
        agent = APISupportAgent()
        mock_doc = Mock()
        mock_doc.page_content = "This is document content"
        result = agent.format_context([mock_doc])
        assert result == "This is document content"

    @pytest.mark.unit
    def test_format_context_multiple_docs(self):
        """format_context should join multiple docs with double newline"""
        agent = APISupportAgent()
        doc1 = Mock(page_content="First document content")
        doc2 = Mock(page_content="Second document content")
        result = agent.format_context([doc1, doc2])
        assert result == "First document content\n\nSecond document content"

    @pytest.mark.unit
    def test_format_context_uses_page_content_only(self):
        """format_context should use only page_content, ignore other attrs"""
        agent = APISupportAgent()
        doc = Mock()
        doc.page_content = "Real content"
        doc.metadata = {"source": "ignored"}
        result = agent.format_context([doc])
        assert result == "Real content"


# ============================================================================
# Test: BaseAgent - get_system_prompt
# ============================================================================

class TestBaseAgentGetSystemPrompt:
    """Unit tests for BaseAgent.get_system_prompt()"""

    @pytest.mark.unit
    def test_get_system_prompt_contains_name(self):
        """get_system_prompt should contain agent name"""
        agent = APISupportAgent()
        prompt = agent.get_system_prompt("test question", "test context")
        assert "API Support Agent" in prompt

    @pytest.mark.unit
    def test_get_system_prompt_contains_category(self):
        """get_system_prompt should contain category"""
        agent = APISupportAgent()
        prompt = agent.get_system_prompt("test question", "test context")
        assert "suporte_api" in prompt

    @pytest.mark.unit
    def test_get_system_prompt_contains_question(self):
        """get_system_prompt should contain the question"""
        agent = APISupportAgent()
        prompt = agent.get_system_prompt("How to fix 401?", "some context")
        assert "How to fix 401?" in prompt

    @pytest.mark.unit
    def test_get_system_prompt_contains_context(self):
        """get_system_prompt should contain context"""
        agent = APISupportAgent()
        prompt = agent.get_system_prompt("test question", "JWT token invalid")
        assert "JWT token invalid" in prompt

    @pytest.mark.unit
    def test_get_system_prompt_structure(self):
        """get_system_prompt should have correct structure"""
        agent = APISupportAgent()
        prompt = agent.get_system_prompt("Q", "C")
        assert "You are" in prompt
        assert "Context:" in prompt
        assert "Question:" in prompt

    @pytest.mark.unit
    def test_get_system_prompt_with_custom_system_prompt(self):
        """get_system_prompt should use name/category, not custom system_prompt directly"""
        agent = APISupportAgent(system_prompt="Custom system prompt")
        prompt = agent.get_system_prompt("Q", "C")
        # BaseAgent.get_system_prompt uses name/category, not custom _system_prompt
        assert "API Support Agent" in prompt
        assert "suporte_api" in prompt


# ============================================================================
# Test: BaseAgent - search (mocked vectorstore)
# ============================================================================

class TestBaseAgentSearch:
    """Unit tests for BaseAgent.search() with mocked vectorstore"""

    @pytest.mark.unit
    def test_search_returns_empty_when_no_vectorstore(self):
        """search should return empty list when vectorstore doesn't exist"""
        agent = APISupportAgent()
        agent._vectorstore = None

        with patch.object(agent, '_load_vectorstore', return_value=None):
            result = agent.search("test query")
            assert result == []

    @pytest.mark.unit
    def test_search_calls_similarity_search(self):
        """search should call similarity_search on vectorstore"""
        agent = APISupportAgent()
        mock_store = Mock()
        mock_docs = [Mock(), Mock()]
        mock_store.similarity_search.return_value = mock_docs
        agent._vectorstore = mock_store

        result = agent.search("test query", top_k=5)

        mock_store.similarity_search.assert_called_once_with("test query", k=5)
        assert result == mock_docs

    @pytest.mark.unit
    def test_search_uses_default_top_k(self):
        """search should use default top_k=4"""
        agent = APISupportAgent()
        mock_store = Mock()
        mock_store.similarity_search.return_value = []
        agent._vectorstore = mock_store

        agent.search("test query")

        mock_store.similarity_search.assert_called_once_with("test query", k=4)

    @pytest.mark.unit
    def test_search_loads_vectorstore_if_none(self):
        """search should load vectorstore if not loaded"""
        agent = APISupportAgent()
        agent._vectorstore = None
        mock_store = Mock()
        mock_store.similarity_search.return_value = []

        with patch.object(agent, '_load_vectorstore', return_value=mock_store):
            agent.search("test query")

        mock_store.similarity_search.assert_called_once()


# ============================================================================
# Test: BaseAgent - refresh_vectorstore
# ============================================================================

class TestBaseAgentRefreshVectorstore:
    """Unit tests for BaseAgent.refresh_vectorstore()"""

    @pytest.mark.unit
    def test_refresh_vectorstore_clears_cache(self):
        """refresh_vectorstore should set _vectorstore to None"""
        agent = APISupportAgent()
        agent._vectorstore = Mock()  # Pre-existing store

        with patch.object(agent, '_load_vectorstore', return_value=None):
            agent.refresh_vectorstore()

        assert agent._vectorstore is None


# ============================================================================
# Test: Specialized Agent - APISupportAgent
# ============================================================================

class TestAPISupportAgent:
    """Unit tests for APISupportAgent"""

    @pytest.mark.unit
    def test_api_support_agent_initialization(self):
        """APISupportAgent should have correct default values"""
        agent = APISupportAgent()
        assert agent.name == "API Support Agent"
        assert agent.category == "suporte_api"
        assert agent.collection_name == "SuporteAPI"
        assert agent.provider == "ollama"
        assert agent.model_name == "llama3.2:3b"
        assert agent.temperature == 0.3

    @pytest.mark.unit
    def test_api_support_agent_custom_config(self):
        """APISupportAgent should accept custom config"""
        agent = APISupportAgent(
            provider="minimax",
            model_name="MiniMax-M2.7",
            temperature=0.7,
            system_prompt="Custom prompt"
        )
        assert agent.provider == "minimax"
        assert agent.model_name == "MiniMax-M2.7"
        assert agent.temperature == 0.7
        assert agent._system_prompt == "Custom prompt"

    @pytest.mark.unit
    def test_api_support_agent_execute_no_docs(self):
        """execute should return 'no info' when no docs found"""
        agent = APISupportAgent()

        with patch.object(agent, 'search', return_value=[]):
            result = agent.execute("test question")

        assert result.answer == "I did not find relevant information about API support in the knowledge base."
        assert result.sources == []
        assert result.confidence == 0.0
        assert result.agent_name == "API Support Agent"
        assert result.category == "suporte_api"

    @pytest.mark.unit
    def test_api_support_agent_execute_with_docs(self):
        """execute should return answer when docs found"""
        agent = APISupportAgent()

        mock_doc = Mock()
        mock_doc.page_content = "Error 401 means unauthorized"
        mock_doc.metadata = {"source": "api_errors.md", "page": 5}

        mock_llm = Mock()
        mock_llm.generate_with_usage.return_value = (
            "401 error indicates unauthorized access",
            {"total_tokens": 100, "model": "llama3.2:3b"}
        )

        with patch.object(agent, 'search', return_value=[mock_doc]):
            with patch.object(agent, '_get_llm', return_value=mock_llm):
                result = agent.execute("what is error 401?")

        assert result.answer == "401 error indicates unauthorized access"
        assert result.confidence == 0.9
        assert result.agent_name == "API Support Agent"
        assert "api_errors.md#page=6" in result.sources  # page+1

    @pytest.mark.unit
    def test_api_support_agent_execute_handles_error(self):
        """execute should handle LLM errors gracefully"""
        agent = APISupportAgent()

        mock_doc = Mock()
        mock_doc.page_content = "Some content"
        mock_doc.metadata = {"source": "doc.md"}

        mock_llm = Mock()
        mock_llm.generate_with_usage.side_effect = Exception("LLM Error")

        with patch.object(agent, 'search', return_value=[mock_doc]):
            with patch.object(agent, '_get_llm', return_value=mock_llm):
                result = agent.execute("test question")

        assert "Error" in result.answer
        assert result.confidence == 0.0
        assert result.tokens_used == 0


# ============================================================================
# Test: Specialized Agent - DatabaseAgent
# ============================================================================

class TestDatabaseAgent:
    """Unit tests for DatabaseAgent"""

    @pytest.mark.unit
    def test_database_agent_initialization(self):
        """DatabaseAgent should have correct default values"""
        agent = DatabaseAgent()
        assert agent.name == "Database Agent"
        assert agent.category == "database"
        assert agent.collection_name == "Database"
        assert agent.provider == "ollama"

    @pytest.mark.unit
    def test_database_agent_execute_no_docs(self):
        """execute should return 'no info' when no docs found"""
        agent = DatabaseAgent()

        with patch.object(agent, 'search', return_value=[]):
            result = agent.execute("postgres slow query")

        assert result.answer == "I did not find relevant information about databases in the knowledge base."
        assert result.confidence == 0.0
        assert result.category == "database"

    @pytest.mark.unit
    def test_database_agent_execute_with_docs(self):
        """execute should return answer when docs found"""
        agent = DatabaseAgent()

        mock_doc = Mock()
        mock_doc.page_content = "PostgreSQL slow query optimization"
        mock_doc.metadata = {"source": "postgres_guide.md", "page": 0}

        mock_llm = Mock()
        mock_llm.generate_with_usage.return_value = (
            "Use EXPLAIN ANALYZE to debug slow queries",
            {"total_tokens": 80, "model": "llama3.2:3b"}
        )

        with patch.object(agent, 'search', return_value=[mock_doc]):
            with patch.object(agent, '_get_llm', return_value=mock_llm):
                result = agent.execute("how to optimize slow query?")

        assert result.answer == "Use EXPLAIN ANALYZE to debug slow queries"
        assert result.confidence == 0.9
        assert result.agent_name == "Database Agent"


# ============================================================================
# Test: Specialized Agent - DevOpsAgent
# ============================================================================

class TestDevOpsAgent:
    """Unit tests for DevOpsAgent"""

    @pytest.mark.unit
    def test_devops_agent_initialization(self):
        """DevOpsAgent should have correct default values"""
        agent = DevOpsAgent()
        assert agent.name == "DevOps Agent"
        assert agent.category == "devops"
        assert agent.collection_name == "DevOps"
        assert agent.provider == "ollama"

    @pytest.mark.unit
    def test_devops_agent_execute_no_docs(self):
        """execute should return 'no info' when no docs found"""
        agent = DevOpsAgent()

        with patch.object(agent, 'search', return_value=[]):
            result = agent.execute("deploy kubernetes")

        assert result.answer == "I did not find relevant information about DevOps in the knowledge base."
        assert result.confidence == 0.0
        assert result.category == "devops"

    @pytest.mark.unit
    def test_devops_agent_execute_with_docs(self):
        """execute should return answer when docs found"""
        agent = DevOpsAgent()

        mock_doc = Mock()
        mock_doc.page_content = "Kubernetes deployment rollback procedure"
        mock_doc.metadata = {"source": "k8s_guide.md", "page": 2}

        mock_llm = Mock()
        mock_llm.generate_with_usage.return_value = (
            "Run kubectl rollout undo to rollback",
            {"total_tokens": 60, "model": "llama3.2:3b"}
        )

        with patch.object(agent, 'search', return_value=[mock_doc]):
            with patch.object(agent, '_get_llm', return_value=mock_llm):
                result = agent.execute("how to rollback deploy?")

        assert result.answer == "Run kubectl rollout undo to rollback"
        assert result.confidence == 0.9
        assert result.agent_name == "DevOps Agent"


# ============================================================================
# Test: Specialized Agent - GeneralistAgent
# ============================================================================

class TestGeneralistAgent:
    """Unit tests for GeneralistAgent"""

    @pytest.mark.unit
    def test_generalist_agent_initialization(self):
        """GeneralistAgent should have correct default values"""
        agent = GeneralistAgent()
        assert agent.name == "Generalist Agent"
        assert agent.category == "general"
        assert agent.collection_name == "General"
        assert agent.provider == "ollama"

    @pytest.mark.unit
    def test_generalist_agent_execute_no_docs(self):
        """execute should return 'no info' when no docs found"""
        agent = GeneralistAgent()

        with patch.object(agent, 'search', return_value=[]):
            result = agent.execute("general question")

        assert "I did not find relevant information in the knowledge base." in result.answer
        assert result.confidence == 0.0
        assert result.category == "general"

    @pytest.mark.unit
    def test_generalist_agent_execute_with_docs(self):
        """execute should return answer when docs found"""
        agent = GeneralistAgent()

        mock_doc = Mock()
        mock_doc.page_content = "General support information"
        mock_doc.metadata = {"source": "general.md", "page": 0}

        mock_llm = Mock()
        mock_llm.generate_with_usage.return_value = (
            "For general support, contact the helpdesk",
            {"total_tokens": 50, "model": "llama3.2:3b"}
        )

        with patch.object(agent, 'search', return_value=[mock_doc]):
            with patch.object(agent, '_get_llm', return_value=mock_llm):
                result = agent.execute("what is your support process?")

        assert result.answer == "For general support, contact the helpdesk"
        assert result.confidence == 0.8  # GeneralistAgent uses 0.8
        assert result.agent_name == "Generalist Agent"


# ============================================================================
# Test: Specialized Agents - Sources Formatting
# ============================================================================

class TestAgentSourcesFormatting:
    """Unit tests for source formatting in agents"""

    @pytest.mark.unit
    def test_sources_with_page(self):
        """Sources should include page number when available"""
        agent = APISupportAgent()

        mock_doc = Mock()
        mock_doc.page_content = "Content"
        mock_doc.metadata = {"source": "doc.md", "page": 3}

        mock_llm = Mock()
        mock_llm.generate_with_usage.return_value = ("Answer", {"total_tokens": 50, "model": "test"})

        with patch.object(agent, 'search', return_value=[mock_doc]):
            with patch.object(agent, '_get_llm', return_value=mock_llm):
                result = agent.execute("question")

        # page 3 stored, should show page=4 (0-indexed + 1)
        assert "doc.md#page=4" in result.sources

    @pytest.mark.unit
    def test_sources_without_page(self):
        """Sources should not include page when page is None"""
        agent = DatabaseAgent()

        mock_doc = Mock()
        mock_doc.page_content = "Content"
        mock_doc.metadata = {"source": "doc.md"}  # No page

        mock_llm = Mock()
        mock_llm.generate_with_usage.return_value = ("Answer", {"total_tokens": 50, "model": "test"})

        with patch.object(agent, 'search', return_value=[mock_doc]):
            with patch.object(agent, '_get_llm', return_value=mock_llm):
                result = agent.execute("question")

        assert "doc.md" in result.sources
        assert "#page=" not in str(result.sources)

    @pytest.mark.unit
    def test_sources_multiple_docs(self):
        """Sources should include all document sources"""
        agent = DevOpsAgent()

        doc1 = Mock(page_content="Content 1", metadata={"source": "doc1.md", "page": 0})
        doc2 = Mock(page_content="Content 2", metadata={"source": "doc2.md", "page": 1})

        mock_llm = Mock()
        mock_llm.generate_with_usage.return_value = ("Answer", {"total_tokens": 50, "model": "test"})

        with patch.object(agent, 'search', return_value=[doc1, doc2]):
            with patch.object(agent, '_get_llm', return_value=mock_llm):
                result = agent.execute("question")

        assert "doc1.md#page=1" in result.sources
        assert "doc2.md#page=2" in result.sources


# ============================================================================
# Test: Agent LLM Configuration
# ============================================================================

class TestAgentLLMConfiguration:
    """Unit tests for agent LLM configuration"""

    @pytest.mark.unit
    def test_agent_uses_correct_provider(self):
        """Agent should use configured provider"""
        agent = APISupportAgent(provider="ollama")
        assert agent.provider == "ollama"

        agent_minimax = APISupportAgent(provider="minimax")
        assert agent_minimax.provider == "minimax"

    @pytest.mark.unit
    def test_agent_uses_correct_model(self):
        """Agent should use configured model"""
        agent = APISupportAgent(model_name="llama3.2:3b")
        assert agent.model_name == "llama3.2:3b"

        agent_custom = APISupportAgent(model_name="MiniMax-M2.7")
        assert agent_custom.model_name == "MiniMax-M2.7"

    @pytest.mark.unit
    def test_agent_uses_correct_temperature(self):
        """Agent should use configured temperature"""
        agent_default = APISupportAgent()
        assert agent_default.temperature == 0.3

        agent_custom = APISupportAgent(temperature=0.9)
        assert agent_custom.temperature == 0.9

    @pytest.mark.unit
    def test_agent_system_prompt_override(self):
        """Agent should use custom system prompt when provided"""
        custom_prompt = "You are a specialized API expert."
        agent = APISupportAgent(system_prompt=custom_prompt)
        assert agent._system_prompt == custom_prompt