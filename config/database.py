"""Database engine and session factory for IIMP.

Uses SQLAlchemy with SQLite. All database access must go through
the session factory provided here — no widget or view should touch
the engine directly.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from config.paths import DATABASE_URL, ensure_runtime_dirs


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:  # noqa: ARG001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def build_engine():
    """Create and configure the SQLAlchemy engine."""
    ensure_runtime_dirs()
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine


# Module-level singletons — created once at import
engine = build_engine()
SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
