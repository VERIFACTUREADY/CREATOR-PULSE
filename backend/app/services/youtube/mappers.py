"""Conversión de las respuestas de la YouTube Data API a diccionarios de dominio.

Todos los campos son tolerantes a valores ausentes: la API omite estadísticas
ocultas (por ejemplo el número de suscriptores) y no devuelve `dislikeCount`,
que se trata como no disponible.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.core.privacy import hash_author_id

_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?"
    r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def parse_iso_datetime(value: Any) -> datetime | None:
    """Convierte una marca temporal RFC3339 de la API en `datetime` con zona UTC."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def parse_duration(value: Any) -> int | None:
    """Convierte una duración ISO-8601 (`PT4M13S`) en segundos."""
    if not value or not isinstance(value, str):
        return None
    match = _DURATION_RE.match(value.strip())
    if not match:
        return None
    parts = {k: int(v) for k, v in match.groupdict(default="0").items()}
    total = parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]
    return total


def to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    # Los contadores nunca son negativos; un valor negativo es dato corrupto.
    return max(0, number)


def pick_thumbnail(thumbnails: dict[str, Any] | None) -> str | None:
    """Elige la miniatura de mayor calidad disponible."""
    if not thumbnails:
        return None
    for key in ("maxres", "standard", "high", "medium", "default"):
        entry = thumbnails.get(key)
        if isinstance(entry, dict) and entry.get("url"):
            return str(entry["url"])
    return None


def map_channel(item: dict[str, Any]) -> dict[str, Any]:
    snippet = item.get("snippet") or {}
    stats = item.get("statistics") or {}
    content = item.get("contentDetails") or {}
    related = content.get("relatedPlaylists") or {}

    hidden = bool(stats.get("hiddenSubscriberCount", False))
    subscriber_count = None if hidden else to_int(stats.get("subscriberCount"))

    handle = snippet.get("customUrl") or ""
    handle = handle.lstrip("@") or None

    return {
        "youtube_channel_id": str(item.get("id", "")),
        "handle": handle,
        "title": str(snippet.get("title") or "Canal sin título"),
        "description": snippet.get("description") or None,
        "thumbnail_url": pick_thumbnail(snippet.get("thumbnails")),
        "subscriber_count": subscriber_count,
        "subscriber_count_hidden": hidden,
        "video_count": to_int(stats.get("videoCount")),
        "view_count": to_int(stats.get("viewCount")),
        "country": (snippet.get("country") or None),
        "published_at": parse_iso_datetime(snippet.get("publishedAt")),
        "uploads_playlist_id": related.get("uploads") or None,
    }


def map_playlist_item_to_video_id(item: dict[str, Any]) -> str | None:
    content = item.get("contentDetails") or {}
    video_id = content.get("videoId")
    if video_id:
        return str(video_id)
    resource = (item.get("snippet") or {}).get("resourceId") or {}
    return str(resource["videoId"]) if resource.get("videoId") else None


def map_video(item: dict[str, Any]) -> dict[str, Any]:
    snippet = item.get("snippet") or {}
    stats = item.get("statistics") or {}
    content = item.get("contentDetails") or {}
    live = snippet.get("liveBroadcastContent") or "none"

    # La API omite `commentCount` cuando los comentarios están desactivados.
    raw_comment_count = stats.get("commentCount")
    comments_disabled = raw_comment_count is None and bool(stats)

    return {
        "youtube_video_id": str(item.get("id", "")),
        "title": str(snippet.get("title") or "Vídeo sin título"),
        "description": snippet.get("description") or None,
        "published_at": parse_iso_datetime(snippet.get("publishedAt")),
        "thumbnail_url": pick_thumbnail(snippet.get("thumbnails")),
        "duration_seconds": parse_duration(content.get("duration")),
        "view_count": to_int(stats.get("viewCount")),
        "like_count": to_int(stats.get("likeCount")),
        # `dislikeCount` ya no es público: se trata como no disponible.
        "comment_count": to_int(raw_comment_count),
        "tags": list(snippet.get("tags") or []) or None,
        "category_id": str(snippet.get("categoryId")) if snippet.get("categoryId") else None,
        "is_live_content": live in {"live", "upcoming"} or bool(item.get("liveStreamingDetails")),
        "live_broadcast_content": str(live),
        "comments_disabled": comments_disabled,
    }


def _map_comment_snippet(
    comment_id: str,
    snippet: dict[str, Any],
    *,
    is_top_level: bool,
    parent_comment_id: str | None,
    reply_count: int = 0,
) -> dict[str, Any]:
    text = snippet.get("textOriginal") or snippet.get("textDisplay") or ""
    return {
        "youtube_comment_id": comment_id,
        "parent_comment_id": parent_comment_id,
        "text": str(text),
        "published_at": parse_iso_datetime(snippet.get("publishedAt")),
        "updated_at_source": parse_iso_datetime(snippet.get("updatedAt")),
        "like_count": to_int(snippet.get("likeCount")) or 0,
        "reply_count": reply_count,
        "is_top_level": is_top_level,
        # Sólo se guarda un hash: nunca el nombre público ni la foto del autor.
        "author_hash": hash_author_id(
            (snippet.get("authorChannelId") or {}).get("value")
            or snippet.get("authorChannelUrl")
            or None
        ),
    }


def map_comment_thread(item: dict[str, Any], *, include_replies: bool) -> list[dict[str, Any]]:
    """Convierte un `commentThread` en el comentario principal y sus respuestas."""
    out: list[dict[str, Any]] = []
    thread_snippet = item.get("snippet") or {}
    top = thread_snippet.get("topLevelComment") or {}
    top_id = str(top.get("id") or item.get("id") or "")
    if not top_id:
        return out

    out.append(
        _map_comment_snippet(
            top_id,
            top.get("snippet") or {},
            is_top_level=True,
            parent_comment_id=None,
            reply_count=to_int(thread_snippet.get("totalReplyCount")) or 0,
        )
    )

    if include_replies:
        replies = (item.get("replies") or {}).get("comments") or []
        for reply in replies:
            reply_id = str(reply.get("id") or "")
            if not reply_id:
                continue
            out.append(
                _map_comment_snippet(
                    reply_id,
                    reply.get("snippet") or {},
                    is_top_level=False,
                    parent_comment_id=top_id,
                )
            )
    return out


def map_comment_reply(item: dict[str, Any], parent_id: str) -> dict[str, Any] | None:
    """Convierte un elemento de `comments.list` en una respuesta.

    Devuelve `None` si el elemento no trae identificador: nunca se inventa uno.
    """
    reply_id = str(item.get("id") or "")
    if not reply_id:
        return None
    return _map_comment_snippet(
        reply_id,
        item.get("snippet") or {},
        is_top_level=False,
        parent_comment_id=parent_id,
    )


__all__ = [
    "map_channel",
    "map_comment_reply",
    "map_comment_thread",
    "map_playlist_item_to_video_id",
    "map_video",
    "parse_duration",
    "parse_iso_datetime",
    "pick_thumbnail",
    "to_int",
]
