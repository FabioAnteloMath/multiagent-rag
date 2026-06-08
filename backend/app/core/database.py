import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# Allow DATA_DIR override (used in Docker/Fly volume mount).
# Defaults to <project_root>/data for local dev.
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
_data_root = os.getenv("DATA_DIR", os.path.join(_project_root, "data"))

db_path = os.path.join(_data_root, "db", "multiagent_rag.db")
os.makedirs(os.path.dirname(db_path), exist_ok=True)

DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models.document import Collection, Document, Chunk, Agent, ProcessingLog
    Base.metadata.create_all(bind=engine)