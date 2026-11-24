import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "bankguard.db"
DATABASE_URL = os.getenv("BANKGUARD_DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Kolumny dodane po pierwszym wydaniu. `create_all` tworzy tylko brakujące TABELE, więc
# istniejące bazy dostają nowe kolumny tu — idempotentnie, z wartością domyślną.
_ADDED_COLUMNS = (
    ("analysts", "role", "VARCHAR(20) NOT NULL DEFAULT 'analyst'"),
    ("fraud_cases", "updated_by", "VARCHAR(255)"),
    ("transactions", "is_new_payee", "BOOLEAN NOT NULL DEFAULT 0"),
    ("transactions", "payee_account_age_days", "INTEGER"),
    ("transactions", "remote_access_detected", "BOOLEAN NOT NULL DEFAULT 0"),
    ("transactions", "active_call_during_session", "BOOLEAN NOT NULL DEFAULT 0"),
    ("transactions", "recent_sim_swap", "BOOLEAN NOT NULL DEFAULT 0"),
)


def _add_missing_columns() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    with engine.begin() as connection:
        for table, column, ddl in _ADDED_COLUMNS:
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

