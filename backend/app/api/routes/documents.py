from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import shutil

from app.core.database import get_db
from app.models import Document, Chunk, Collection, ProcessingLog
from app.services.index_manager import index_manager

router = APIRouter(prefix="/documents", tags=["documents"])

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
UPLOAD_DIR = os.path.join(project_root, "data", "docs")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    upload_date: str
    status: str
    collection_id: Optional[str]
    chunks_count: int

    class Config:
        from_attributes = True


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    content: str
    chunk_index: int
    embedding_status: str

    class Config:
        from_attributes = True


class ChunkCreate(BaseModel):
    content: str
    chunk_index: Optional[int] = None


class ChunkUpdate(BaseModel):
    content: Optional[str] = None
    chunk_index: Optional[int] = None
    embedding_status: Optional[str] = None


class UploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str


class DocumentUpdate(BaseModel):
    collection_id: Optional[str] = None


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    collection_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Document)
    if collection_id:
        query = query.filter(Document.collection_id == collection_id)
    if status:
        query = query.filter(Document.status == status)
    documents = query.order_by(Document.upload_date.desc()).all()

    result = []
    for doc in documents:
        chunks_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
        result.append(DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            upload_date=doc.upload_date.isoformat() if doc.upload_date else "",
            status=doc.status,
            collection_id=doc.collection_id,
            chunks_count=chunks_count
        ))
    return result


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")
    chunks_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        upload_date=doc.upload_date.isoformat() if doc.upload_date else "",
        status=doc.status,
        collection_id=doc.collection_id,
        chunks_count=chunks_count
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    collection_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    file_type = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if file_type not in ["pdf", "md", "txt"]:
        raise HTTPException(status_code=400, detail="Tipo de arquivo invalido. Use PDF, MD ou TXT")

    doc_id = f"doc_{os.urandom(8).hex()}"
    safe_filename = f"{doc_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    collection = None
    if collection_id:
        collection = db.query(Collection).filter(Collection.id == collection_id).first()

    document = Document(
        id=doc_id,
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        file_path=file_path,
        status="pending",
        collection_id=collection_id if collection else None
    )
    db.add(document)
    db.commit()

    ProcessingLog(
        document_id=doc_id,
        status="uploaded",
        message=f"Arquivo {file.filename} carregado com sucesso"
    )
    db.add(ProcessingLog(
        document_id=doc_id,
        status="pending",
        message="Aguardando processamento de chunking"
    ))
    db.commit()

    return UploadResponse(
        id=doc_id,
        filename=file.filename,
        status="pending",
        message="Documento carregado. Use /documents/{id}/process para processar."
    )


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")

    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.query(Chunk).filter(Chunk.document_id == document_id).delete()
    db.query(ProcessingLog).filter(ProcessingLog.document_id == document_id).delete()
    db.delete(doc)
    db.commit()

    return {"message": "Documento excluido"}


