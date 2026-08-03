"""Fixtures compartidas de las pruebas."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_JSON", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from app.services.analysis.pipeline import RawComment, RawVideo

NOW = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def anchor() -> datetime:
    return NOW


def make_video(
    index: int,
    *,
    views: int | None = 10_000,
    likes: int | None = 400,
    comments: int | None = 50,
    days_ago: int = 30,
    comments_disabled: bool = False,
    title: str | None = None,
) -> RawVideo:
    return RawVideo(
        video_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"video-{index}"),
        youtube_video_id=f"vid{index:08d}".ljust(11, "x")[:11],
        title=title or f"Vídeo de prueba {index}",
        published_at=NOW - timedelta(days=days_ago),
        view_count=views,
        like_count=likes,
        comment_count=comments,
        comments_disabled=comments_disabled,
    )


def make_comment(
    index: int,
    video: RawVideo,
    text: str,
    *,
    days_ago: int = 10,
    likes: int = 3,
) -> RawComment:
    return RawComment(
        comment_id=uuid.uuid5(uuid.NAMESPACE_DNS, f"comment-{index}-{video.youtube_video_id}"),
        video_id=video.video_id,
        youtube_video_id=video.youtube_video_id,
        text=text,
        published_at=NOW - timedelta(days=days_ago),
        like_count=likes,
        author_hash=f"a_{index:024d}",
    )


@pytest.fixture
def videos() -> list[RawVideo]:
    return [make_video(i, days_ago=90 - i * 7) for i in range(8)]


@pytest.fixture
def comments(videos: list[RawVideo]) -> list[RawComment]:
    """Muestra sintética con elogios, críticas, peticiones y preguntas."""
    praise = [
        "Me encanta tu humor, eres un crack",
        "El humor de este canal es lo mejor, me río muchísimo",
        "Qué gracioso eres, genial el vídeo",
        "Tu sentido del humor me alegra el día, gracias",
    ]
    criticism = [
        "La música está muy alta, no se escucha bien tu voz",
        "No se te oye cuando hablas bajito, sube el micro",
        "El audio se escucha fatal en esta parte",
        "Baja la música de fondo, tapa lo que dices",
    ]
    requests = [
        "Haz un tutorial paso a paso de esto por favor",
        "Necesitamos un tutorial para principiantes",
        "¿Puedes hacer un vídeo explicando cómo lo haces?",
        "Tutorial desde cero porfa",
    ]
    questions = [
        "¿Qué micrófono usas para grabar?",
        "¿Cuál es la configuración que utilizas?",
        "¿Dónde compro ese producto?",
    ]

    out: list[RawComment] = []
    counter = 0
    for video_index, video in enumerate(videos):
        pool = praise + criticism + requests + questions
        for text in pool:
            counter += 1
            out.append(
                make_comment(
                    counter,
                    video,
                    f"{text} (v{video_index})",
                    days_ago=max(1, 80 - video_index * 9),
                    likes=counter % 7,
                )
            )
    return out
