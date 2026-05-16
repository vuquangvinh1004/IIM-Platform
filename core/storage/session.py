"""Context-managed DB session helper for IIMP.

Usage::

    from core.storage.session import get_session

    with get_session() as session:
        session.add(obj)
        # auto-committed on clean exit; rolled back on exception
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session

from config.database import SessionFactory
from core.utils.logger import get_logger

_log = get_logger("iimp.storage.session")


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional DB session with automatic commit/rollback."""
    session: Session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        _log.exception("DB transaction rolled back due to unhandled exception.")
        raise
    finally:
        session.close()
