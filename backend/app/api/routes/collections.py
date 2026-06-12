from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models import Chunk, Collection, Document

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: str
    is_default: bool
    document_count: int
    created_at: str

    class Config:
        from_attributes = True


class DocumentInCollection(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    upload_date: str
    chunks_count: int

    class Config:
        from_attributes = True


class CollectionCreate(BaseModel):
    name: str
    description: str = ""
    is_default: bool = False


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class MergeRequest(BaseModel):
    source_ids: list[str]
    target_id: str


def _to_response(col: Collection, document_count: int) -> CollectionResponse:
    return CollectionResponse(
        id=col.id,
        name=col.name,
        description=col.description or "",
        is_default=bool(col.is_default),
        document_count=document_count,
        created_at=col.created_at.isoformat() if col.created_at else "",
    )


@router.get("", response_model=list[CollectionResponse])
def list_collections(db: Session = Depends(get_db)):
    collections = db.query(Collection).order_by(Collection.created_at.desc()).all()
    return [
        _to_response(
            col,
            db.query(Document).filter(Document.collection_id == col.id).count(),
        )
        for col in collections
    ]


@router.post("", response_model=CollectionResponse)
def create_collection(collection: CollectionCreate, db: Session = Depends(get_db)):
    existing = db.query(Collection).filter(Collection.name == collection.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Collection com este nome ja existe")

    if collection.is_default:
        db.query(Collection).update({"is_default": False})

    new_collection = Collection(
        name=collection.name,
        description=collection.description,
        is_default=collection.is_default,
    )
    db.add(new_collection)
    db.commit()
    db.refresh(new_collection)
    return _to_response(new_collection, 0)


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(collection_id: str, db: Session = Depends(get_db)):
    col = db.query(Collection).filter(Collection.id == collection_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection nao encontrada")
    doc_count = db.query(Document).filter(Document.collection_id == col.id).count()
    return _to_response(col, doc_count)


@router.put("/{collection_id}", response_model=CollectionResponse)
def update_collection(collection_id: str, update: CollectionUpdate, db: Session = Depends(get_db)):
    col = db.query(Collection).filter(Collection.id == collection_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection nao encontrada")

    if update.name:
        existing = db.query(Collection).filter(
            Collection.name == update.name,
            Collection.id != collection_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Nome ja esta em uso")

    if update.name is not None:
        col.name = update.name
    if update.description is not None:
        col.description = update.description

    db.commit()
    db.refresh(col)
    doc_count = db.query(Document).filter(Document.collection_id == col.id).count()
    return _to_response(col, doc_count)


@router.delete("/{collection_id}")
def delete_collection(collection_id: str, db: Session = Depends(get_db)):
    col = db.query(Collection).filter(Collection.id == collection_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection nao encontrada")

    default_col = db.query(Collection).filter(Collection.is_default == True).first()
    if default_col and col.id == default_col.id:
        raise HTTPException(status_code=400, detail="Nao e possivel excluir collection padrao")

    db.query(Document).filter(Document.collection_id == collection_id).update({"collection_id": None})
    db.delete(col)
    db.commit()

    return {"message": "Collection excluida"}


@router.post("/merge")
def merge_collections(request: MergeRequest, db: Session = Depends(get_db)):
    target = db.query(Collection).filter(Collection.id == request.target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Collection target nao encontrada")

    for source_id in request.source_ids:
        if source_id == request.target_id:
            continue
        db.query(Document).filter(Document.collection_id == source_id).update(
            {"collection_id": request.target_id}
        )
        col = db.query(Collection).filter(Collection.id == source_id).first()
        if col:
            db.delete(col)

    db.commit()
    return {"message": f"Collections mescladas em {target.name}"}


@router.get("/{collection_id}/documents", response_model=list[DocumentInCollection])
def get_collection_documents(collection_id: str, db: Session = Depends(get_db)):
    col = db.query(Collection).filter(Collection.id == collection_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    documents = (
        db.query(Document)
        .filter(Document.collection_id == collection_id)
        .order_by(Document.upload_date.desc())
        .all()
    )

    result = []
    for d in documents:
        chunks_count = db.query(Chunk).filter(Chunk.document_id == d.id).count()
        result.append(DocumentInCollection(
            id=d.id,
            filename=d.filename,
            file_type=d.file_type,
            file_size=d.file_size,
            status=d.status,
            upload_date=d.upload_date.isoformat() if d.upload_date else "",
            chunks_count=chunks_count,
        ))
    return result
