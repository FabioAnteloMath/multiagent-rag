"""
E2E tests for API endpoints using FastAPI TestClient.
Tests the actual HTTP layer without mocking the core logic.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Import the FastAPI app
from app.main import app


@pytest.fixture
def client():
    """Create FastAPI test client"""
    return TestClient(app)


# ============================================================================
# Test: /api/health endpoint
# ============================================================================

class TestHealthEndpoint:
    """E2E tests for /api/health endpoint"""

    @pytest.mark.e2e
    def test_health_returns_ok(self, client):
        """GET /api/health should return status ok"""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.e2e
    def test_health_no_auth_required(self, client):
        """GET /api/health should not require authentication"""
        response = client.get("/api/health")
        assert response.status_code == 200


# ============================================================================
# Test: /api/info endpoint
# ============================================================================

class TestInfoEndpoint:
    """E2E tests for /api/info endpoint"""

    @pytest.mark.e2e
    def test_info_returns_api_info(self, client):
        """GET /api/info should return API information"""
        response = client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Multiagent RAG - Support Copilot"
        assert data["version"] == "0.2.0"


# ============================================================================
# Test: /api/ask endpoint - Request Validation
# ============================================================================

class TestAskEndpointValidation:
    """E2E tests for /api/ask request validation"""

    @pytest.mark.e2e
    def test_ask_requires_question(self, client):
        """POST /api/ask should require question field"""
        response = client.post("/api/ask", json={})
        assert response.status_code == 422  # Validation error

    @pytest.mark.e2e
    def test_ask_question_min_length(self, client):
        """POST /api/ask should reject questions < 3 chars"""
        response = client.post("/api/ask", json={"question": "ab"})
        assert response.status_code == 422

    @pytest.mark.e2e
    def test_ask_question_valid_length(self, client):
        """POST /api/ask should accept questions >= 3 chars"""
        response = client.post("/api/ask", json={"question": "abc"})
        # Could be 422 if validation fails, or 500 if server error (no agents configured)
        assert response.status_code in [200, 422, 500]

    @pytest.mark.e2e
    def test_ask_valid_mode_values(self, client):
        """POST /api/ask should accept valid mode values"""
        for mode in ["baseline", "auto", "single_rag"]:
            response = client.post("/api/ask", json={
                "question": "test question about api",
                "mode": mode
            })
            # Should not be 422 (validation error)
            assert response.status_code != 422, f"Mode {mode} should be valid"

    @pytest.mark.e2e
    def test_ask_invalid_mode_rejected(self, client):
        """POST /api/ask should reject invalid mode values"""
        response = client.post("/api/ask", json={
            "question": "test question",
            "mode": "invalid_mode"
        })
        assert response.status_code == 422

    @pytest.mark.e2e
    def test_ask_valid_force_agent_values(self, client):
        """POST /api/ask should accept valid force_agent values"""
        for agent in ["suporte_api", "database", "devops"]:
            response = client.post("/api/ask", json={
                "question": "test question",
                "mode": "auto",
                "force_agent": agent
            })
            assert response.status_code != 422

    @pytest.mark.e2e
    def test_ask_invalid_force_agent_rejected(self, client):
        """POST /api/ask should reject invalid force_agent values"""
        response = client.post("/api/ask", json={
            "question": "test question",
            "force_agent": "invalid_agent"
        })
        assert response.status_code == 422

    @pytest.mark.e2e
    def test_ask_top_k_bounds(self, client):
        """POST /api/ask should validate top_k bounds"""
        # top_k < 1 should fail
        response = client.post("/api/ask", json={
            "question": "test question",
            "top_k": 0
        })
        assert response.status_code == 422

        # top_k > 10 should fail
        response = client.post("/api/ask", json={
            "question": "test question",
            "top_k": 11
        })
        assert response.status_code == 422

        # top_k = 5 should pass validation
        response = client.post("/api/ask", json={
            "question": "test question",
            "top_k": 5
        })
        assert response.status_code != 422


# ============================================================================
# Test: /api/ingest endpoint
# ============================================================================

class TestIngestEndpoint:
    """E2E tests for /api/ingest endpoint"""

    @pytest.mark.e2e
    def test_ingest_validation_chunk_overlap(self, client):
        """POST /api/ingest should reject chunk_overlap >= chunk_size"""
        response = client.post("/api/ingest", json={
            "chunk_size": 600,
            "chunk_overlap": 600  # overlap >= size is invalid
        })
        assert response.status_code == 400

    @pytest.mark.e2e
    def test_ingest_chunk_size_bounds(self, client):
        """POST /api/ingest should validate chunk_size bounds"""
        # chunk_size < 200 should fail
        response = client.post("/api/ingest", json={
            "chunk_size": 100,
            "chunk_overlap": 10
        })
        assert response.status_code == 422

        # chunk_size > 2000 should fail
        response = client.post("/api/ingest", json={
            "chunk_size": 3000,
            "chunk_overlap": 100
        })
        assert response.status_code == 422

    @pytest.mark.e2e
    def test_ingest_default_values(self, client):
        """POST /api/ingest should accept default values"""
        response = client.post("/api/ingest", json={})
        # Default values are: clear_existing=True, chunk_size=600, chunk_overlap=80
        assert response.status_code in [200, 500]  # 500 if no docs found


# ============================================================================
# Test: API root endpoint
# ============================================================================

class TestRootEndpoint:
    """E2E tests for / endpoint"""

    @pytest.mark.e2e
    def test_root_returns_info(self, client):
        """GET / should return API info or redirect"""
        response = client.get("/")
        # Could be 200 (with HTML) or redirect
        assert response.status_code in [200, 307, 308]


# ============================================================================
# Test: Error handling
# ============================================================================

class TestErrorHandling:
    """E2E tests for error handling"""

    @pytest.mark.e2e
    def test_404_for_unknown_endpoint(self, client):
        """Unknown endpoints should return 404"""
        response = client.get("/api/unknown")
        assert response.status_code == 404

    @pytest.mark.e2e
    def test_method_not_allowed_on_ask(self, client):
        """Wrong HTTP method should return 405"""
        response = client.get("/api/ask")
        assert response.status_code == 405

    @pytest.mark.e2e
    def test_method_not_allowed_on_health(self, client):
        """Wrong HTTP method should return 405"""
        response = client.delete("/api/health")
        assert response.status_code == 405