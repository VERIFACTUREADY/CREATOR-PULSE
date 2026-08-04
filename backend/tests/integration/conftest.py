"""Fixtures de integración: base de datos real y API de YouTube mockeada."""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest
from app.core.config import settings
from app.db.base import Base
from app.db.types import set_pgvector_available
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


def _derive_test_url(url: str) -> str:
    """Sustituye sólo el nombre de la base de datos, no el del usuario.

    La URL contiene el usuario y la base con el mismo nombre, así que un
    `replace` global renombraría también el usuario.
    """
    base, _, database = url.rpartition("/")
    return f"{base}/{database}_test"


#: Base de datos de pruebas. Se puede sobrescribir con TEST_DATABASE_URL.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", _derive_test_url(settings.database_url))


def _ensure_test_database() -> None:
    """Crea la base de datos de pruebas si no existe."""
    admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    db_name = TEST_DATABASE_URL.rsplit("/", 1)[1]
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
        ).first()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    engine.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Any]:
    try:
        _ensure_test_database()
    except Exception as exc:  # pragma: no cover - entorno sin PostgreSQL
        pytest.skip(f"PostgreSQL no disponible para las pruebas de integración: {exc}")

    test_engine = create_engine(TEST_DATABASE_URL, future=True)
    with test_engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            set_pgvector_available(True)
        except Exception:
            conn.rollback()
            set_pgvector_available(False)

    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session(engine: Any) -> Iterator[Session]:
    """Sesión limpia por prueba: se vacían todas las tablas al terminar."""
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    db = factory()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
        with engine.connect() as conn:
            # `maintenance_run` no cuelga de `channel`, así que hay que nombrarla:
            # si no, los registros de purga se filtran entre pruebas.
            conn.execute(text("TRUNCATE channel, comparison, api_usage, maintenance_run CASCADE"))
            conn.commit()


# ---------------------------------------------------------------------------
# Cargas útiles de la API de YouTube
# ---------------------------------------------------------------------------

#: Un ID de canal válido son exactamente 24 caracteres: «UC» + 22.
CHANNEL_ID = "UCtest" + "0" * 17 + "a"
UPLOADS_ID = "UU" + CHANNEL_ID[2:]


def channel_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "items": [
            {
                "id": CHANNEL_ID,
                "snippet": {
                    "title": "Canal de prueba",
                    "description": "Descripción del canal",
                    "customUrl": "@canalprueba",
                    "publishedAt": "2020-01-01T00:00:00Z",
                    "country": "ES",
                    "thumbnails": {"high": {"url": "https://example.test/thumb.jpg"}},
                },
                "statistics": {
                    "subscriberCount": "12345",
                    "videoCount": "80",
                    "viewCount": "999999",
                    "hiddenSubscriberCount": False,
                },
                "contentDetails": {"relatedPlaylists": {"uploads": UPLOADS_ID}},
            }
        ]
    }
    payload.update(overrides)
    return payload


def playlist_payload(count: int = 3, next_token: str | None = None) -> dict[str, Any]:
    items = [
        {
            "contentDetails": {"videoId": f"vid{i:08d}"[:11].ljust(11, "x")},
            "status": {"privacyStatus": "public"},
            "snippet": {"title": f"Vídeo {i}"},
        }
        for i in range(count)
    ]
    payload: dict[str, Any] = {"items": items}
    if next_token:
        payload["nextPageToken"] = next_token
    return payload


def videos_payload(count: int = 3, *, comments_disabled_index: int | None = None) -> dict[str, Any]:
    items = []
    for i in range(count):
        statistics: dict[str, Any] = {
            "viewCount": str(10_000 + i * 1000),
            "likeCount": str(400 + i * 10),
            "commentCount": str(50 + i),
        }
        if comments_disabled_index is not None and i == comments_disabled_index:
            # La API omite `commentCount` cuando los comentarios están cerrados.
            statistics.pop("commentCount")
        items.append(
            {
                "id": f"vid{i:08d}"[:11].ljust(11, "x"),
                "snippet": {
                    "title": f"Vídeo {i}",
                    "description": "Descripción",
                    "publishedAt": f"2024-0{(i % 9) + 1}-01T10:00:00Z",
                    "thumbnails": {"high": {"url": f"https://example.test/v{i}.jpg"}},
                    "categoryId": "22",
                    "liveBroadcastContent": "none",
                    "tags": ["tag1"],
                },
                "statistics": statistics,
                "contentDetails": {"duration": "PT10M30S"},
            }
        )
    return {"items": items}


def comment_threads_payload(
    video_id: str, count: int = 5, *, start: int = 0, next_token: str | None = None
) -> dict[str, Any]:
    texts = [
        "Me encanta tu humor, eres un crack",
        "La música está muy alta, no se escucha bien tu voz",
        "¿Puedes hacer un tutorial paso a paso?",
        "Gran vídeo, muy útil la explicación",
        "¿Qué micrófono usas para grabar?",
    ]
    items = [
        {
            "id": f"thread-{video_id}-{start + i}",
            "snippet": {
                "totalReplyCount": 0,
                "topLevelComment": {
                    "id": f"comment-{video_id}-{start + i}",
                    "snippet": {
                        "textOriginal": texts[(start + i) % len(texts)],
                        "publishedAt": "2024-05-01T10:00:00Z",
                        "likeCount": (start + i) % 10,
                        "authorChannelId": {"value": f"UCauthor{(start + i) % 20}"},
                    },
                },
            },
        }
        for i in range(count)
    ]
    payload: dict[str, Any] = {"items": items}
    if next_token:
        payload["nextPageToken"] = next_token
    return payload


def error_payload(reason: str, message: str = "error") -> dict[str, Any]:
    return {"error": {"errors": [{"reason": reason, "message": message}], "message": message}}
