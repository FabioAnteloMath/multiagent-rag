"""
Pytest configuration and shared fixtures for multiagent-rag tests.
"""
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest

# Add backend root to path for imports
backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))


# ============================================================================
# Fixtures: Mock Documents
# ============================================================================

@pytest.fixture
def mock_suporte_api_doc():
    """Mock document about API support (401 error)"""
    doc = Mock()
    doc.page_content = "Erro 401 Unauthorized: O cliente não está autenticado. Verifique o token JWT."
    doc.metadata = {"source": "runbook_auth.md", "page": 0}
    return doc


@pytest.fixture
def mock_database_doc():
    """Mock document about database (postgres slow query)"""
    doc = Mock()
    doc.page_content = "PostgreSQL slow query: Utilize EXPLAIN ANALYZE para debugging. Índice missing pode causar full scan."
    doc.metadata = {"source": "postgres_guide.md", "page": 1}
    return doc


@pytest.fixture
def mock_devops_doc():
    """Mock document about DevOps (deploy rollback)"""
    doc = Mock()
    doc.page_content = "Deploy rollback: Execute /opt/scripts/rollback.sh para reverter para versão anterior."
    doc.metadata = {"source": "deployment.md", "page": 0}
    return doc


@pytest.fixture
def mock_general_doc():
    """Mock document about general support"""
    doc = Mock()
    doc.page_content = "Para suporte geral, consulte a base de conhecimento em https://docs.internal.com"
    doc.metadata = {"source": "general.md", "page": 0}
    return doc


@pytest.fixture
def mock_docs_list(mock_suporte_api_doc, mock_database_doc, mock_devops_doc):
    """List of mock documents for testing"""
    return [mock_suporte_api_doc, mock_database_doc, mock_devops_doc]


# ============================================================================
# Fixtures: Mock LLM Providers
# ============================================================================

@pytest.fixture
def mock_ollama_response():
    """Mock Ollama response"""
    return {
        "response": "Este é um resposta de teste do Ollama mockado."
    }


@pytest.fixture
def mock_ollama_generate(mocker):
    """Mock ollama.generate for testing without real Ollama"""
    return mocker.patch("ollama.generate")


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for agent tests"""
    provider = Mock()
    provider.generate.return_value = "Mocked LLM response"
    provider.generate_with_usage.return_value = (
        "Mocked LLM response",
        {"total_tokens": 50, "prompt_tokens": 20, "completion_tokens": 30, "provider": "mock"}
    )
    return provider


# ============================================================================
# Fixtures: Mock Vector Store
# ============================================================================

@pytest.fixture
def mock_vectorstore():
    """Mock FAISS vector store"""
    store = Mock()
    store.similarity_search.return_value = [mock_suporte_api_doc()]
    return store


# ============================================================================
# Fixtures: Mock Agents
# ============================================================================

@pytest.fixture
def mock_agent_result():
    """Mock AgentResult for testing"""
    result = Mock()
    result.answer = "Resposta mockada do agente"
    result.sources = ["test_doc.md"]
    result.confidence = 0.9
    result.agent_name = "TestAgent"
    result.category = "test"
    result.tokens_used = 100
    result.thinking = "Test thinking"
    result.model_used = "mock-model"
    return result


# ============================================================================
# Fixtures: Sample Data
# ============================================================================

@pytest.fixture
def sample_question_api():
    """Sample API-related question"""
    return "como resolver erro 401 unauthorized no gateway?"


@pytest.fixture
def sample_question_database():
    """Sample database-related question"""
    return "postgres está lento com queries complexas"


@pytest.fixture
def sample_question_devops():
    """Sample DevOps-related question"""
    return "como fazer rollback de deploy em produção?"


@pytest.fixture
def sample_question_generic():
    """Sample generic question"""
    return "o que é kubernetes?"


@pytest.fixture
def sample_question_multi():
    """Sample question that could match multiple categories"""
    return "tenho um erro 500 no postgres e o deploy está falhando"


# ============================================================================
# Fixtures: App Configuration
# ============================================================================

@pytest.fixture
def test_config():
    """Test configuration"""
    return {
        "provider": "ollama",
        "model_name": "llama3.2:3b",
        "temperature": 0.3,
        "system_prompt": "You are a test agent."
    }


@pytest.fixture
def agent_configs():
    """Agent configurations for MasterAgent testing"""
    return {
        "suporte_api": {
            "provider": "ollama",
            "model_name": "llama3.2:3b",
            "temperature": 0.3,
            "system_prompt": "You are API Support Agent."
        },
        "database": {
            "provider": "ollama",
            "model_name": "llama3.2:3b",
            "temperature": 0.3,
            "system_prompt": "You are Database Agent."
        },
        "devops": {
            "provider": "ollama",
            "model_name": "llama3.2:3b",
            "temperature": 0.3,
            "system_prompt": "You are DevOps Agent."
        },
        "general": {
            "provider": "ollama",
            "model_name": "llama3.2:3b",
            "temperature": 0.3,
            "system_prompt": "You are Generalist Agent."
        },
        "classifier": {
            "provider": "ollama",
            "model_name": "llama3.2:3b",
            "temperature": 0.1
        }
    }


# ============================================================================
# Fixtures: Path Helpers
# ============================================================================

@pytest.fixture
def project_root():
    """Project root path"""
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def data_dir(project_root):
    """Data directory path"""
    return project_root / "data"


@pytest.fixture
def docs_dir(project_root):
    """Docs directory path"""
    return project_root / "data" / "docs"


@pytest.fixture
def faiss_dir(project_root):
    """FAISS directory path"""
    return project_root / "data" / "faiss"


# ============================================================================
# Session-scoped fixtures (reuse across tests)
# ============================================================================

@pytest.fixture(scope="session")
def test_session_info():
    """Session-wide test information"""
    return {
        "backend_root": Path(__file__).resolve().parents[2],
        "project_name": "multiagent-rag",
        "test_mode": True
    }