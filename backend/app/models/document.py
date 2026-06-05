from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def generate_id():
    return str(uuid.uuid4())


class Collection(Base):
    __tablename__ = "collections"

    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, default="")
    is_default = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="collection")
    agents = relationship("Agent", back_populates="collection")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_id)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    file_path = Column(String, default="")
    upload_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")
    collection_id = Column(String, ForeignKey("collections.id"), nullable=True)

    collection = relationship("Collection", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=generate_id)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    embedding_status = Column(String, default="pending")
    chunk_id = Column(String, nullable=True)

    document = relationship("Document", back_populates="chunks")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, nullable=False)
    specialty = Column(Text, default="")
    system_prompt = Column(Text, default="")
    guidelines = Column(Text, default="")
    personality = Column(Text, default="")
    response_format = Column(Text, default="")
    examples = Column(Text, default="")
    collection_id = Column(String, ForeignKey("collections.id"), nullable=True)
    provider = Column(String, default="ollama")
    model_name = Column(String, default="llama3.2:3b")
    temperature = Column(String, default="0.3")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)

    collection = relationship("Collection", back_populates="agents")


class ProcessingLog(Base):
    __tablename__ = "processing_log"

    id = Column(String, primary_key=True, default=generate_id)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    status = Column(String, default="pending")
    message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)