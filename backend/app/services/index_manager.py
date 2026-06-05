import os
from pathlib import Path
from typing import Optional

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.core.database import SessionLocal
from app.models import Chunk, Document as DocModel


class IndexManager:
    """Manages FAISS index rebuilding for collections."""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[3]
        self.embedding_model = "all-MiniLM-L6-v2"
        self._embeddings: Optional[HuggingFaceEmbeddings] = None

    def _get_embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model,
                model_kwargs={"device": "cpu"},
            )
        return self._embeddings

    def rebuild_collection_index(self, collection_id: str) -> dict:
        """Rebuild FAISS index for a collection based on its documents' chunks."""
        db = SessionLocal()
        try:
            from app.models import Collection

            collection = db.query(Collection).filter(Collection.id == collection_id).first()
            if not collection:
                return {"success": False, "error": "Collection not found"}

            docs = db.query(DocModel).filter(DocModel.collection_id == collection_id).all()
            if not docs:
                return {"success": False, "error": "No documents in collection"}

            all_chunks = []
            for doc in docs:
                chunks = db.query(Chunk).filter(
                    Chunk.document_id == doc.id
                ).order_by(Chunk.chunk_index).all()

                for chunk in chunks:
                    metadata = {
                        "source": doc.filename,
                        "document_id": doc.id,
                        "chunk_index": chunk.chunk_index,
                        "collection": collection.name,
                    }
                    all_chunks.append(Document(
                        page_content=chunk.content,
                        metadata=metadata
                    ))

            if not all_chunks:
                return {"success": False, "error": "No chunks found"}

            index_dir = self.project_root / "data" / "faiss" / collection.name
            index_dir.mkdir(parents=True, exist_ok=True)

            embeddings = self._get_embeddings()
            vectorstore = FAISS.from_documents(documents=all_chunks, embedding=embeddings)
            vectorstore.save_local(str(index_dir))

            # Mark every chunk of every document in this collection as indexed
            doc_ids = [doc.id for doc in docs]
            for doc_id in doc_ids:
                db.query(Chunk).filter(
                    Chunk.document_id == doc_id,
                    Chunk.embedding_status == "pending",
                ).update({"embedding_status": "indexed"}, synchronize_session=False)
            db.commit()

            return {
                "success": True,
                "collection": collection.name,
                "chunks_indexed": len(all_chunks),
                "index_path": str(index_dir)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            db.close()

    def rebuild_document_index(self, document_id: str) -> dict:
        """Rebuild FAISS index for a single document's collection."""
        from app.models import Collection
        
        db = SessionLocal()
        try:
            doc = db.query(DocModel).filter(DocModel.id == document_id).first()
            if not doc:
                return {"success": False, "error": "Document not found"}

            # Create default collection if none exists
            if not doc.collection_id:
                default_col = db.query(Collection).filter(Collection.name == "default").first()
                if not default_col:
                    default_col = Collection(
                        id=f"col_{os.urandom(8).hex()}",
                        name="default",
                        description="Default collection"
                    )
                    db.add(default_col)
                    db.commit()
                    db.refresh(default_col)
                doc.collection_id = default_col.id
                db.commit()

            return self.rebuild_collection_index(doc.collection_id)

        finally:
            db.close()

    def rebuild_all_indexes(self) -> list[dict]:
        """Rebuild indexes for all collections."""
        from app.models import Collection

        db = SessionLocal()
        results = []
        try:
            collections = db.query(Collection).all()
            for col in collections:
                result = self.rebuild_collection_index(col.id)
                results.append(result)
        finally:
            db.close()

        return results


index_manager = IndexManager()