@router.put("/{document_id}")
def update_document(document_id: str, update_data: DocumentUpdate, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")

    if update_data.collection_id is not None:
        if update_data.collection_id:
            col = db.query(Collection).filter(Collection.id == update_data.collection_id).first()
            if not col:
                raise HTTPException(status_code=400, detail="Collection nao encontrada")
        doc.collection_id = update_data.collection_id

    db.commit()
    return {"message": "Documento atualizado"}


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
def get_document_chunks(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
    return [ChunkResponse(
        id=c.id,
        document_id=c.document_id,
        content=c.content,
        chunk_index=c.chunk_index,
        embedding_status=c.embedding_status
    ) for c in chunks]


@router.post("/{document_id}/process")
def process_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")

    doc.status = "processing"
    db.commit()

    try:
        if doc.file_type == "pdf":
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(doc.file_path)
            pages = loader.load()
            content = "\n\n".join([p.page_content for p in pages])
        elif doc.file_type == "md":
            content = open(doc.file_path, "r", encoding="utf-8", errors="ignore").read()
        else:
            content = open(doc.file_path, "r", encoding="utf-8", errors="ignore").read()

        from langchain.text_splitter import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
        texts = splitter.split_text(content)

        db.query(Chunk).filter(Chunk.document_id == document_id).delete()

        for idx, text in enumerate(texts):
            chunk = Chunk(
                id=f"chunk_{os.urandom(8).hex()}",
                document_id=document_id,
                content=text,
                chunk_index=idx,
                embedding_status="pending",
                chunk_id=str(idx)
            )
            db.add(chunk)

        doc.status = "indexed"
        db.add(ProcessingLog(
            document_id=document_id,
            status="completed",
            message=f"{len(texts)} chunks criados e indexados"
        ))
        db.commit()

        return {"message": f"Documento processado. {len(texts)} chunks criados."}

    except Exception as e:
        doc.status = "error"
        db.add(ProcessingLog(
            document_id=document_id,
            status="error",
            message=f"Erro no processamento: {str(e)}"
        ))
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/status")
def get_document_status(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento nao encontrado")
    logs = db.query(ProcessingLog).filter(
        ProcessingLog.document_id == document_id
    ).order_by(ProcessingLog.created_at.desc()).limit(10).all()
    return {
        "document_id": document_id,
        "status": doc.status,
        "logs": [{"status": l.status, "message": l.message, "created_at": l.created_at.isoformat()} for l in logs]
    }


@router.post("/{document_id}/chunks", response_model=ChunkResponse)
def create_chunk(document_id: str, chunk_data: ChunkCreate, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if chunk_data.chunk_index is not None:
        existing = db.query(Chunk).filter(
            Chunk.document_id == document_id,
            Chunk.chunk_index == chunk_data.chunk_index
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Chunk index already exists")

    max_index = db.query(Chunk).filter(Chunk.document_id == document_id).count()

    chunk = Chunk(
        id=f"chunk_{os.urandom(8).hex()}",
        document_id=document_id,
        content=chunk_data.content,
        chunk_index=chunk_data.chunk_index if chunk_data.chunk_index is not None else max_index,
        embedding_status="pending"
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    return ChunkResponse(
        id=chunk.id,
        document_id=chunk.document_id,
        content=chunk.content,
        chunk_index=chunk.chunk_index,
        embedding_status=chunk.embedding_status
    )


@router.put("/{document_id}/chunks/{chunk_id}", response_model=ChunkResponse)
def update_chunk(document_id: str, chunk_id: str, chunk_data: ChunkUpdate, db: Session = Depends(get_db)):
    chunk = db.query(Chunk).filter(
        Chunk.id == chunk_id,
        Chunk.document_id == document_id
    ).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    if chunk_data.content is not None:
        chunk.content = chunk_data.content
        chunk.embedding_status = "pending"

    if chunk_data.chunk_index is not None:
        existing = db.query(Chunk).filter(
            Chunk.document_id == document_id,
            Chunk.chunk_index == chunk_data.chunk_index,
            Chunk.id != chunk_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Chunk index already in use")
        chunk.chunk_index = chunk_data.chunk_index

    if chunk_data.embedding_status is not None:
        chunk.embedding_status = chunk_data.embedding_status

    db.commit()
    db.refresh(chunk)

    return ChunkResponse(
        id=chunk.id,
        document_id=chunk.document_id,
        content=chunk.content,
        chunk_index=chunk.chunk_index,
        embedding_status=chunk.embedding_status
    )


@router.delete("/{document_id}/chunks/{chunk_id}")
def delete_chunk(document_id: str, chunk_id: str, db: Session = Depends(get_db)):
    chunk = db.query(Chunk).filter(
        Chunk.id == chunk_id,
        Chunk.document_id == document_id
    ).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    db.delete(chunk)
    db.commit()

    remaining = db.query(Chunk).filter(Chunk.document_id == document_id).order_by(Chunk.chunk_index).all()
    for idx, c in enumerate(remaining):
        c.chunk_index = idx
    db.commit()

    result = index_manager.rebuild_document_index(document_id)

    return {
        "message": "Chunk deleted",
        "chunks_remaining": len(remaining),
        "index_rebuilt": result.get("success", False)
    }


@router.post("/{document_id}/reindex")
def rebuild_document_index(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result = index_manager.rebuild_document_index(document_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to rebuild index"))

    return result


@router.post("/rebuild-all-indexes")
def rebuild_all_indexes():
    results = index_manager.rebuild_all_indexes()
    return {
        "message": "Rebuild complete",
        "results": results
    }