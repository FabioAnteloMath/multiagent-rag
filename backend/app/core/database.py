import os
from sqlalchemy import create_engine, inspect, text
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


def _add_column_if_missing(conn, table: str, column: str, ddl: str) -> None:
    """Lightweight in-place migration: ALTER TABLE ADD COLUMN if missing.

    Used because Base.metadata.create_all() does not migrate existing tables
    when new columns are added to ORM models. Cheap and SQLite-safe.
    """
    cols = {c["name"] for c in inspect(engine).get_columns(table)}
    if column not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def init_db():
    from app.models.document import Collection, Document, Chunk, Agent, ProcessingLog, UsageLog
    Base.metadata.create_all(bind=engine)

    # Forward-only migrations for columns added after the original schema.
    # Each line is idempotent: it only runs if the column is missing.
    with engine.begin() as conn:
        _add_column_if_missing(
            conn, "agents", "is_fallback",
            "is_fallback BOOLEAN NOT NULL DEFAULT 0",
        )

        # One-shot backfill: any pre-existing agent whose name or specialty
        # strongly implies "fallback" role gets flagged. Idempotent: only
        # updates rows that are currently is_fallback = 0 and match the hints.
        conn.execute(text("""
            UPDATE agents
               SET is_fallback = 1
             WHERE is_fallback = 0
               AND (
                   LOWER(COALESCE(name, ''))     LIKE '%general%'
                OR LOWER(COALESCE(specialty, '')) LIKE '%general%'
                OR LOWER(COALESCE(name, ''))     LIKE '%geral%'
                OR LOWER(COALESCE(specialty, '')) LIKE '%geral%'
                OR LOWER(COALESCE(name, ''))     LIKE '%generalista%'
                OR LOWER(COALESCE(specialty, '')) LIKE '%generalista%'
               )
        """))