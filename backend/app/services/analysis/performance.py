"""Etapa 8 del pipeline: métricas de rendimiento de vídeo.

Se usan medianas en lugar de medias porque un único vídeo viral distorsiona la
media del canal. Todas las divisiones están protegidas frente a cero y los
vídeos muy recientes se marcan con una advertencia de edad, ya que aún no han
acumulado sus visualizaciones.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

#: Días por debajo de los cuales un vídeo se considera demasiado reciente para
#: compararlo directamente con el resto del canal.
YOUNG_VIDEO_DAYS = 7.0
#: Umbrales sobre la mediana del canal para clasificar el rendimiento.
OVERPERFORM_THRESHOLD = 1.25
UNDERPERFORM_THRESHOLD = 0.75


@dataclass(slots=True)
class VideoStats:
    """Entrada mínima para calcular métricas de un vídeo."""

    video_id: str
    views: int | None
    likes: int | None
    comments: int | None
    published_at: datetime | None
    title: str = ""


@dataclass(slots=True)
class VideoPerformance:
    """Métricas derivadas de un vídeo respecto al canal."""

    video_id: str
    likes_per_1000_views: float | None = None
    comments_per_1000_views: float | None = None
    engagement_actions_per_1000_views: float | None = None
    views_relative_to_median: float | None = None
    likes_relative_to_median: float | None = None
    comments_relative_to_median: float | None = None
    age_adjusted_view_velocity: float | None = None
    age_days: float | None = None
    performance_band: str = "normal"
    age_caveat: bool = False


@dataclass
class ChannelBaseline:
    """Referencias robustas del canal calculadas con medianas."""

    median_views: float = 0.0
    median_likes: float = 0.0
    median_comments: float = 0.0
    median_likes_per_1000: float = 0.0
    median_comments_per_1000: float = 0.0
    video_count: int = 0
    notes: list[str] = field(default_factory=list)


def safe_ratio(numerator: float | int | None, denominator: float | int | None) -> float | None:
    """División protegida: devuelve `None` si el denominador no es utilizable."""
    if numerator is None or denominator is None:
        return None
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def per_1000(count: int | None, views: int | None) -> float | None:
    """Métrica por cada 1.000 visualizaciones."""
    ratio = safe_ratio(count, views)
    return None if ratio is None else round(ratio * 1000.0, 3)


def _median(values: list[float]) -> float:
    usable = [v for v in values if v is not None]
    return float(statistics.median(usable)) if usable else 0.0


def age_days(published_at: datetime | None, *, now: datetime | None = None) -> float | None:
    if published_at is None:
        return None
    reference = now or datetime.now(UTC)
    published = published_at if published_at.tzinfo else published_at.replace(tzinfo=UTC)
    delta = (reference - published).total_seconds() / 86400.0
    return round(max(0.0, delta), 3)


def compute_baseline(videos: list[VideoStats]) -> ChannelBaseline:
    """Calcula las medianas del canal sobre los vídeos analizados."""
    if not videos:
        return ChannelBaseline(notes=["No hay vídeos analizados."])

    views = [float(v.views) for v in videos if v.views is not None]
    likes = [float(v.likes) for v in videos if v.likes is not None]
    comments = [float(v.comments) for v in videos if v.comments is not None]

    likes_ratio = [r for r in (per_1000(v.likes, v.views) for v in videos) if r is not None]
    comments_ratio = [r for r in (per_1000(v.comments, v.views) for v in videos) if r is not None]

    notes: list[str] = []
    if len(videos) < 5:
        notes.append(
            "La mediana del canal se ha calculado con menos de 5 vídeos: "
            "las comparaciones relativas son orientativas."
        )
    if not views:
        notes.append("Ningún vídeo tiene visualizaciones públicas disponibles.")

    return ChannelBaseline(
        median_views=_median(views),
        median_likes=_median(likes),
        median_comments=_median(comments),
        median_likes_per_1000=_median(likes_ratio),
        median_comments_per_1000=_median(comments_ratio),
        video_count=len(videos),
        notes=notes,
    )


def compute_performance(
    video: VideoStats, baseline: ChannelBaseline, *, now: datetime | None = None
) -> VideoPerformance:
    """Calcula las métricas de un vídeo frente a la referencia del canal."""
    likes_1k = per_1000(video.likes, video.views)
    comments_1k = per_1000(video.comments, video.views)

    engagement_1k: float | None = None
    if likes_1k is not None or comments_1k is not None:
        engagement_1k = round((likes_1k or 0.0) + (comments_1k or 0.0), 3)

    age = age_days(video.published_at, now=now)
    velocity: float | None = None
    if video.views is not None and age is not None:
        # Se suma medio día para que un vídeo de minutos no dé un valor infinito.
        velocity = round(float(video.views) / max(0.5, age), 2)

    views_rel = _relative(video.views, baseline.median_views)
    likes_rel = _relative(video.likes, baseline.median_likes)
    comments_rel = _relative(video.comments, baseline.median_comments)

    band = "normal"
    if views_rel is not None:
        if views_rel >= OVERPERFORM_THRESHOLD:
            band = "por_encima"
        elif views_rel <= UNDERPERFORM_THRESHOLD:
            band = "por_debajo"

    caveat = age is not None and age < YOUNG_VIDEO_DAYS
    if caveat:
        # Un vídeo muy reciente no es comparable: no se le asigna banda.
        band = "reciente"

    return VideoPerformance(
        video_id=video.video_id,
        likes_per_1000_views=likes_1k,
        comments_per_1000_views=comments_1k,
        engagement_actions_per_1000_views=engagement_1k,
        views_relative_to_median=views_rel,
        likes_relative_to_median=likes_rel,
        comments_relative_to_median=comments_rel,
        age_adjusted_view_velocity=velocity,
        age_days=age,
        performance_band=band,
        age_caveat=caveat,
    )


def _relative(value: int | None, median: float) -> float | None:
    ratio = safe_ratio(value, median)
    return None if ratio is None else round(ratio, 3)


def topic_performance_association(
    topic_video_ids: set[str],
    performances: dict[str, VideoPerformance],
) -> dict[str, Any]:
    """Asocia un tema con el rendimiento de los vídeos donde aparece.

    Devuelve una **asociación**, nunca una relación causal: los mismos datos
    son compatibles con que el tema atraiga público o con que el público que ya
    vio el vídeo comente sobre ese tema.
    """
    with_topic = [
        p for vid, p in performances.items() if vid in topic_video_ids and not p.age_caveat
    ]
    without_topic = [
        p for vid, p in performances.items() if vid not in topic_video_ids and not p.age_caveat
    ]

    if len(with_topic) < 2 or len(without_topic) < 2:
        return {
            "available": False,
            "reason_es": (
                "No hay suficientes vídeos comparables para estimar una asociación "
                "entre este tema y el rendimiento."
            ),
            "videos_with_topic": len(with_topic),
            "videos_without_topic": len(without_topic),
        }

    def median_of(items: list[VideoPerformance], attr: str) -> float:
        values = [getattr(p, attr) for p in items if getattr(p, attr) is not None]
        return float(statistics.median(values)) if values else 0.0

    with_views = median_of(with_topic, "views_relative_to_median")
    without_views = median_of(without_topic, "views_relative_to_median")
    with_engagement = median_of(with_topic, "engagement_actions_per_1000_views")
    without_engagement = median_of(without_topic, "engagement_actions_per_1000_views")

    view_lift = (
        None if without_views <= 0 else round((with_views - without_views) / without_views, 3)
    )
    engagement_lift = (
        None
        if without_engagement <= 0
        else round((with_engagement - without_engagement) / without_engagement, 3)
    )

    direction = "neutra"
    reference = view_lift if view_lift is not None else engagement_lift
    if reference is not None:
        if reference >= 0.15:
            direction = "positiva"
        elif reference <= -0.15:
            direction = "negativa"

    # Con pocos vídeos la asociación es débil por construcción.
    strength = min(1.0, (len(with_topic) + len(without_topic)) / 16.0)

    return {
        "available": True,
        "direction": direction,
        "view_lift": view_lift,
        "engagement_lift": engagement_lift,
        "videos_with_topic": len(with_topic),
        "videos_without_topic": len(without_topic),
        "strength": round(strength, 3),
        "caveat_es": (
            "Es una asociación estadística sobre una muestra pequeña, "
            "no una relación de causa y efecto."
        ),
    }


def viral_concentration(view_counts: list[int | None]) -> float:
    """Cuota de visualizaciones que aporta el vídeo más visto.

    Por encima de ~0.5 un solo vídeo domina la muestra y las conclusiones
    generales del canal deben leerse con cautela.
    """
    values = [float(v) for v in view_counts if v is not None and v > 0]
    total = sum(values)
    if total <= 0:
        return 0.0
    return round(max(values) / total, 4)


__all__ = [
    "OVERPERFORM_THRESHOLD",
    "UNDERPERFORM_THRESHOLD",
    "YOUNG_VIDEO_DAYS",
    "ChannelBaseline",
    "VideoPerformance",
    "VideoStats",
    "age_days",
    "compute_baseline",
    "compute_performance",
    "per_1000",
    "safe_ratio",
    "topic_performance_association",
    "viral_concentration",
]
