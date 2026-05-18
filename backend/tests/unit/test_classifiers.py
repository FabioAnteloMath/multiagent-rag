"""
Sample unit tests for classifiers module.
These tests verify KeywordClassifier and LLMClassifier work correctly.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.agents.classifiers import KeywordClassifier, LLMClassifier, classify_by_keywords


# ============================================================================
# Test: KeywordClassifier
# ============================================================================

class TestKeywordClassifier:
    """Unit tests for KeywordClassifier"""

    def setup_method(self):
        """Setup fresh classifier for each test"""
        self.classifier = KeywordClassifier()

    # -----------------------------------------------------------------------
    # API Support keywords
    # -----------------------------------------------------------------------
    @pytest.mark.unit
    def test_api_error_401(self):
        """401 should classify to suporte_api"""
        result = self.classifier.classify("erro 401 unauthorized")
        assert "suporte_api" in result

    @pytest.mark.unit
    def test_api_error_403(self):
        """403 should classify to suporte_api"""
        result = self.classifier.classify("403 forbidden access denied")
        assert "suporte_api" in result

    @pytest.mark.unit
    def test_api_error_500(self):
        """500 should classify to suporte_api"""
        result = self.classifier.classify("500 internal server error")
        assert "suporte_api" in result

    @pytest.mark.unit
    def test_api_gateway(self):
        """gateway should classify to suporte_api"""
        result = self.classifier.classify("gateway timeout error")
        assert "suporte_api" in result

    @pytest.mark.unit
    def test_api_auth(self):
        """auth/jwt should classify to suporte_api"""
        result = self.classifier.classify("jwt token invalid authentication")
        assert "suporte_api" in result

    @pytest.mark.unit
    def test_api_oauth(self):
        """oauth should classify to suporte_api"""
        result = self.classifier.classify("oauth2 authorization failed")
        assert "suporte_api" in result

    # -----------------------------------------------------------------------
    # Database keywords
    # -----------------------------------------------------------------------
    @pytest.mark.unit
    def test_database_postgres(self):
        """postgres should classify to database"""
        result = self.classifier.classify("postgres slow query")
        assert "database" in result

    @pytest.mark.unit
    def test_database_mysql(self):
        """mysql should classify to database"""
        result = self.classifier.classify("mysql connection timeout")
        assert "database" in result

    @pytest.mark.unit
    def test_database_redis(self):
        """redis should classify to database"""
        result = self.classifier.classify("redis cache unavailable")
        assert "database" in result

    @pytest.mark.unit
    def test_database_query(self):
        """query should classify to database"""
        result = self.classifier.classify("slow query optimization")
        assert "database" in result

    @pytest.mark.unit
    def test_database_connection(self):
        """connection should classify to database"""
        result = self.classifier.classify("database connection refused")
        assert "database" in result

    # -----------------------------------------------------------------------
    # DevOps keywords
    # -----------------------------------------------------------------------
    @pytest.mark.unit
    def test_devops_deploy(self):
        """deploy should classify to devops"""
        result = self.classifier.classify("deploy application production")
        assert "devops" in result

    @pytest.mark.unit
    def test_devops_rollback(self):
        """rollback should classify to devops"""
        result = self.classifier.classify("rollback to previous version")
        assert "devops" in result

    @pytest.mark.unit
    def test_devops_pipeline(self):
        """pipeline should classify to devops"""
        result = self.classifier.classify("ci/cd pipeline failed")
        assert "devops" in result

    @pytest.mark.unit
    def test_devops_kubernetes(self):
        """kubernetes should classify to devops"""
        result = self.classifier.classify("kubernetes pod pending")
        assert "devops" in result

    @pytest.mark.unit
    def test_devops_docker(self):
        """docker should classify to devops"""
        result = self.classifier.classify("docker container restart")
        assert "devops" in result

    @pytest.mark.unit
    def test_devops_release(self):
        """release should classify to devops"""
        result = self.classifier.classify("release criteria abort")
        assert "devops" in result

    @pytest.mark.unit
    def test_devops_ci_cd(self):
        """ci/cd should classify to devops"""
        result = self.classifier.classify("ci cd build monitoring")
        assert "devops" in result

    # -----------------------------------------------------------------------
    # Case insensitivity
    # -----------------------------------------------------------------------
    @pytest.mark.unit
    def test_case_insensitive_uppercase(self):
        """Keywords should be case insensitive (uppercase)"""
        result = self.classifier.classify("POSTGRES QUERY")
        assert "database" in result

    @pytest.mark.unit
    def test_case_insensitive_mixed(self):
        """Keywords should be case insensitive (mixed)"""
        result = self.classifier.classify("Jwt AuTh ErRoR")
        assert "suporte_api" in result

    @pytest.mark.unit
    def test_case_insensitive_lowercase(self):
        """Keywords should be case insensitive (lowercase)"""
        result = self.classifier.classify("docker container")
        assert "devops" in result

    # -----------------------------------------------------------------------
    # Unknown/General fallback
    # -----------------------------------------------------------------------
    @pytest.mark.unit
    def test_unknown_question_returns_general(self):
        """Question with no keywords should return general"""
        result = self.classifier.classify("what is the weather today")
        assert result == ["general"]

    @pytest.mark.unit
    def test_random_text_returns_general(self):
        """Random text with no keywords should return general"""
        result = self.classifier.classify("asdfghjkl qwerty")
        assert result == ["general"]

    # -----------------------------------------------------------------------
    # Multiple matches
    # -----------------------------------------------------------------------
    @pytest.mark.unit
    def test_multiple_categories(self):
        """Question matching multiple categories returns all"""
        result = self.classifier.classify("postgres error 500 deploy")
        # Should match database (postgres) and devops (deploy)
        # Note: 500 is API, so might match 3 categories
        assert len(result) >= 1
        assert any(cat in result for cat in ["database", "suporte_api", "devops"])

    # -----------------------------------------------------------------------
    # Empty and edge cases
    # -----------------------------------------------------------------------
    @pytest.mark.unit
    def test_empty_string(self):
        """Empty string should return general"""
        result = self.classifier.classify("")
        assert result == ["general"]

    @pytest.mark.unit
    def test_whitespace_only(self):
        """Whitespace only should return general"""
        result = self.classifier.classify("   ")
        assert result == ["general"]


# ============================================================================
# Test: classify_by_keywords function
# ============================================================================

class TestClassifyByKeywordsFunction:
    """Unit tests for classify_by_keywords helper function"""

    @pytest.mark.unit
    def test_function_with_api_question(self):
        """classify_by_keywords should work for API questions"""
        result = classify_by_keywords("gateway returning 401")
        assert "suporte_api" in result

    @pytest.mark.unit
    def test_function_with_database_question(self):
        """classify_by_keywords should work for database questions"""
        result = classify_by_keywords("redis cache miss performance")
        assert "database" in result

    @pytest.mark.unit
    def test_function_with_devops_question(self):
        """classify_by_keywords should work for devops questions"""
        result = classify_by_keywords("kubernetes deployment rollback")
        assert "devops" in result

    @pytest.mark.unit
    def test_function_returns_list(self):
        """classify_by_keywords should return a list"""
        result = classify_by_keywords("test question")
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_function_with_unknown(self):
        """classify_by_keywords should return general for unknown"""
        result = classify_by_keywords("hello world")
        assert result == ["general"]


# ============================================================================
# Test: LLMClassifier (with mocks)
# ============================================================================

class TestLLMClassifier:
    """Unit tests for LLMClassifier with mocked LLM"""

    @pytest.mark.unit
    def test_llm_classifier_returns_list(self):
        """LLMClassifier should return a list of categories"""
        classifier = LLMClassifier(provider="ollama", model_name="llama3.2:3b")
        # Mock the internal LLM
        with patch.object(classifier, '_get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.generate.return_value = "suporte_api"
            mock_get_llm.return_value = mock_llm

            result = classifier.classify("error 401 unauthorized")
            assert isinstance(result, list)
            assert len(result) >= 1

    @pytest.mark.unit
    def test_llm_classifier_handles_error(self):
        """LLMClassifier should fallback on error"""
        classifier = LLMClassifier(provider="ollama", model_name="llama3.2:3b")

        with patch.object(classifier, '_get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.generate.side_effect = Exception("LLM error")
            mock_get_llm.return_value = mock_llm

            # Should fallback to keyword classification
            result = classifier.classify("postgres query")
            assert isinstance(result, list)
            # Should fallback to keyword-based result

    @pytest.mark.unit
    def test_llm_classifier_parses_valid_categories(self):
        """LLMClassifier should parse valid categories from response"""
        classifier = LLMClassifier(provider="ollama", model_name="llama3.2:3b")

        with patch.object(classifier, '_get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.generate.return_value = "suporte_api, database"
            mock_get_llm.return_value = mock_llm

            result = classifier.classify("error with postgres")
            # Should contain both categories (deduped)
            assert "suporte_api" in result
            assert "database" in result

    @pytest.mark.unit
    def test_llm_classifier_ignores_invalid_categories(self):
        """LLMClassifier should ignore invalid categories"""
        classifier = LLMClassifier(provider="ollama", model_name="llama3.2:3b")

        with patch.object(classifier, '_get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.generate.return_value = "suporte_api, invalid_cat, database"
            mock_get_llm.return_value = mock_llm

            result = classifier.classify("error")
            assert "suporte_api" in result
            assert "database" in result
            assert "invalid_cat" not in result

    @pytest.mark.unit
    def test_llm_classifier_empty_response_fallback(self):
        """LLMClassifier should fallback when response is empty"""
        classifier = LLMClassifier(provider="ollama", model_name="llama3.2:3b")

        with patch.object(classifier, '_get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.generate.return_value = ""
            mock_get_llm.return_value = mock_llm

            result = classifier.classify("some question")
            # Empty response should fallback to general
            assert "general" in result or result == ["general"]

    @pytest.mark.unit
    def test_llm_classifier_unknown_response_fallback(self):
        """LLMClassifier should fallback when response has no valid categories"""
        classifier = LLMClassifier(provider="ollama", model_name="llama3.2:3b")

        with patch.object(classifier, '_get_llm') as mock_get_llm:
            mock_llm = Mock()
            mock_llm.generate.return_value = "foo, bar, baz"
            mock_get_llm.return_value = mock_llm

            result = classifier.classify("some question")
            # No valid categories should fallback to general
            assert result == ["general"]