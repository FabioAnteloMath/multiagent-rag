from abc import ABC, abstractmethod
from typing import Optional, Tuple
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return provider name."""
        pass

    def generate_with_usage(self, prompt: str, **kwargs) -> Tuple[str, dict]:
        """Generate response and return usage info. Returns (response, usage_dict)."""
        response = self.generate(prompt, **kwargs)
        return response, {"tokens_used": 0, "provider": self.get_name()}


class OllamaProvider(LLMProvider):
    """Ollama local provider."""

    def __init__(self, model_name: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url

    def generate(self, prompt: str, **kwargs) -> str:
        import ollama
        options = {}
        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]
        if "num_predict" in kwargs:
            options["num_predict"] = kwargs["num_predict"]
        if "top_p" in kwargs:
            options["top_p"] = kwargs["top_p"]

        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            options=options if options else None
        )
        return response["response"]

    def generate_with_usage(self, prompt: str, **kwargs) -> Tuple[str, dict]:
        import ollama
        options = {}
        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]
        if "num_predict" in kwargs:
            options["num_predict"] = kwargs["num_predict"]
        if "top_p" in kwargs:
            options["top_p"] = kwargs["top_p"]

        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            options=options if options else None
        )

        prompt_tokens = len(prompt.split())
        completion_tokens = len(response["response"].split())
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "provider": "ollama",
            "model": self.model_name
        }
        return response["response"], usage

    def get_name(self) -> str:
        return f"ollama:{self.model_name}"


class MiniMaxProvider(LLMProvider):
    """MiniMax cloud provider via TokenPlan or direct API."""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://api.minimax.io",
        model_name: str = "MiniMax-M2.7"
    ):
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY", "")
        self.base_url = base_url
        self.model_name = model_name

    def generate(self, prompt: str, **kwargs) -> str:
        import requests

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set. Please configure your API key.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 500)
        }

        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"MiniMax API error: {response.status_code} - {response.text}")

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def generate_with_usage(self, prompt: str, **kwargs) -> Tuple[str, dict]:
        import requests

        if not self.api_key:
            raise ValueError("MINIMAX_API_KEY not set. Please configure your API key.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 500)
        }

        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"MiniMax API error: {response.status_code} - {response.text}")

        result = response.json()
        usage = result.get("usage", {})
        usage["provider"] = "minimax"
        usage["model"] = self.model_name
        return result["choices"][0]["message"]["content"], usage

    def get_name(self) -> str:
        return f"minimax:{self.model_name}"


class ModelProviderFactory:
    """Factory to create LLM providers based on configuration."""

    PROVIDERS = {
        "ollama": OllamaProvider,
        "minimax": MiniMaxProvider
    }

    @staticmethod
    def create(provider: str, model_name: str, **kwargs) -> LLMProvider:
        if provider not in ModelProviderFactory.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(ModelProviderFactory.PROVIDERS.keys())}")

        provider_class = ModelProviderFactory.PROVIDERS[provider]
        return provider_class(model_name=model_name, **kwargs)

    @staticmethod
    def list_providers() -> list[str]:
        return list(ModelProviderFactory.PROVIDERS.keys())


class AgentLLM:
    """Configurable LLM for agents with full customization."""

    def __init__(
        self,
        provider: str = "ollama",
        model_name: str = "llama3.2:3b",
        temperature: float = 0.3,
        max_tokens: int = 300,
        top_p: float = 0.9,
        system_prompt: str = ""
    ):
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self._system_prompt = system_prompt
        self._llm = None

    def _get_llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = ModelProviderFactory.create(
                self.provider,
                self.model_name
            )
        return self._llm

    def generate(self, user_prompt: str, context: str = "") -> str:
        """Generate response with optional context."""
        full_prompt = user_prompt
        if context:
            full_prompt = f"Context:\n{context}\n\nUser: {user_prompt}"
        if self._system_prompt:
            full_prompt = f"{self._system_prompt}\n\n{full_prompt}"

        llm = self._get_llm()
        return llm.generate(
            prompt=full_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p
        )

    def generate_with_usage(self, user_prompt: str, context: str = "") -> Tuple[str, dict]:
        """Generate response with usage tracking."""
        full_prompt = user_prompt
        if context:
            full_prompt = f"Context:\n{context}\n\nUser: {user_prompt}"
        if self._system_prompt:
            full_prompt = f"{self._system_prompt}\n\n{full_prompt}"

        llm = self._get_llm()
        return llm.generate_with_usage(
            prompt=full_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p
        )

    def set_system_prompt(self, prompt: str):
        self._system_prompt = prompt

    def get_config(self) -> dict:
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p
        }