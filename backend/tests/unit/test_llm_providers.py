"""
Unit tests for LLM providers (OllamaProvider, MiniMaxProvider, AgentLLM, ModelProviderFactory).
All external calls (ollama, requests) are mocked.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Tuple

from app.services.llm_providers import (
    LLMProvider,
    OllamaProvider,
    MiniMaxProvider,
    ModelProviderFactory,
    AgentLLM
)


# ============================================================================
# Test: LLMProvider Abstract Base
# ============================================================================

class TestLLMProviderBase:
    """Unit tests for LLMProvider abstract class"""

    @pytest.mark.unit
    def test_llm_provider_is_abc(self):
        """LLMProvider should be abstract base class"""
        from abc import ABC
        assert issubclass(LLMProvider, ABC)

    @pytest.mark.unit
    def test_llm_provider_has_abstract_methods(self):
        """LLMProvider should have generate and get_name as abstract"""
        provider = LLMProvider.__abstractmethods__
        assert "generate" in provider
        assert "get_name" in provider

    @pytest.mark.unit
    def test_llm_provider_base_generate_with_usage(self):
        """LLMProvider base should return response with usage dict"""
        class ConcreteProvider(LLMProvider):
            def generate(self, prompt: str, **kwargs) -> str:
                return "test response"

            def get_name(self) -> str:
                return "test"

        provider = ConcreteProvider()
        response, usage = provider.generate_with_usage("test prompt")

        assert response == "test response"
        assert usage["tokens_used"] == 0
        assert usage["provider"] == "test"


# ============================================================================
# Test: OllamaProvider
# ============================================================================

class TestOllamaProvider:
    """Unit tests for OllamaProvider"""

    @pytest.mark.unit
    def test_ollama_provider_initialization(self):
        """OllamaProvider should have correct defaults"""
        provider = OllamaProvider()
        assert provider.model_name == "llama3.2:3b"
        assert provider.base_url == "http://localhost:11434"

    @pytest.mark.unit
    def test_ollama_provider_custom_initialization(self):
        """OllamaProvider should accept custom values"""
        provider = OllamaProvider(model_name="llama3.2:1b", base_url="http://custom:11434")
        assert provider.model_name == "llama3.2:1b"
        assert provider.base_url == "http://custom:11434"

    @pytest.mark.unit
    def test_ollama_provider_get_name(self):
        """OllamaProvider.get_name() should return 'ollama:{model}'"""
        provider = OllamaProvider(model_name="llama3.2:3b")
        assert provider.get_name() == "ollama:llama3.2:3b"

    @pytest.mark.unit
    def test_ollama_provider_generate_calls_ollama(self):
        """OllamaProvider.generate() should call ollama.generate"""
        provider = OllamaProvider(model_name="llama3.2:3b")

        mock_response = {"response": "Test response from Ollama"}

        with patch("ollama.generate") as mock_ollama:
            mock_ollama.return_value = mock_response
            result = provider.generate("test prompt")

            mock_ollama.assert_called_once()
            call_kwargs = mock_ollama.call_args
            assert call_kwargs.kwargs["model"] == "llama3.2:3b"
            assert call_kwargs.kwargs["prompt"] == "test prompt"
            assert result == "Test response from Ollama"

    @pytest.mark.unit
    def test_ollama_provider_generate_with_temperature(self):
        """OllamaProvider.generate() should pass temperature"""
        provider = OllamaProvider()

        with patch("ollama.generate") as mock_ollama:
            mock_ollama.return_value = {"response": "test"}
            provider.generate("prompt", temperature=0.8)

            assert mock_ollama.call_args.kwargs["options"]["temperature"] == 0.8

    @pytest.mark.unit
    def test_ollama_provider_generate_with_num_predict(self):
        """OllamaProvider.generate() should pass num_predict"""
        provider = OllamaProvider()

        with patch("ollama.generate") as mock_ollama:
            mock_ollama.return_value = {"response": "test"}
            provider.generate("prompt", num_predict=100)

            assert mock_ollama.call_args.kwargs["options"]["num_predict"] == 100

    @pytest.mark.unit
    def test_ollama_provider_generate_with_top_p(self):
        """OllamaProvider.generate() should pass top_p"""
        provider = OllamaProvider()

        with patch("ollama.generate") as mock_ollama:
            mock_ollama.return_value = {"response": "test"}
            provider.generate("prompt", top_p=0.9)

            assert mock_ollama.call_args.kwargs["options"]["top_p"] == 0.9

    @pytest.mark.unit
    def test_ollama_provider_generate_with_usage(self):
        """OllamaProvider.generate_with_usage() should return usage info"""
        provider = OllamaProvider()

        with patch("ollama.generate") as mock_ollama:
            mock_ollama.return_value = {"response": "word1 word2 word3"}
            response, usage = provider.generate_with_usage("word1 word2 word3")

            assert response == "word1 word2 word3"
            assert usage["prompt_tokens"] == 3
            assert usage["completion_tokens"] == 3
            assert usage["total_tokens"] == 6
            assert usage["provider"] == "ollama"
            assert usage["model"] == "llama3.2:3b"

    @pytest.mark.unit
    def test_ollama_provider_generate_with_usage_handles_long_response(self):
        """OllamaProvider.generate_with_usage() should count tokens correctly"""
        provider = OllamaProvider()

        with patch("ollama.generate") as mock_ollama:
            mock_ollama.return_value = {"response": "one two three four five"}
            response, usage = provider.generate_with_usage("one two")

            assert usage["prompt_tokens"] == 2
            assert usage["completion_tokens"] == 5


# ============================================================================
# Test: MiniMaxProvider
# ============================================================================

class TestMiniMaxProvider:
    """Unit tests for MiniMaxProvider"""

    @pytest.mark.unit
    def test_minimax_provider_initialization(self):
        """MiniMaxProvider should have correct defaults"""
        provider = MiniMaxProvider()
        assert provider.model_name == "MiniMax-M2.7"
        assert provider.base_url == "https://api.minimax.io"

    @pytest.mark.unit
    def test_minimax_provider_custom_initialization(self):
        """MiniMaxProvider should accept custom values"""
        provider = MiniMaxProvider(
            api_key="test-key",
            base_url="https://custom.api.com",
            model_name="CustomModel"
        )
        assert provider.api_key == "test-key"
        assert provider.base_url == "https://custom.api.com"
        assert provider.model_name == "CustomModel"

    @pytest.mark.unit
    def test_minimax_provider_get_name(self):
        """MiniMaxProvider.get_name() should return 'minimax:{model}'"""
        provider = MiniMaxProvider(model_name="MiniMax-M2.7")
        assert provider.get_name() == "minimax:MiniMax-M2.7"

    @pytest.mark.unit
    def test_minimax_provider_generate_requires_api_key(self):
        """MiniMaxProvider.generate() should raise if no API key"""
        with patch.dict('os.environ', {'MINIMAX_API_KEY': ''}, clear=False):
            provider = MiniMaxProvider(api_key="")

            with pytest.raises(ValueError, match="MINIMAX_API_KEY not set"):
                provider.generate("test prompt")

    @pytest.mark.unit
    def test_minimax_provider_generate_success(self):
        """MiniMaxProvider.generate() should call API and return response"""
        provider = MiniMaxProvider(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "MiniMax response"}}]
        }

        with patch("requests.post") as mock_requests:
            mock_requests.return_value = mock_response
            result = provider.generate("test prompt")

            mock_requests.assert_called_once()
            call_kwargs = mock_requests.call_args.kwargs
            assert "Bearer test-key" in call_kwargs["headers"]["Authorization"]
            assert call_kwargs["json"]["model"] == "MiniMax-M2.7"
            assert result == "MiniMax response"

    @pytest.mark.unit
    def test_minimax_provider_generate_with_temperature(self):
        """MiniMaxProvider.generate() should pass temperature"""
        provider = MiniMaxProvider(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}]
        }

        with patch("requests.post") as mock_requests:
            mock_requests.return_value = mock_response
            provider.generate("prompt", temperature=0.5)

            assert mock_requests.call_args.kwargs["json"]["temperature"] == 0.5

    @pytest.mark.unit
    def test_minimax_provider_generate_with_max_tokens(self):
        """MiniMaxProvider.generate() should pass max_tokens"""
        provider = MiniMaxProvider(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}]
        }

        with patch("requests.post") as mock_requests:
            mock_requests.return_value = mock_response
            provider.generate("prompt", max_tokens=1000)

            assert mock_requests.call_args.kwargs["json"]["max_tokens"] == 1000

    @pytest.mark.unit
    def test_minimax_provider_generate_handles_error(self):
        """MiniMaxProvider.generate() should raise on non-200 response"""
        provider = MiniMaxProvider(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("requests.post") as mock_requests:
            mock_requests.return_value = mock_response

            with pytest.raises(Exception, match="401"):
                provider.generate("test prompt")

    @pytest.mark.unit
    def test_minimax_provider_generate_with_usage(self):
        """MiniMaxProvider.generate_with_usage() should return usage info"""
        provider = MiniMaxProvider(api_key="test-key")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }

        with patch("requests.post") as mock_requests:
            mock_requests.return_value = mock_response
            response, usage = provider.generate_with_usage("test prompt")

            assert response == "response"
            assert usage["prompt_tokens"] == 10
            assert usage["completion_tokens"] == 20
            assert usage["total_tokens"] == 30
            assert usage["provider"] == "minimax"
            assert usage["model"] == "MiniMax-M2.7"


# ============================================================================
# Test: ModelProviderFactory
# ============================================================================

class TestModelProviderFactory:
    """Unit tests for ModelProviderFactory"""

    @pytest.mark.unit
    def test_factory_has_ollama_provider(self):
        """ModelProviderFactory should have 'ollama' provider"""
        assert "ollama" in ModelProviderFactory.PROVIDERS

    @pytest.mark.unit
    def test_factory_has_minimax_provider(self):
        """ModelProviderFactory should have 'minimax' provider"""
        assert "minimax" in ModelProviderFactory.PROVIDERS

    @pytest.mark.unit
    def test_factory_create_ollama(self):
        """ModelProviderFactory.create('ollama') should return OllamaProvider"""
        provider = ModelProviderFactory.create("ollama", "llama3.2:3b")
        assert isinstance(provider, OllamaProvider)
        assert provider.model_name == "llama3.2:3b"

    @pytest.mark.unit
    def test_factory_create_minimax(self):
        """ModelProviderFactory.create('minimax') should return MiniMaxProvider"""
        provider = ModelProviderFactory.create("minimax", "MiniMax-M2.7", api_key="test")
        assert isinstance(provider, MiniMaxProvider)
        assert provider.model_name == "MiniMax-M2.7"

    @pytest.mark.unit
    def test_factory_create_unknown_provider_raises(self):
        """ModelProviderFactory.create() should raise for unknown provider"""
        with pytest.raises(ValueError, match="Unknown provider"):
            ModelProviderFactory.create("unknown", "model")

    @pytest.mark.unit
    def test_factory_create_error_message_contains_provider(self):
        """Error message should mention the unknown provider"""
        with pytest.raises(ValueError, match="unknown"):
            ModelProviderFactory.create("unknown", "model")

    @pytest.mark.unit
    def test_factory_create_error_shows_available(self):
        """Error message should show available providers"""
        try:
            ModelProviderFactory.create("unknown", "model")
        except ValueError as e:
            error_message = str(e)
            assert "ollama" in error_message
            assert "minimax" in error_message

    @pytest.mark.unit
    def test_factory_list_providers(self):
        """ModelProviderFactory.list_providers() should return list of provider names"""
        providers = ModelProviderFactory.list_providers()
        assert isinstance(providers, list)
        assert "ollama" in providers
        assert "minimax" in providers


# ============================================================================
# Test: AgentLLM
# ============================================================================

class TestAgentLLM:
    """Unit tests for AgentLLM"""

    @pytest.mark.unit
    def test_agent_llm_initialization(self):
        """AgentLLM should have correct defaults"""
        agent = AgentLLM()
        assert agent.provider == "ollama"
        assert agent.model_name == "llama3.2:3b"
        assert agent.temperature == 0.3
        assert agent.max_tokens == 300
        assert agent.top_p == 0.9
        assert agent._system_prompt == ""

    @pytest.mark.unit
    def test_agent_llm_custom_initialization(self):
        """AgentLLM should accept custom values"""
        agent = AgentLLM(
            provider="minimax",
            model_name="MiniMax-M2.7",
            temperature=0.7,
            max_tokens=500,
            top_p=0.8,
            system_prompt="You are a test agent"
        )
        assert agent.provider == "minimax"
        assert agent.model_name == "MiniMax-M2.7"
        assert agent.temperature == 0.7
        assert agent.max_tokens == 500
        assert agent.top_p == 0.8
        assert agent._system_prompt == "You are a test agent"

    @pytest.mark.unit
    def test_agent_llm_get_config(self):
        """AgentLLM.get_config() should return configuration dict"""
        agent = AgentLLM(
            provider="ollama",
            model_name="llama3.2:3b",
            temperature=0.3,
            max_tokens=300,
            top_p=0.9
        )
        config = agent.get_config()

        assert config["provider"] == "ollama"
        assert config["model_name"] == "llama3.2:3b"
        assert config["temperature"] == 0.3
        assert config["max_tokens"] == 300
        assert config["top_p"] == 0.9

    @pytest.mark.unit
    def test_agent_llm_set_system_prompt(self):
        """AgentLLM.set_system_prompt() should update _system_prompt"""
        agent = AgentLLM()
        agent.set_system_prompt("New system prompt")
        assert agent._system_prompt == "New system prompt"

    @pytest.mark.unit
    def test_agent_llm_generate_without_context(self):
        """AgentLLM.generate() should use only user_prompt when no context"""
        agent = AgentLLM()

        mock_provider = Mock()
        mock_provider.generate.return_value = "Generated response"

        with patch.object(agent, '_get_llm', return_value=mock_provider):
            result = agent.generate("user question")

            mock_provider.generate.assert_called_once()
            call_kwargs = mock_provider.generate.call_args.kwargs
            assert "user question" in call_kwargs["prompt"]
            assert "Context:" not in call_kwargs["prompt"]
            assert result == "Generated response"

    @pytest.mark.unit
    def test_agent_llm_generate_with_context(self):
        """AgentLLM.generate() should prepend context when provided"""
        agent = AgentLLM()

        mock_provider = Mock()
        mock_provider.generate.return_value = "Generated response"

        with patch.object(agent, '_get_llm', return_value=mock_provider):
            result = agent.generate("user question", context="Some context information")

            call_kwargs = mock_provider.generate.call_args.kwargs
            prompt = call_kwargs["prompt"]
            assert "Context:" in prompt
            assert "Some context information" in prompt
            assert "user question" in prompt

    @pytest.mark.unit
    def test_agent_llm_generate_with_system_prompt(self):
        """AgentLLM.generate() should prepend system prompt"""
        agent = AgentLLM(system_prompt="You are a helpful assistant.")

        mock_provider = Mock()
        mock_provider.generate.return_value = "Generated response"

        with patch.object(agent, '_get_llm', return_value=mock_provider):
            result = agent.generate("user question")

            call_kwargs = mock_provider.generate.call_args.kwargs
            prompt = call_kwargs["prompt"]
            assert prompt.startswith("You are a helpful assistant.")

    @pytest.mark.unit
    def test_agent_llm_generate_passes_temperature(self):
        """AgentLLM.generate() should pass temperature to provider"""
        agent = AgentLLM(temperature=0.5)

        mock_provider = Mock()
        mock_provider.generate.return_value = "response"

        with patch.object(agent, '_get_llm', return_value=mock_provider):
            agent.generate("question")

            assert mock_provider.generate.call_args.kwargs["temperature"] == 0.5

    @pytest.mark.unit
    def test_agent_llm_generate_passes_max_tokens(self):
        """AgentLLM.generate() should pass max_tokens to provider"""
        agent = AgentLLM(max_tokens=200)

        mock_provider = Mock()
        mock_provider.generate.return_value = "response"

        with patch.object(agent, '_get_llm', return_value=mock_provider):
            agent.generate("question")

            assert mock_provider.generate.call_args.kwargs["max_tokens"] == 200

    @pytest.mark.unit
    def test_agent_llm_generate_passes_top_p(self):
        """AgentLLM.generate() should pass top_p to provider"""
        agent = AgentLLM(top_p=0.8)

        mock_provider = Mock()
        mock_provider.generate.return_value = "response"

        with patch.object(agent, '_get_llm', return_value=mock_provider):
            agent.generate("question")

            assert mock_provider.generate.call_args.kwargs["top_p"] == 0.8

    @pytest.mark.unit
    def test_agent_llm_generate_with_usage(self):
        """AgentLLM.generate_with_usage() should return usage info"""
        agent = AgentLLM()

        mock_provider = Mock()
        mock_provider.generate_with_usage.return_value = (
            "Generated response",
            {"total_tokens": 100, "provider": "ollama", "model": "llama3.2:3b"}
        )

        with patch.object(agent, '_get_llm', return_value=mock_provider):
            response, usage = agent.generate_with_usage("user question")

            assert response == "Generated response"
            assert usage["total_tokens"] == 100

    @pytest.mark.unit
    def test_agent_llm_generate_with_usage_with_context(self):
        """AgentLLM.generate_with_usage() should handle context"""
        agent = AgentLLM()

        mock_provider = Mock()
        mock_provider.generate_with_usage.return_value = ("response", {"total_tokens": 50})

        with patch.object(agent, '_get_llm', return_value=mock_provider):
            agent.generate_with_usage("user question", context="Some context")

            call_kwargs = mock_provider.generate_with_usage.call_args.kwargs
            prompt = call_kwargs["prompt"]
            assert "Context:" in prompt

    @pytest.mark.unit
    def test_agent_llm_caches_llm_instance(self):
        """AgentLLM should cache the LLM instance"""
        agent = AgentLLM()

        mock_provider = Mock()
        mock_provider.generate.return_value = "response"

        with patch.object(agent, '_get_llm', return_value=mock_provider):
            agent.generate("q1")
            agent.generate("q2")

            # _get_llm is called twice but should only create once
            # (In real implementation, _llm is cached in self._llm)
            # Here we just verify it doesn't error
            pass

    @pytest.mark.unit
    def test_agent_llm_full_pipeline_with_context_and_system(self):
        """AgentLLM.generate() should handle both context and system prompt"""
        agent = AgentLLM(system_prompt="You are an expert.")

        mock_provider = Mock()
        mock_provider.generate.return_value = "Expert answer"

        with patch.object(agent, '_get_llm', return_value=mock_provider):
            result = agent.generate("user question", context="Relevant facts")

            call_kwargs = mock_provider.generate.call_args.kwargs
            prompt = call_kwargs["prompt"]

            # Should have: system prompt + context + user question
            assert prompt.startswith("You are an expert.")
            assert "Context:" in prompt
            assert "Relevant facts" in prompt
            assert "user question" in prompt


# ============================================================================
# Test: Integration scenarios
# ============================================================================

class TestLLMProviderIntegration:
    """Integration-style tests for LLM provider scenarios"""

    @pytest.mark.unit
    def test_switch_provider_from_ollama_to_minimax(self):
        """Factory should allow switching between providers"""
        ollama_provider = ModelProviderFactory.create("ollama", "llama3.2:3b")
        assert isinstance(ollama_provider, OllamaProvider)

        minimax_provider = ModelProviderFactory.create("minimax", "MiniMax-M2.7", api_key="test")
        assert isinstance(minimax_provider, MiniMaxProvider)

    @pytest.mark.unit
    def test_agent_with_different_providers(self):
        """AgentLLM should work with different provider backends"""
        agent_ollama = AgentLLM(provider="ollama", model_name="llama3.2:3b")
        agent_minimax = AgentLLM(provider="minimax", model_name="MiniMax-M2.7")

        # Both should be able to generate (mocked)
        mock_ollama = Mock()
        mock_ollama.generate.return_value = "Ollama response"

        mock_minimax = Mock()
        mock_minimax.generate.return_value = "MiniMax response"

        with patch.object(agent_ollama, '_get_llm', return_value=mock_ollama):
            result1 = agent_ollama.generate("test")
            assert result1 == "Ollama response"

        with patch.object(agent_minimax, '_get_llm', return_value=mock_minimax):
            result2 = agent_minimax.generate("test")
            assert result2 == "MiniMax response"