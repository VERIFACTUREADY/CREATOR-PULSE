"""Carga de datos de demostración.

Los datos son ficticios y se marcan siempre con `source = "demo"`, de modo que
nunca se mezclan con registros reales de la API sin que la interfaz lo indique.
El pipeline determinista los analiza igual que a los datos reales: no hay
resultados precalculados.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import FeatureDisabledError, NotFoundError
from app.core.logging import get_logger
from app.core.privacy import hash_author_id
from app.models.entities import Channel
from app.models.enums import DataSource
from app.repositories.channels import ChannelRepository, CommentRepository, VideoRepository

logger = get_logger(__name__)

#: Directorio de fixtures. Se resuelve relativo a la raíz del repositorio y
#: puede sobrescribirse en los tests.
FIXTURES_DIR = Path(__file__).resolve().parents[2].parent / "fixtures"


@dataclass(frozen=True)
class DemoChannelInfo:
    """Metadatos de un canal de demostración disponible."""

    file: str
    youtube_channel_id: str
    handle: str
    title: str
    videos: int
    comments: int


def _fixtures_dir() -> Path:
    if FIXTURES_DIR.exists():
        return FIXTURES_DIR
    # Alternativa cuando el backend se ejecuta desde su propio directorio.
    candidate = Path.cwd() / "fixtures"
    if candidate.exists():
        return candidate
    candidate = Path.cwd().parent / "fixtures"
    return candidate


@lru_cache(maxsize=1)
def list_demo_channels() -> list[DemoChannelInfo]:
    """Lee `fixtures/index.json` y devuelve los canales disponibles."""
    index_path = _fixtures_dir() / "index.json"
    if not index_path.exists():
        logger.warning("demo_index_missing", path=str(index_path))
        return []
    data = json.loads(index_path.read_text(encoding="utf-8"))
    return [DemoChannelInfo(**entry) for entry in data.get("channels", [])]


def load_demo_payload(handle: str) -> dict[str, Any]:
    """Carga el fichero de un canal de demostración por su handle."""
    for info in list_demo_channels():
        if info.handle == handle.lstrip("@") or info.youtube_channel_id == handle:
            path = _fixtures_dir() / info.file
            return dict(json.loads(path.read_text(encoding="utf-8")))
    raise NotFoundError(
        f"No existe ningún canal de demostración llamado «{handle}».",
        detail=f"handle desconocido: {handle}",
    )


def _reanchor(value: str, delta: timedelta) -> datetime:
    """Desplaza una fecha del fixture para que sea reciente respecto a hoy."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed + delta


class DemoLoader:
    """Inserta un canal de demostración completo en la base de datos."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.channels = ChannelRepository(session)
        self.videos = VideoRepository(session)
        self.comments = CommentRepository(session)

    def load(self, handle: str, *, enabled: bool = True) -> Channel:
        """Carga (o refresca) un canal de demostración. Es idempotente."""
        if not enabled:
            raise FeatureDisabledError(
                "El modo demostración está desactivado en esta instalación.",
                detail="ENABLE_DEMO_MODE=false",
            )

        payload = load_demo_payload(handle)
        reference = datetime.fromisoformat(payload["reference_date"])
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=UTC)
        # Las fechas se reanclan a hoy para que las ventanas temporales del
        # análisis de tendencias tengan sentido en cualquier momento.
        delta = datetime.now(UTC) - reference

        channel_data = dict(payload["channel"])
        channel_data["published_at"] = _reanchor(channel_data["published_at"], delta)
        channel = self.channels.upsert(channel_data, source=DataSource.DEMO)

        video_rows = []
        for video in payload["videos"]:
            row = dict(video)
            row["published_at"] = _reanchor(row["published_at"], delta)
            video_rows.append(row)
        stored_videos = self.videos.upsert_many(channel.id, video_rows, source=DataSource.DEMO)
        video_by_youtube_id = {v.youtube_video_id: v for v in stored_videos}

        by_video: dict[str, list[dict[str, Any]]] = {}
        for comment in payload["comments"]:
            row = {
                "youtube_comment_id": comment["youtube_comment_id"],
                "text": comment["text"],
                "published_at": _reanchor(comment["published_at"], delta),
                "updated_at_source": None,
                "like_count": comment["like_count"],
                "reply_count": comment["reply_count"],
                "is_top_level": comment["is_top_level"],
                "parent_comment_id": None,
                "author_hash": hash_author_id(comment["author_seed"]),
                "sampling_bucket": comment.get("sampling_bucket"),
            }
            by_video.setdefault(comment["video_id"], []).append(row)

        for youtube_video_id, rows in by_video.items():
            video = video_by_youtube_id.get(youtube_video_id)
            if video is None:
                continue
            self.comments.upsert_many(video.id, rows, source=DataSource.DEMO)

        channel.last_fetched_at = datetime.now(UTC)
        self.session.add(channel)
        self.session.flush()

        logger.info(
            "demo_channel_loaded",
            handle=handle,
            videos=len(stored_videos),
            comments=sum(len(rows) for rows in by_video.values()),
        )
        return channel


def resolve_demo_reference(raw: str) -> str | None:
    """Devuelve el handle de demostración si la referencia corresponde a uno."""
    candidate = raw.strip().lstrip("@").lower()
    for info in list_demo_channels():
        if candidate in {info.handle.lower(), info.youtube_channel_id.lower()}:
            return info.handle
        if candidate.endswith(info.handle.lower()):
            return info.handle
    return None


__all__ = [
    "FIXTURES_DIR",
    "DemoChannelInfo",
    "DemoLoader",
    "list_demo_channels",
    "load_demo_payload",
    "resolve_demo_reference",
]
