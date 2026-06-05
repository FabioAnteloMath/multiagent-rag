"""Import existing documents from data/docs into the SQLite database.

Idempotent: skips when documents are already imported.
Paths are resolved relative to this file, so it runs from any CWD.
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

PROJECT_ROOT = BACKEND_DIR.parent
DOCS_DIR = PROJECT_ROOT / "data" / "docs"

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.models import Document, Chunk  # noqa: E402


def import_existing_documents() -> None:
    init_db()
    db = SessionLocal()
    try:
        existing_docs = db.query(Document).count()
        if existing_docs > 0:
            print(f"Ja existem {existing_docs} documentos no banco. Pulando import.")
            return

        print(f"Importando documentos de {DOCS_DIR}...")

        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)

        for file_path in DOCS_DIR.iterdir():
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lstrip(".").lower()
            if suffix not in {"pdf", "md", "txt"}:
                continue

            file_size = file_path.stat().st_size
            doc_id = f"doc_{__import__('os').urandom(8).hex()}"

            doc = Document(
                id=doc_id,
                filename=file_path.name,
                file_type=suffix,
                file_size=file_size,
                file_path=str(file_path),
                status="indexed",
                collection_id=None,
            )
            db.add(doc)

            if suffix in {"md", "txt"}:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                texts = splitter.split_text(content)
                for idx, text in enumerate(texts):
                    chunk = Chunk(
                        id=f"chunk_{__import__('os').urandom(8).hex()}",
                        document_id=doc_id,
                        content=text,
                        chunk_index=idx,
                        embedding_status="indexed",
                        chunk_id=str(idx),
                    )
                    db.add(chunk)
                print(f"  Importado: {file_path.name} ({len(texts)} chunks)")

        db.commit()
        print("Import concluido!")
    except Exception as e:
        print(f"Erro: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import_existing_documents()
