"""Estimación de consumo de cuota de la YouTube Data API.

Los costes son los publicados por Google para la v3. La aplicación **no** conoce
la cuota real restante del proyecto de Google: sólo lleva un registro propio y
aproximado de lo que ella misma ha consumido.
"""

from __future__ import annotations

from typing import Final

#: Coste en unidades de cuota por llamada, por categoría de endpoint.
QUOTA_COST: Final[dict[str, int]] = {
    "channels.list": 1,
    "playlistItems.list": 1,
    "videos.list": 1,
    "commentThreads.list": 1,
    "comments.list": 1,
    "search.list": 100,
}

#: Cuota diaria por defecto de un proyecto nuevo de Google Cloud.
DEFAULT_DAILY_QUOTA: Final[int] = 10_000


def estimate_cost(endpoint: str, calls: int = 1) -> int:
    """Unidades estimadas para `calls` llamadas a `endpoint`."""
    return QUOTA_COST.get(endpoint, 1) * max(0, calls)


def estimate_analysis_cost(
    max_videos: int,
    max_comments_per_video: int,
    *,
    include_replies: bool = False,
    page_size: int = 100,
) -> int:
    """Estimación previa del coste de un análisis completo.

    Se usa para mostrar al usuario el aviso de carga estimada antes de lanzar
    el análisis.
    """
    max_videos = max(0, max_videos)
    max_comments_per_video = max(0, max_comments_per_video)

    # Resolución del canal + lectura de la playlist de subidas.
    cost = estimate_cost("channels.list", 1)
    playlist_pages = _pages(max_videos, page_size=50)
    cost += estimate_cost("playlistItems.list", playlist_pages)

    # Estadísticas de vídeo en lotes de 50.
    cost += estimate_cost("videos.list", _pages(max_videos, page_size=50))

    # Comentarios: una página por cada `page_size` comentarios y vídeo.
    comment_pages_per_video = _pages(max_comments_per_video, page_size=page_size)
    cost += estimate_cost("commentThreads.list", comment_pages_per_video * max_videos)

    if include_replies:
        # Aproximación conservadora: una página de respuestas por cada 5 hilos.
        cost += estimate_cost("comments.list", max(1, comment_pages_per_video) * max_videos)

    return cost


def _pages(total: int, page_size: int) -> int:
    if total <= 0:
        return 0
    return (total + page_size - 1) // page_size


__all__ = [
    "DEFAULT_DAILY_QUOTA",
    "QUOTA_COST",
    "estimate_analysis_cost",
    "estimate_cost",
]
