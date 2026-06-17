from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


def generate_id():
    return str(uuid.uuid4())


class _CoerceFloat(TypeDecorator):
    """Float column that transparently accepts legacy string values.

    Earlier versions of the schema stored `Agent.temperature` as a
    String (because the API endpoints received it as a string and we
    never normalized). This decorator makes reads tolerant: if a
    row still has the old "0.3" form, the value comes back as 0.3
    instead of crashing. Writes always go out as proper floats.

    Backward compatibility is the only reason this exists — once the
    legacy rows are gone, the decorator can be removed and the column
    can be a plain `Float`.
    """

    impl = Float
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return float(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return None


class _CoerceBool(TypeDecorator):
    """Boolean column that accepts legacy INTEGER 0/1 rows on read.

    Same rationale as `_CoerceFloat`: the `is_active`, `is_default`,
    and `UsageLog.success` columns were originally declared as
    `Integer` and we never migrated the data. Reads from a legacy
    row return a proper `bool`; writes always go out as a bool.

    SQLAlchemy emits a CAST for the column so the underlying
    INTEGER/Float value is converted on the way out. SQLite handles
    `CAST(1 AS BOOLEAN)` returning 1 and Python bool() of 1 is True,
    so filter expressions like `Agent.is_active == True` still match
    legacy rows.
    """

    impl = Boolean
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return bool(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return bool(value)


class Collection(Base):
    __tablename__ = "collections"

    id = Column(String, primary_key=True, default=generate_id)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, default="")
    is_default = Column(_CoerceBool, default=False, nullable=False)
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
    # Stored as a real float now. _CoerceFloat tolerates legacy string rows
    # (e.g. "0.3") on read so we don't need a data migration just to boot
    # against a pre-existing dev DB.
    temperature = Column(_CoerceFloat, default=0.3, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(_CoerceBool, default=True, nullable=False)
    # True = fallback agent. The MasterAgent only uses fallback agents when no
    # specialist has relevant context. Agents without a collection (collection_id
    # is NULL) are *implicitly* fallbacks, but having an explicit flag lets you
    # mark an agent with a collection as a last-resort responder too.
    is_fallback = Column(_CoerceBool, default=False, nullable=False)

    collection = relationship("Collection", back_populates="agents")


class ProcessingLog(Base):
    __tablename__ = "processing_log"

    id = Column(String, primary_key=True, default=generate_id)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    status = Column(String, default="pending")
    message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class UsageLog(Base):
    """Per-request LLM usage record. Used by QuotaTracker to enforce
    free-tier limits and by /api/usage for visibility.

    One row per call to a provider (including fallback attempts that
    fail). A successful response increments `success=True`; a
    rate-limited fallback increments `success=False` and stores the
    error in `error`.
    """
    __tablename__ = "usage_log"

    id = Column(String, primary_key=True, default=generate_id)
    provider = Column(String, nullable=False, index=True)         # e.g. "groq"
    model = Column(String, nullable=False)                        # e.g. "llama-3.1-8b-instant"
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    success = Column(_CoerceBool, default=True, nullable=False)        # True=ok, False=failed
    fallback_from = Column(String, nullable=True)                  # e.g. "groq" if this row was a fallback attempt
    error = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
