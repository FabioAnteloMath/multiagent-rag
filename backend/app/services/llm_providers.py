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
            "max_tokens": kwargs.get("max_tokens", 1000)
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
        content = result["choices"][0]["message"]["content"]

        import re
        content = re.sub(r'<[^>]+>', '', content).strip()
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        content = re.sub(r'^(<think>|<\/think>)+', '', content).strip()
        content = re.sub(r'($(<think>|<\/think>))+$', '', content).strip()

        return content

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
        content = result["choices"][0]["message"]["content"]

        import re
        content = re.sub(r'<[^>]+>', '', content).strip()
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        content = re.sub(r'^(<think>|<\/think>)+', '', content).strip()
        content = re.sub(r'($(<think>|<\/think>))+$', '', content).strip()
        # Strip chain-of-thought preamble (e.g. "The user is asking about X. Let me explain...")
        # even if the system prompt said not to. Safety net for MiniMax-M2.7's
        # trained thinking-aloud behavior.
        content = strip_thinking_preamble(content)

        usage = result.get("usage", {})
        usage["provider"] = "minimax"
        usage["model"] = self.model_name
        return content, usage

    def get_name(self) -> str:
        return f"minimax:{self.model_name}"


class GroqProvider(LLMProvider):
    """Groq cloud provider - OpenAI-compatible API, free tier with fast inference."""

    PRICING = {
        "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},  # per 1M tokens
        "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
        "mixtral-8x7b-32768": {"input": 0.27, "output": 0.27},
        "gemma2-9b-it": {"input": 0.20, "output": 0.20},
    }

    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://api.groq.com/openai/v1",
        model_name: str = "llama-3.1-8b-instant",
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.base_url = base_url
        self.model_name = model_name

    def _check_key(self):
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set. Free key at https://console.groq.com")

    def _build_payload(self, prompt, **kwargs):
        return {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.3),
            "max_tokens": kwargs.get("max_tokens", 2000),
            "top_p": kwargs.get("top_p", 0.9),
        }

    def _clean(self, content: str) -> str:
        import re
        content = re.sub(r"<[^>]+>", "", content).strip()
        return content

    def generate(self, prompt: str, **kwargs) -> str:
        import requests
        self._check_key()
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=self._build_payload(prompt, **kwargs),
            timeout=60,
        )
        if response.status_code != 200:
            raise Exception(f"Groq API error: {response.status_code} - {response.text}")
        return self._clean(response.json()["choices"][0]["message"]["content"])

    def generate_with_usage(self, prompt: str, **kwargs) -> Tuple[str, dict]:
        import requests
        self._check_key()
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=self._build_payload(prompt, **kwargs),
            timeout=60,
        )
        if response.status_code != 200:
            raise Exception(f"Groq API error: {response.status_code} - {response.text}")
        result = response.json()
        content = self._clean(result["choices"][0]["message"]["content"])
        usage = result.get("usage", {})
        usage["provider"] = "groq"
        usage["model"] = self.model_name
        return content, usage

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = self.PRICING.get(self.model_name, {"input": 0.0, "output": 0.0})
        return (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000

    def get_name(self) -> str:
        return f"groq:{self.model_name}"


class GeminiProvider(LLMProvider):
    """Google Gemini provider - REST API, free tier with rate limits."""

    PRICING = {
        "gemini-1.5-flash": {"input": 0.0, "output": 0.0},  # free tier
        "gemini-1.5-pro": {"input": 0.0, "output": 0.0},    # free tier (rate limited)
        "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},
    }

    def __init__(
        self,
        api_key: str = None,
        model_name: str = "gemini-1.5-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name

    def _check_key(self):
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set. Free key at https://aistudio.google.com")

    def _url(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"

    def _build_payload(self, prompt, **kwargs):
        return {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.3),
                "maxOutputTokens": kwargs.get("max_tokens", 2000),
                "topP": kwargs.get("top_p", 0.9),
            },
        }

    def _clean(self, content: str) -> str:
        import re
        return re.sub(r"<[^>]+>", "", content).strip()

    def generate(self, prompt: str, **kwargs) -> str:
        import requests
        self._check_key()
        response = requests.post(
            f"{self._url()}?key={self.api_key}",
            json=self._build_payload(prompt, **kwargs),
            timeout=60,
        )
        if response.status_code != 200:
            raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
        result = response.json()
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        return self._clean(content)

    def generate_with_usage(self, prompt: str, **kwargs) -> Tuple[str, dict]:
        import requests
        self._check_key()
        response = requests.post(
            f"{self._url()}?key={self.api_key}",
            json=self._build_payload(prompt, **kwargs),
            timeout=60,
        )
        if response.status_code != 200:
            raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
        result = response.json()
        content = self._clean(result["candidates"][0]["content"]["parts"][0]["text"])
        usage_meta = result.get("usageMetadata", {})
        usage = {
            "prompt_tokens": usage_meta.get("promptTokenCount", 0),
            "completion_tokens": usage_meta.get("candidatesTokenCount", 0),
            "total_tokens": usage_meta.get("totalTokenCount", 0),
            "provider": "gemini",
            "model": self.model_name,
        }
        return content, usage

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = self.PRICING.get(self.model_name, {"input": 0.0, "output": 0.0})
        return (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000

    def get_name(self) -> str:
        return f"gemini:{self.model_name}"


class ModelProviderFactory:
    """Factory to create LLM providers based on configuration."""

    PROVIDERS = {
        "ollama": OllamaProvider,
        "minimax": MiniMaxProvider,
        "groq": GroqProvider,
        "gemini": GeminiProvider,
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
        max_tokens: int = 2000,
        top_p: float = 0.9,
        system_prompt: str = "",
        # Optional callback used to wrap a single LLM call in a
        # ProviderRouter. If set, `generate_with_usage` delegates the
        # actual call to the router (which provides fallback + quota
        # tracking). If None, the original direct-call behaviour is
        # preserved (used in unit tests that don't want a DB session).
        router_callable=None,
    ):
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self._system_prompt = system_prompt
        self._llm = None
        self._router_callable = router_callable

    def _get_llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = ModelProviderFactory.create(
                self.provider,
                self.model_name
            )
        return self._llm

    def _build_full_prompt(self, user_prompt: str, context: str) -> str:
        full_prompt = user_prompt
        if context:
            full_prompt = f"Context:\n{context}\n\nUser: {user_prompt}"
        if self._system_prompt:
            full_prompt = f"{self._system_prompt}\n\n{full_prompt}"
        return full_prompt

    def generate(self, user_prompt: str, context: str = "") -> str:
        """Generate response with optional context."""
        full_prompt = self._build_full_prompt(user_prompt, context)

        if self._router_callable is not None:
            answer, _ = self._router_callable(
                preferred=self.provider,
                model=self.model_name,
                prompt=full_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
            )
            return answer

        llm = self._get_llm()
        return llm.generate(
            prompt=full_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            top_p=self.top_p
        )

    def generate_with_usage(self, user_prompt: str, context: str = "") -> Tuple[str, dict]:
        """Generate response with usage tracking.

        If `router_callable` is set, the call goes through the
        ProviderRouter (quota + fallback). Otherwise it calls the
        configured provider directly (legacy / test path).
        """
        full_prompt = self._build_full_prompt(user_prompt, context)

        if self._router_callable is not None:
            return self._router_callable(
                preferred=self.provider,
                model=self.model_name,
                prompt=full_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
            )

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


# ---------------------------------------------------------------------------
# Preamble stripping - safety net for chain-of-thought leakage
# ---------------------------------------------------------------------------

_PREAMBLE_PATTERNS = [
    r"^The user is asking (?:me )?(?:about|to|for|whether|why|how|what|if)[^.]*\.\s*",
    r"^The user wants (?:me )?(?:to know|to|about)[^.]*\.\s*",
    r"^They (?:want|wanted) (?:me )?to (?:know|see|find|understand)[^.]*\.\s*",
    r"^The user (?:asked|is asking|wants|wants to know)[^.]*\.\s*",
    r"^Let me (?:think|craft|provide|analyze|consider|examine|break|write|approach|walk through|look at|review|read)[^.]*\.\s*",
    r"^I'll (?:craft|provide|analyze|think|break|write|examine|walk through|outline|look at|review|read)[^.]*\.\s*",
    r"^I (?:will|should|can) (?:provide|analyze|explain|examine|discuss|break|outline|look at|review|read|now)[^.]*\.\s*",
    r"^Let me (?:also )?(?:see|look|check|read) [^.]*\.\s*",
    r"^Based on the (?:context|provided|question|information|what was|document)[^.]*\.\s*",
    r"^Based on (?:what's|what was) (?:provided|given|shared)[^.]*\.\s*",
    r"^According to the (?:context|provided|question|information|document) [^.]*[:.]\s*",
    r"^According to (?:what's|what was) (?:provided|given|shared)[^.]*[:.]\s*",
    r"^Sure[,!]? [^.]*\.\s*",
    r"^Okay[,!]? [^.]*\.\s*",
    r"^Absolutely[,!]? [^.]*\.\s*",
    r"^Of course[,!]? [^.]*\.\s*",
    r"^Great question[,!]? [^.]*\.\s*",
    r"^(?:First|Let me start|Let's start|To start) [^.]*\.\s*",
    r"^Looking at the (?:context|provided|question|information|document) [^.]*[:.]\s*",
    r"^In the (?:context|provided) (?:section|it is mentioned|we can|there's|we see)[^.]*[:.]\s*",
    r"^In the (?:context|provided|document)[: ]*\s*",
    r"^From the (?:context|provided|document) (?:provided|there is|there's|we can|I can|information|section)[^.]*[:.]\s*",
    r"^From the (?:context|provided)[: ]*\s*",
    r"^Given the (?:context|question|document)[^.]*\.\s*",
    r"^I can see[: ]*",
    r"^, I can see[^a-z]*",
    r"^, I can find[^a-z]*",
    r"^, I can extract[^a-z]*",
    r"^I see[: ]*",
    # Instruction echo / meta-acknowledgement
    r"^I need to (?:use|follow|provide|answer|start with)[^.]*\.\s*",
    r"^I must (?:use|follow|provide|answer|start with)[^.]*\.\s*",
    r"^I should (?:use|follow|provide|answer|start with)[^.]*\.\s*",
    r"^I will (?:use|follow|provide|answer|start with)[^.]*\.\s*",
    r"^I(?:'ll| will) (?:use|follow|provide|answer|start with)[^.]*\.\s*",
    r"^I need to use only the information[^.]*\.\s*",
    r"^I need to follow the [^.]*\.\s*",
    # Common mid-sentence artifacts after partial strip
    r"^,\s*",
]


def strip_thinking_preamble(text: str) -> str:
    """Remove chain-of-thought preamble sentences from the start of an LLM response.

    Some models (notably MiniMax-M2.7) start their output with phrases like
    'The user is asking about X. Let me explain...' even when the system prompt
    explicitly says not to. This is a safety net that strips one or more
    leading sentences matching known preamble patterns.

    If no pattern matches, returns the input unchanged.
    """
    if not text:
        return text
    import re as _re
    # Strip repeatedly in case there are multiple preamble sentences
    for _ in range(3):
        original = text
        for pattern in _PREAMBLE_PATTERNS:
            m = _re.match(pattern, text, _re.IGNORECASE | _re.DOTALL)
            if m:
                text = text[m.end():].lstrip()
                break
        if text == original:
            break
    return text