from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


@dataclass
class AskResult:
    answer: str
    sources: list[str]


@dataclass
class IngestResult:
    files_indexed: int
    documents_loaded: int
    chunks_created: int
    collection_name: str
    vector_backend: str


class RagPipeline:
    """Coordinates loading, indexing and querying support documents."""

    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parents[3]
        self.docs_dir = self.project_root / "data" / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        faiss_dir = self.project_root / "data" / "faiss"
        faiss_dir.mkdir(parents=True, exist_ok=True)
        self.faiss_dir = faiss_dir.as_posix()

        self.collection_name = "support_docs"

        self.embedding_model_name = "all-MiniLM-L6-v2"
        self.ollama_model_name = "llama3.2:3b"

        self._embeddings: HuggingFaceEmbeddings | None = None
        self._vectorstore: Any | None = None

    def _to_relative_source(self, file_path: Path) -> str:
        return str(file_path.relative_to(self.project_root)).replace("\\", "/")

    def _load_documents(self) -> tuple[list[Document], int]:
        docs: list[Document] = []
        files_indexed = 0

        for file_path in self.docs_dir.rglob("*"):
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            if suffix not in {".pdf", ".md", ".txt"}:
                continue

            files_indexed += 1
            source = self._to_relative_source(file_path)

            if suffix == ".pdf":
                pdf_pages = PyPDFLoader(str(file_path)).load()
                for page in pdf_pages:
                    page.metadata["source"] = source
                docs.extend(pdf_pages)
                continue

            text_content = file_path.read_text(encoding="utf-8", errors="ignore")
            docs.append(
                Document(
                    page_content=text_content,
                    metadata={"source": source, "page": 0},
                )
            )

        return docs, files_indexed

    def _chunk_documents(
        self, documents: list[Document], chunk_size: int, chunk_overlap: int
    ) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return splitter.split_documents(documents)

    def _get_embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                model_kwargs={"device": "cpu"},
            )
        return self._embeddings

    def ingest(
        self,
        clear_existing: bool = True,
        chunk_size: int = 600,
        chunk_overlap: int = 80,
    ) -> IngestResult:
        documents, files_indexed = self._load_documents()
        if not documents:
            raise ValueError(
                "Nenhum documento encontrado em data/docs (aceitos: .pdf, .md, .txt)."
            )

        chunks = self._chunk_documents(documents, chunk_size, chunk_overlap)

        self._vectorstore = FAISS.from_documents(
            documents=chunks,
            embedding=self._get_embeddings(),
        )
        self._vectorstore.save_local(self.faiss_dir)

        return IngestResult(
            files_indexed=files_indexed,
            documents_loaded=len(documents),
            chunks_created=len(chunks),
            collection_name=self.collection_name,
            vector_backend="faiss",
        )

    def _get_vectorstore(self) -> Any:
        if self._vectorstore is not None:
            return self._vectorstore

        try:
            self._vectorstore = FAISS.load_local(
                self.faiss_dir,
                self._get_embeddings(),
                allow_dangerous_deserialization=True,
            )
            return self._vectorstore
        except Exception as exc:
            raise RuntimeError(
                "Base vetorial indisponivel. Rode /api/ingest antes de consultar."
            ) from exc

    def ask(self, question: str, top_k: int = 4) -> AskResult:
        retriever = self._get_vectorstore().as_retriever(search_kwargs={"k": top_k})
        docs = retriever.invoke(question)

        if not docs:
            return AskResult(
                answer="Nao encontrei contexto relevante para responder com seguranca.",
                sources=[],
            )

        context = "\n\n".join(doc.page_content for doc in docs)

        prompt = (
            "Voce e um copiloto de suporte tecnico. Responda em portugues de forma objetiva, "
            "usando apenas o contexto fornecido. Se faltar informacao, diga claramente.\n\n"
            f"Pergunta: {question}\n\n"
            f"Contexto:\n{context}"
        )

        try:
            response = ollama.generate(
                model=self.ollama_model_name,
                prompt=prompt,
                options={"num_predict": 300, "temperature": 0.3, "top_k": 10, "top_p": 0.9},
            )
            answer = response["response"]
        except Exception as exc:
            raise RuntimeError(
                "Falha ao gerar resposta no Ollama. Verifique se o Ollama esta ativo e o modelo baixado."
            ) from exc

        sources: list[str] = []
        for doc in docs:
            source = str(doc.metadata.get("source", "desconhecido"))
            page = doc.metadata.get("page")
            if page is None:
                sources.append(source)
                continue
            sources.append(f"{source}#page={int(page) + 1}")

        return AskResult(answer=answer, sources=sorted(set(sources)))
