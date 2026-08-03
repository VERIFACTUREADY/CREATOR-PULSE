"""Motor de base de datos y gestión de sesiones."""

from __future__ import annotations

from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger
from app.db.types import set_pgvector_available

logger = get_logger(__name__)

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(), autoflush=False, expire_on_commit=False, future=True
        )
    return _SessionFactory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Sesión transaccional: confirma al salir, revierte ante una excepción."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def detect_pgvector() -> bool:
    """Comprueba contra la base de datos si la extensión `vector` está activa."""
    if settings.pgvector_mode == "false":
        set_pgvector_available(False)
        return False
    try:
        with get_engine().connect() as conn:
            row = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")).first()
        available = row is not None
    except Exception as exc:  # pragma: no cover - depende del entorno
        logger.warning("pgvector_detection_failed", error=str(exc))
        available = False
    set_pgvector_available(available)
    return available


def check_database() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("database_healthcheck_failed", error=str(exc))
        return False


__all__ = [
    "check_database",
    "detect_pgvector",
    "get_db",
    "get_engine",
    "get_session_factory",
    "session_scope",
]
