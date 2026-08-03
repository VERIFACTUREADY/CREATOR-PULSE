"""Tipos de columna reutilizables.

`EmbeddingVector` usa `pgvector` cuando la extensión está disponible y degrada a
JSON en caso contrario, de modo que el sistema arranca aunque la extensión no
esté instalada (por ejemplo en un PostgreSQL gestionado sin `vector`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Dialect
from sqlalchemy.types import TypeDecorator, UserDefinedType

from app.core.config import settings

_pgvector_available: bool | None = None


def pgvector_enabled() -> bool:
    """Indica si debe usarse el tipo nativo `vector`."""
    global _pgvector_available
    if settings.pgvector_mode == "false":
        return False
    if settings.pgvector_mode == "true":
        return True
    if _pgvector_available is None:
        # En modo `auto` se asume disponible: la migración crea la extensión y
        # marca el resultado real con `set_pgvector_available()`.
        return True
    return _pgvector_available


def set_pgvector_available(value: bool) -> None:
    global _pgvector_available
    _pgvector_available = value


class _VectorFallback(UserDefinedType[Any]):
    """Representación JSON usada cuando pgvector no está disponible."""

    cache_ok = True

    def get_col_spec(self, **_kw: Any) -> str:
        return "JSONB"


class EmbeddingVector(TypeDecorator[list[float]]):
    """Vector de embeddings de dimensión fija.

    Se serializa como `vector(dim)` en PostgreSQL con pgvector y como JSONB en
    el resto de casos. En Python siempre es una lista de `float`.
    """

    impl = JSON
    cache_ok = True

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or settings.embedding_dim
        super().__init__()

    def load_dialect_impl(self, dialect: Dialect) -> Any:
        if dialect.name == "postgresql" and pgvector_enabled():
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return None
        return [float(v) for v in value]

    def process_result_value(self, value: Any, dialect: Dialect) -> list[float] | None:
        if value is None:
            return None
        return [float(v) for v in value]


__all__ = ["EmbeddingVector", "_VectorFallback", "pgvector_enabled", "set_pgvector_available"]
