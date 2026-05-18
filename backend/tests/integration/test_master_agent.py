"""
Integration tests for MasterAgent.
Tests the orchestrator: classify, delegate_parallel, aggregate, single_rag_ask, ask.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

from app.agents.master_agent import MasterAgent, AskResponse, ASK_CLARIFYING
from app.agents.base_agent import AgentResult
from app.agents.classifiers import classify_by_keywords


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def agent_configs():
    """Standard agent configurations for testing"""
    return {
        "suporte_api": {
            "provider": "ollama",
            "model_name": "llama3.2:3b",
            "temperature": 0.3,
            "system_prompt": ""
        },
        "database": {
            "provider": "ollama",
            "model_name": "llama3.2:3b",
            "temperature": 0.3,
            "system_prompt": ""
        },
        "devops": {
            "provider": "ollama",
            "model_name": "llama3.2:3b",
            "temperature": 0.3,
            "system_prompt": ""
        },
        "general": {
            "provider": "ollama",
            "model_name": "llama3.2:3b",
            "temperature": 0.3,
            "system_prompt": ""
        },
        "classifier": {
            "provider": "ollama",
            "model_name": "llama3.2:3b",
            "temperature": 0.1
        }
    }


@pytest.fixture
def master_agent(agent_configs):
    """Create MasterAgent with test configs"""
    return MasterAgent(agent_configs=agent_configs)


@pytest.fixture
def mock_agent_result():
    """Factory for mock AgentResult"""
    def make_result(answer="Test answer", agent_name="TestAgent", category="test",
                    confidence=0.9, tokens_used=100, sources=None, thinking=""):
        return AgentResult(
            answer=answer,
            sources=sources or ["test.md"],
            confidence=confidence,
            agent_name=agent_name,
            category=category,
            tokens_used=tokens_used,
            thinking=thinking,
            model_used="llama3.2:3b"
        )
    return make_result


# ============================================================================
# Test: MasterAgent Initialization
# ============================================================================

class TestMasterAgentInitialization:
    """Unit tests for MasterAgent initialization"""

    @pytest.mark.integration
    def test_master_agent_default_agents(self):
        """MasterAgent should have 4 default agents"""
        agent = MasterAgent()
        assert "suporte_api" in agent.agents
        assert "database" in agent.agents
        assert "devops" in agent.agents
        assert "general" in agent.agents

    @pytest.mark.integration
    def test_master_agent_custom_configs(self):
        """MasterAgent should use custom agent configs"""
        configs = {
            "suporte_api": {
                "provider": "minimax",
                "model_name": "MiniMax-M2.7",
                "temperature": 0.8
            }
        }
        agent = MasterAgent(agent_configs=configs)
        assert agent.agents["suporte_api"].provider == "minimax"
        assert agent.agents["suporte_api"].model_name == "MiniMax-M2.7"
        assert agent.agents["suporte_api"].temperature == 0.8

    @pytest.mark.integration
    def test_master_agent_has_classifier(self):
        """MasterAgent should have a classifier"""
        agent = MasterAgent()
        assert agent.classifier is not None

    @pytest.mark.integration
    def test_master_agent_default_timeout(self):
        """MasterAgent should have 180s default timeout"""
        agent = MasterAgent()
        assert agent.agent_timeout == 180


# ============================================================================
# Test: needs_clarifying
# ============================================================================

class TestNeedsClarifying:
    """Unit tests for MasterAgent.needs_clarifying()"""

    @pytest.mark.integration
    def test_empty_categories(self):
        """Empty categories should need clarifying"""
        agent = MasterAgent()
        assert agent.needs_clarifying([]) is True

    @pytest.mark.integration
    def test_clarifying_category(self):
        """'clarifying' in categories should need clarifying"""
        agent = MasterAgent()
        assert agent.needs_clarifying(["clarifying"]) is True
        assert agent.needs_clarifying(["suporte_api", "clarifying"]) is True

    @pytest.mark.integration
    def test_general_only(self):
        """categories == ['general'] should NOT need clarifying"""
        agent = MasterAgent()
        assert agent.needs_clarifying(["general"]) is False

    @pytest.mark.integration
    def test_specific_categories(self):
        """Specific categories should NOT need clarifying"""
        agent = MasterAgent()
        assert agent.needs_clarifying(["suporte_api"]) is False
        assert agent.needs_clarifying(["database", "devops"]) is False
        assert agent.needs_clarifying(["suporte_api", "database", "devops"]) is False


# ============================================================================
# Test: classify
# ============================================================================

class TestClassify:
    """Unit tests for MasterAgent.classify()"""

    @pytest.mark.integration
    def test_classify_uses_keyword_when_llm_fails(self, master_agent):
        """classify should fallback to keyword when LLM fails"""
        with patch.object(master_agent.classifier, 'classify', side_effect=Exception("LLM error")):
            result = master_agent.classify("postgres query error")
            # postgres query error matches both "database" (postgres) and "suporte_api" (error)
            assert "database" in result
            assert isinstance(result, list)

    @pytest.mark.integration
    def test_classify_with_force_disabled(self):
        """classify should use keyword when use_llm_classify is False"""
        agent = MasterAgent()
        agent.use_llm_classify = False

        result = agent.classify("deploy kubernetes rollback")
        assert "devops" in result

    @pytest.mark.integration
    def test_classify_keyword_fallback_api(self, master_agent):
        """classify keyword fallback for API questions"""
        with patch.object(master_agent.classifier, 'classify', side_effect=Exception("fail")):
            result = master_agent.classify("401 unauthorized error gateway")
            assert "suporte_api" in result

    @pytest.mark.integration
    def test_classify_keyword_fallback_database(self, master_agent):
        """classify keyword fallback for database questions"""
        with patch.object(master_agent.classifier, 'classify', side_effect=Exception("fail")):
            result = master_agent.classify("postgres slow query timeout")
            assert "database" in result

    @pytest.mark.integration
    def test_classify_keyword_fallback_devops(self, master_agent):
        """classify keyword fallback for devops questions"""
        with patch.object(master_agent.classifier, 'classify', side_effect=Exception("fail")):
            result = master_agent.classify("deploy kubernetes rollback ci/cd")
            assert "devops" in result


# ============================================================================
# Test: aggregate
# ============================================================================

class TestAggregate:
    """Unit tests for MasterAgent.aggregate()"""

    @pytest.mark.integration
    def test_aggregate_single_answer(self, master_agent, mock_agent_result):
        """aggregate should return single answer when one agent responds"""
        results = {
            "suporte_api": mock_agent_result(
                answer="API error solution",
                agent_name="API Support Agent",
                category="suporte_api",
                confidence=0.9
            )
        }
        response = master_agent.aggregate(results)

        assert response.answer == "API error solution"
        assert response.confidence == 0.9
        assert "API Support Agent" in response.agent_used
        assert response.steps == ["classify", "delegate_parallel", "aggregate"]

    @pytest.mark.integration
    def test_aggregate_filters_no_info(self, master_agent, mock_agent_result):
        """aggregate should filter out 'no info' responses"""
        results = {
            "suporte_api": mock_agent_result(
                answer="I did not find relevant information in the knowledge base.",
                agent_name="API Support Agent",
                category="suporte_api",
                confidence=0.0
            ),
            "database": mock_agent_result(
                answer="Postgres solution: use EXPLAIN ANALYZE",
                agent_name="Database Agent",
                category="database",
                confidence=0.9
            )
        }
        response = master_agent.aggregate(results)

        # Only database answer should be present
        assert "Postgres solution" in response.answer
        assert "I did not find relevant" not in response.answer
        assert "Database Agent" in response.agent_used
        assert "API Support Agent" not in response.agent_used

    @pytest.mark.integration
    def test_aggregate_multiple_answers(self, master_agent, mock_agent_result):
        """aggregate should combine multiple answers"""
        results = {
            "suporte_api": mock_agent_result(
                answer="API error solution",
                agent_name="API Support Agent",
                category="suporte_api"
            ),
            "database": mock_agent_result(
                answer="Database solution",
                agent_name="Database Agent",
                category="database"
            )
        }
        response = master_agent.aggregate(results)

        assert "\n\n---\n\n" in response.answer
        assert "API error solution" in response.answer
        assert "Database solution" in response.answer

    @pytest.mark.integration
    def test_aggregate_no_valid_answers(self, master_agent, mock_agent_result):
        """aggregate should return 'no info' message when all agents return no info"""
        results = {
            "suporte_api": mock_agent_result(
                answer="I did not find relevant information",
                agent_name="API Support Agent",
                category="suporte_api",
                confidence=0.0
            ),
            "database": mock_agent_result(
                answer="could not find relevant information",
                agent_name="Database Agent",
                category="database",
                confidence=0.0
            )
        }
        response = master_agent.aggregate(results)

        assert "No agent found relevant information" in response.answer
        assert response.confidence == 0.0

    @pytest.mark.integration
    def test_aggregate_calculates_avg_confidence(self, master_agent, mock_agent_result):
        """aggregate should calculate average confidence"""
        results = {
            "suporte_api": mock_agent_result(confidence=0.8),
            "database": mock_agent_result(confidence=1.0)
        }
        response = master_agent.aggregate(results)

        assert response.confidence == 0.9  # (0.8 + 1.0) / 2

    @pytest.mark.integration
    def test_aggregate_merges_sources(self, master_agent, mock_agent_result):
        """aggregate should merge and deduplicate sources"""
        results = {
            "suporte_api": mock_agent_result(sources=["api.md", "auth.md"]),
            "database": mock_agent_result(sources=["postgres.md", "api.md"])
        }
        response = master_agent.aggregate(results)

        assert len(response.sources) == 3  # deduplicated
        assert "api.md" in response.sources
        assert "auth.md" in response.sources
        assert "postgres.md" in response.sources

    @pytest.mark.integration
    def test_aggregate_accumulates_tokens(self, master_agent, mock_agent_result):
        """aggregate should accumulate tokens_used"""
        results = {
            "suporte_api": mock_agent_result(tokens_used=100),
            "database": mock_agent_result(tokens_used=200)
        }
        response = master_agent.aggregate(results)

        assert response.tokens_used == 300


# ============================================================================
# Test: delegate_parallel
# ============================================================================

class TestDelegateParallel:
    """Unit tests for MasterAgent.delegate_parallel()"""

    @pytest.mark.integration
    def test_delegate_parallel_runs_all_categories(self, master_agent):
        """delegate_parallel should execute all valid categories"""
        with patch.object(master_agent.agents["suporte_api"], 'execute') as mock_api:
            with patch.object(master_agent.agents["database"], 'execute') as mock_db:
                mock_api.return_value = AgentResult(
                    answer="API answer", sources=[], confidence=0.9,
                    agent_name="API Support Agent", category="suporte_api"
                )
                mock_db.return_value = AgentResult(
                    answer="DB answer", sources=[], confidence=0.9,
                    agent_name="Database Agent", category="database"
                )

                results = master_agent.delegate_parallel("test question", ["suporte_api", "database"])

                assert "suporte_api" in results
                assert "database" in results
                mock_api.assert_called_once_with("test question")
                mock_db.assert_called_once_with("test question")

    @pytest.mark.integration
    def test_delegate_parallel_fallback_to_general(self, master_agent):
        """delegate_parallel should fallback to general if no valid categories"""
        with patch.object(master_agent.agents["general"], 'execute') as mock_general:
            mock_general.return_value = AgentResult(
                answer="General answer", sources=[], confidence=0.8,
                agent_name="Generalist Agent", category="general"
            )

            results = master_agent.delegate_parallel("test question", ["invalid_cat"])

            assert "general" in results
            mock_general.assert_called_once_with("test question")

    @pytest.mark.integration
    def test_delegate_parallel_handles_timeout(self, master_agent):
        """delegate_parallel should handle agent timeouts"""
        from concurrent.futures import TimeoutError as FuturesTimeoutError

        with patch.object(master_agent.agents["suporte_api"], 'execute') as mock_api:
            mock_api.side_effect = FuturesTimeoutError()

            results = master_agent.delegate_parallel("test question", ["suporte_api"])

            assert "suporte_api" in results
            assert "timed out" in results["suporte_api"].answer.lower()

    @pytest.mark.integration
    def test_delegate_parallel_handles_exception(self, master_agent):
        """delegate_parallel should handle agent exceptions"""
        with patch.object(master_agent.agents["suporte_api"], 'execute') as mock_api:
            mock_api.side_effect = Exception("Agent error")

            results = master_agent.delegate_parallel("test question", ["suporte_api"])

            assert "suporte_api" in results
            assert "error" in results["suporte_api"].answer.lower()


# ============================================================================
# Test: ask (full flow with force_agent)
# ============================================================================

class TestAsk:
    """Unit tests for MasterAgent.ask() with force_agent"""

    @pytest.mark.integration
    def test_ask_force_agent_direct(self, master_agent, mock_agent_result):
        """ask with force_agent should directly call that agent"""
        with patch.object(master_agent.agents["database"], 'execute') as mock_execute:
            mock_execute.return_value = mock_agent_result(
                answer="Database direct answer",
                agent_name="Database Agent",
                category="database"
            )

            response = master_agent.ask("postgres question", force_agent="database")

            mock_execute.assert_called_once_with("postgres question")
            assert response.answer == "Database direct answer"
            assert response.steps == ["direct", "database"]

    @pytest.mark.integration
    def test_ask_invalid_force_agent_ignored(self, master_agent):
        """ask should ignore invalid force_agent and use classification"""
        with patch.object(master_agent, 'classify', return_value=["general"]):
            with patch.object(master_agent, 'delegate_parallel') as mock_delegate:
                mock_delegate.return_value = {
                    "general": AgentResult(
                        answer="General answer", sources=[], confidence=0.8,
                        agent_name="Generalist Agent", category="general"
                    )
                }
                response = master_agent.ask("generic question", force_agent="invalid_agent")

                assert response.steps == ["classify", "delegate_parallel", "aggregate"]


# ============================================================================
# Test: ask (full flow with classification)
# ============================================================================

class TestAskClassification:
    """Unit tests for MasterAgent.ask() with classification"""

    @pytest.mark.integration
    def test_ask_needs_clarifying(self, master_agent):
        """ask should return clarifying message when categories need clarification"""
        with patch.object(master_agent, 'classify', return_value=[]):
            response = master_agent.ask("help")

            assert ASK_CLARIFYING in response.answer
            assert response.steps == ["classify", "clarifying"]
            assert response.needs_clarifying is True or response.answer == ASK_CLARIFYING

    @pytest.mark.integration
    def test_ask_single_category(self, master_agent):
        """ask should delegate to single agent when single category"""
        with patch.object(master_agent, 'classify', return_value=["suporte_api"]):
            with patch.object(master_agent, 'delegate_parallel') as mock_delegate:
                mock_delegate.return_value = {
                    "suporte_api": AgentResult(
                        answer="API answer", sources=["api.md"], confidence=0.9,
                        agent_name="API Support Agent", category="suporte_api",
                        tokens_used=50
                    )
                }
                response = master_agent.ask("401 error question")

                assert "API answer" in response.answer

    @pytest.mark.integration
    def test_ask_multiple_categories(self, master_agent):
        """ask should delegate to multiple agents when multiple categories"""
        with patch.object(master_agent, 'classify', return_value=["suporte_api", "database"]):
            with patch.object(master_agent, 'delegate_parallel') as mock_delegate:
                mock_delegate.return_value = {
                    "suporte_api": AgentResult(
                        answer="API answer", sources=["api.md"], confidence=0.9,
                        agent_name="API Support Agent", category="suporte_api"
                    ),
                    "database": AgentResult(
                        answer="DB answer", sources=["db.md"], confidence=0.9,
                        agent_name="Database Agent", category="database"
                    )
                }
                response = master_agent.ask("error in database api")

                assert "API answer" in response.answer
                assert "DB answer" in response.answer


# ============================================================================
# Test: single_rag_ask
# ============================================================================

class TestSingleRagAsk:
    """Unit tests for MasterAgent.single_rag_ask()"""

    @pytest.mark.integration
    def test_single_rag_force_agent(self, master_agent, mock_agent_result):
        """single_rag_ask with force_agent should use that agent"""
        mock_doc = Mock()
        mock_doc.page_content = "Doc content"
        mock_doc.metadata = {"source": "doc.md", "page": 0}

        mock_llm = Mock()
        mock_llm.generate_with_usage.return_value = (
            "Direct answer", {"total_tokens": 50, "model": "llama3.2:3b"}
        )

        with patch.object(master_agent.agents["database"], 'search', return_value=[mock_doc]):
            with patch.object(master_agent.agents["database"], '_get_llm', return_value=mock_llm):
                response = master_agent.single_rag_ask("postgres question", force_agent="database")

        assert response.collection_searched == "Database"
        assert response.steps == ["route", "search", "generate"]
        assert response.confidence == 0.9

    @pytest.mark.integration
    def test_single_rag_classify_and_route(self, master_agent):
        """single_rag_ask should classify and route to primary category"""
        mock_doc = Mock()
        mock_doc.page_content = "API error content"
        mock_doc.metadata = {"source": "api.md", "page": 0}

        mock_llm = Mock()
        mock_llm.generate_with_usage.return_value = (
            "API answer", {"total_tokens": 50, "model": "llama3.2:3b"}
        )

        with patch.object(master_agent, 'classify', return_value=["suporte_api"]):
            with patch.object(master_agent.agents["suporte_api"], 'search', return_value=[mock_doc]):
                with patch.object(master_agent.agents["suporte_api"], '_get_llm', return_value=mock_llm):
                    response = master_agent.single_rag_ask("401 error")

        assert response.collection_searched == "SuporteAPI"
        assert "suporte_api" in response.thinking

    @pytest.mark.integration
    def test_single_rag_no_docs(self, master_agent):
        """single_rag_ask should return 'no match' when no docs found"""
        with patch.object(master_agent, 'classify', return_value=["suporte_api"]):
            with patch.object(master_agent.agents["suporte_api"], 'search', return_value=[]):
                response = master_agent.single_rag_ask("unknown question")

        assert "No relevant information found" in response.answer
        assert response.steps == ["route", "search", "no_match"]
        assert response.confidence == 0.0

    @pytest.mark.integration
    def test_single_rag_needs_clarifying(self, master_agent):
        """single_rag_ask should return clarifying message when needed"""
        with patch.object(master_agent, 'classify', return_value=["clarifying"]):
            response = master_agent.single_rag_ask("help")

        assert ASK_CLARIFYING in response.answer
        assert response.steps == ["classify", "clarifying"]

    @pytest.mark.integration
    def test_single_rag_fallback_to_general(self, master_agent):
        """single_rag_ask should fallback to general when no category matches"""
        mock_doc = Mock()
        mock_doc.page_content = "General content"
        mock_doc.metadata = {"source": "general.md", "page": 0}

        mock_llm = Mock()
        mock_llm.generate_with_usage.return_value = (
            "General answer", {"total_tokens": 50, "model": "llama3.2:3b"}
        )

        # classify returns ["general"], needs_clarifying returns False,
        # categories[0] is "general" which exists in agents
        with patch.object(master_agent, 'classify', return_value=["general"]):
            with patch.object(master_agent.agents["general"], 'search', return_value=[mock_doc]):
                with patch.object(master_agent.agents["general"], '_get_llm', return_value=mock_llm):
                    response = master_agent.single_rag_ask("generic question")

        assert response.collection_searched == "General"

    @pytest.mark.integration
    def test_single_rag_handles_llm_error(self, master_agent):
        """single_rag_ask should handle LLM errors gracefully"""
        mock_doc = Mock()
        mock_doc.page_content = "Content"
        mock_doc.metadata = {"source": "doc.md"}

        mock_llm = Mock()
        mock_llm.generate_with_usage.side_effect = Exception("LLM error")

        with patch.object(master_agent, 'classify', return_value=["suporte_api"]):
            with patch.object(master_agent.agents["suporte_api"], 'search', return_value=[mock_doc]):
                with patch.object(master_agent.agents["suporte_api"], '_get_llm', return_value=mock_llm):
                    response = master_agent.single_rag_ask("question")

        assert "Error" in response.answer
        assert response.confidence == 0.0


# ============================================================================
# Test: AskResponse Dataclass
# ============================================================================

class TestAskResponse:
    """Unit tests for AskResponse dataclass"""

    @pytest.mark.integration
    def test_ask_response_creation(self):
        """AskResponse should be created with required fields"""
        response = AskResponse(
            answer="Test answer",
            sources=["source.md"],
            agent_used=["TestAgent"],
            steps=["step1", "step2"]
        )
        assert response.answer == "Test answer"
        assert response.sources == ["source.md"]
        assert response.agent_used == ["TestAgent"]
        assert response.steps == ["step1", "step2"]

    @pytest.mark.integration
    def test_ask_response_defaults(self):
        """AskResponse should have correct defaults"""
        response = AskResponse(
            answer="Test",
            sources=[],
            agent_used=[],
            steps=[]
        )
        assert response.needs_clarifying is False
        assert response.tokens_used == 0
        assert response.thinking == ""
        assert response.model_used == ""
        assert response.total_time_ms == 0.0
        assert response.confidence == 0.0
        assert response.collection_searched == ""

    @pytest.mark.integration
    def test_ask_response_with_all_fields(self):
        """AskResponse should accept all optional fields"""
        response = AskResponse(
            answer="Complete answer",
            sources=["source1.md", "source2.md"],
            agent_used=["Agent1", "Agent2"],
            steps=["classify", "search", "generate"],
            needs_clarifying=False,
            tokens_used=250,
            thinking="Test thinking",
            model_used="llama3.2:3b",
            total_time_ms=1500.5,
            confidence=0.95,
            collection_searched="SuporteAPI"
        )
        assert response.needs_clarifying is False
        assert response.tokens_used == 250
        assert response.thinking == "Test thinking"
        assert response.model_used == "llama3.2:3b"
        assert response.total_time_ms == 1500.5
        assert response.confidence == 0.95
        assert response.collection_searched == "SuporteAPI"


# ============================================================================
# Test: ASK_CLARIFYING constant
# ============================================================================

class TestAskClarifyingConstant:
    """Unit tests for ASK_CLARIFYING constant"""

    @pytest.mark.integration
    def test_ask_clarifying_is_not_empty(self):
        """ASK_CLARIFYING should not be empty"""
        assert len(ASK_CLARIFYING) > 0

    @pytest.mark.integration
    def test_ask_clarifying_contains_examples(self):
        """ASK_CLARIFYING should contain examples"""
        assert "Examples:" in ASK_CLARIFYING or "examples" in ASK_CLARIFYING.lower()

    @pytest.mark.integration
    def test_ask_clarifying_mentions_specificity(self):
        """ASK_CLARIFYING should mention being specific"""
        assert "specific" in ASK_CLARIFYING.lower()