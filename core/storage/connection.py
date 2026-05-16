"""Database connection management for IIMP.

Thin wrapper around the engine in config.database that also handles
schema creation and exposes the engine for Alembic.
"""
from __future__ import annotations

from config.database import Base, engine
from core.utils.logger import get_logger

_log = get_logger("iimp.storage")


def init_db() -> None:
    """Create all tables if they do not exist.

    This is the baseline init used at startup. Alembic migrations take
    precedence for schema changes after initial deployment.
    """
    # Import models so SQLAlchemy registers them with Base.metadata
    import core.storage.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _log.info("Database tables ensured.")


def get_engine():
    """Return the shared SQLAlchemy engine (used by Alembic env.py)."""
    return engine
