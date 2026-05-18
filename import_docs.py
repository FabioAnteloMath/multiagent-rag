import sys
import os
sys.path.insert(0, 'C:/WorkSpace/Pessoal/multiagent-rag/backend')

from app.core.database import SessionLocal, init_db
from app.models import Document, Chunk

docs_dir = "C:/WorkSpace/Pessoal/multiagent-rag/data/docs"

def import_existing_documents():
    init_db()
    db = SessionLocal()

    try:
        existing_docs = db.query(Document).count()
        if existing_docs > 0:
            print(f"Ja existem {existing_docs} documentos no banco. Pulando import.")
            return

        print("Importando documentos de data/docs...")

        for file_path in os.listdir(docs_dir):
            full_path = os.path.join(docs_dir, file_path)
            if not os.path.isfile(full_path):
                continue

            suffix = file_path.split('.')[-1].lower()
            if suffix not in ["pdf", "md", "txt"]:
                continue

            file_size = os.path.getsize(full_path)
            doc_id = f"doc_{os.urandom(8).hex()}"

            doc = Document(
                id=doc_id,
                filename=file_path,
                file_type=suffix,
                file_size=file_size,
                file_path=full_path,
                status="indexed",
                collection_id=None
            )
            db.add(doc)

            if suffix == "md" or suffix == "txt":
                content = open(full_path, "r", encoding="utf-8", errors="ignore").read()

                from langchain.text_splitter import RecursiveCharacterTextSplitter
                splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
                texts = splitter.split_text(content)

                for idx, text in enumerate(texts):
                    chunk = Chunk(
                        id=f"chunk_{os.urandom(8).hex()}",
                        document_id=doc_id,
                        content=text,
                        chunk_index=idx,
                        embedding_status="indexed",
                        chunk_id=str(idx)
                    )
                    db.add(chunk)

                print(f"  Importado: {file_path} ({len(texts)} chunks)")

        db.commit()
        print("Import concluida!")

    except Exception as e:
        print(f"Erro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import_existing_documents()