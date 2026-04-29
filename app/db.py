from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_sqlite_schema_compatibility() -> None:
    """Backfill columns for local/demo SQLite databases created before model updates."""
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as conn:
        table_exists = conn.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='wallets'"))
        if table_exists.scalar() is None:
            return

        existing_columns = {row[1] for row in conn.execute(text("PRAGMA table_info(wallets)"))}

        if "version" not in existing_columns:
            conn.execute(text("ALTER TABLE wallets ADD COLUMN version INTEGER NOT NULL DEFAULT 1"))
        if "last_updated_at" not in existing_columns:
            conn.execute(text("ALTER TABLE wallets ADD COLUMN last_updated_at DATETIME"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
