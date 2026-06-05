from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from app.services.llm_providers import AgentLLM


@dataclass
class AgentResult:
    answer: str
    sources: list[str]
    confidence: float
    agent_name: str
    category: str
    tokens_used: int = 0
    thinking: str = ""
    model_used: str = ""


class BaseAgent(ABC):
    def __init__(
        self,
        name: str,
        category: str,
        collection_name: str,
        provider: str = "minimax",
        model_name: str = "MiniMax-M2.7",
        temperature: float = 0.3,
        system_prompt: str = "",
        guidelines: str = "",
        personality: str = "",
        response_format: str = "",
        examples: str = ""
    ):
        self.name = name
        self.category = category
        self.collection_name = collection_name
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self._system_prompt = system_prompt
        self._guidelines = guidelines
        self._personality = personality
        self._response_format = response_format
        self._examples = examples
        self._vectorstore = None
        self._embeddings = None
        self._llm = None

    def _get_llm(self) -> AgentLLM:
        if self._llm is None:
            self._llm = AgentLLM(
                provider=self.provider,
                model_name=self.model_name,
                temperature=self.temperature,
                system_prompt=self._system_prompt or f"You are {self.name}, a specialist in {self.category}."
            )
        return self._llm

    @abstractmethod
    def execute(self, question: str) -> AgentResult:
        """Execute the agent's specialized task"""
        pass

    def _get_embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
            )
        return self._embeddings

    def _load_vectorstore(self):
        """Load the collection-specific vector store"""
        project_root = Path(__file__).resolve().parents[3]
        index_dir = project_root / "data" / "faiss" / self.collection_name
        index_file = index_dir / "index.faiss"

        if not index_file.exists():
            return None

        return FAISS.load_local(
            str(index_dir),
            self._get_embeddings(),
            allow_dangerous_deserialization=True,
        )

    def format_context(self, docs: list) -> str:
        """Format retrieved documents into context string"""
        if not docs:
            return "I did not find relevant context."
        return "\n\n".join([doc.page_content for doc in docs])

    def search(self, query: str, top_k: int = 4) -> list:
        """Search the vector store for relevant documents"""
        if not self._vectorstore:
            self._vectorstore = self._load_vectorstore()
        if not self._vectorstore:
            return []
        return self._vectorstore.similarity_search(query, k=top_k)

    def refresh_vectorstore(self):
        """Force reload the vector store from disk (use after index rebuild)"""
        self._vectorstore = None
        self._vectorstore = self._load_vectorstore()

    def get_system_prompt(self, question: str, context: str) -> str:
        """Generate the system prompt for this agent with full customization"""
        parts = []

        if self._system_prompt:
            parts.append(self._system_prompt)
        else:
            parts.append(f"You are {self.name}, a specialist in {self.category}.")

        parts.append("Use only information from the provided context to answer.")

        if hasattr(self, '_guidelines') and self._guidelines:
            parts.append(f"\nGuidelines:\n{self._guidelines}")

        if hasattr(self, '_personality') and self._personality:
            parts.append(f"\nPersonality: {self._personality}")

        if hasattr(self, '_response_format') and self._response_format:
            parts.append(f"\nResponse Format: {self._response_format}")

        if hasattr(self, '_examples') and self._examples:
            parts.append(f"\nExamples:\n{self._examples}")

        parts.append(f"\nContext:\n{context}")
        parts.append(f"\nQuestion: {question}")

        return "\n\n".join(parts)

    def set_guidelines(self, guidelines: str):
        self._guidelines = guidelines

    def set_personality(self, personality: str):
        self._personality = personality

    def set_response_format(self, format: str):
        self._response_format = format

    def set_examples(self, examples: str):
        self._examples = examples