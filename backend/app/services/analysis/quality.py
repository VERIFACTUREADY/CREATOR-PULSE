"""Calidad de los datos: qué sabe y qué no sabe el análisis.

Esta sección es la que permite al creador distinguir un patrón real de una
anécdota. Se calcula siempre, incluso cuando el análisis termina con datos
insuficientes.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

#: Umbrales que determinan la puntuación global de calidad.
GOOD_COMMENT_SAMPLE = 300
GOOD_VIDEO_SAMPLE = 10
MIN_COMMENTS_FOR_TOPICS = 30
MIN_VIDEOS_FOR_ASSOCIATION = 4


@dataclass
class DataQuality:
    """Resumen de la calidad y las limitaciones de la muestra."""

    videos_sampled: int = 0
    comments_sampled: int = 0
    comments_analysed: int = 0
    comments_discarded_spam: int = 0
    comments_discarded_duplicate: int = 0
    comments_discarded_empty: int = 0
    videos_with_comments_disabled: int = 0
    videos_with_zero_comments: int = 0
    videos_missing_views: int = 0
    videos_missing_likes: int = 0
    sampling_strategy: str = "mixed"
    sampling_buckets: dict[str, int] = field(default_factory=dict)
    date_coverage: dict[str, Any] = field(default_factory=dict)
    language_distribution: dict[str, int] = field(default_factory=dict)
    dominant_video_share: float = 0.0
    viral_view_concentration: float = 0.0
    clustering_strategy: str = "none"
    topics_found: int = 0
    noise_share: float = 0.0
    ai_used: bool = False
    ai_provider: str = "none"
    algorithm_version: str = ""
    embedding_backend: str = ""
    sentiment_backend: str = ""
    is_demo: bool = False
    score: float = 0.0
    level: str = "baja"
    warnings_es: list[str] = field(default_factory=list)
    biases_es: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "videos_sampled": self.videos_sampled,
            "comments_sampled": self.comments_sampled,
            "comments_analysed": self.comments_analysed,
            "comments_discarded_spam": self.comments_discarded_spam,
            "comments_discarded_duplicate": self.comments_discarded_duplicate,
            "comments_discarded_empty": self.comments_discarded_empty,
            "videos_with_comments_disabled": self.videos_with_comments_disabled,
            "videos_with_zero_comments": self.videos_with_zero_comments,
            "videos_missing_views": self.videos_missing_views,
            "videos_missing_likes": self.videos_missing_likes,
            "sampling_strategy": self.sampling_strategy,
            "sampling_buckets": self.sampling_buckets,
            "date_coverage": self.date_coverage,
            "language_distribution": self.language_distribution,
            "dominant_video_share": self.dominant_video_share,
            "viral_view_concentration": self.viral_view_concentration,
            "clustering_strategy": self.clustering_strategy,
            "topics_found": self.topics_found,
            "noise_share": self.noise_share,
            "ai_used": self.ai_used,
            "ai_provider": self.ai_provider,
            "algorithm_version": self.algorithm_version,
            "embedding_backend": self.embedding_backend,
            "sentiment_backend": self.sentiment_backend,
            "is_demo": self.is_demo,
            "score": self.score,
            "level": self.level,
            "warnings_es": self.warnings_es,
            "biases_es": self.biases_es,
        }


def language_distribution(languages: list[str]) -> dict[str, int]:
    counter = Counter(lang or "und" for lang in languages)
    return dict(counter.most_common())


def finalise_quality(quality: DataQuality) -> DataQuality:
    """Calcula la puntuación global y redacta avisos y sesgos en español."""
    warnings: list[str] = []
    biases: list[str] = []

    # --- Puntuación (0-1) ---------------------------------------------
    comment_factor = min(1.0, quality.comments_analysed / GOOD_COMMENT_SAMPLE)
    video_factor = min(1.0, quality.videos_sampled / GOOD_VIDEO_SAMPLE)
    coverage_factor = 1.0 - min(0.6, quality.dominant_video_share)
    cleanliness = 1.0
    total_sampled = max(1, quality.comments_sampled)
    discarded = (
        quality.comments_discarded_spam
        + quality.comments_discarded_duplicate
        + quality.comments_discarded_empty
    )
    cleanliness -= min(0.5, discarded / total_sampled)

    score = 0.4 * comment_factor + 0.3 * video_factor + 0.15 * coverage_factor + 0.15 * cleanliness
    quality.score = round(max(0.0, min(1.0, score)), 3)
    quality.level = "alta" if quality.score >= 0.7 else "media" if quality.score >= 0.4 else "baja"

    # --- Avisos --------------------------------------------------------
    if quality.comments_analysed < MIN_COMMENTS_FOR_TOPICS:
        warnings.append(
            f"Sólo se han podido analizar {quality.comments_analysed} comentarios. "
            "Los temas detectados son orientativos y no deben tomarse como un patrón del canal."
        )
    if quality.videos_sampled < MIN_VIDEOS_FOR_ASSOCIATION:
        warnings.append(
            f"Se han analizado {quality.videos_sampled} vídeos. Con tan pocos vídeos no se "
            "pueden asociar temas con el rendimiento de forma fiable."
        )
    if quality.videos_with_comments_disabled:
        warnings.append(
            f"{quality.videos_with_comments_disabled} vídeo(s) tienen los comentarios "
            "desactivados y no aportan feedback."
        )
    if quality.videos_with_zero_comments:
        warnings.append(
            f"{quality.videos_with_zero_comments} vídeo(s) no tienen comentarios públicos."
        )
    if quality.videos_missing_views:
        warnings.append(
            f"{quality.videos_missing_views} vídeo(s) no exponen sus visualizaciones públicas."
        )
    if quality.clustering_strategy == "keyword":
        warnings.append(
            "No había muestra suficiente para agrupar comentarios por significado. "
            "Los temas se han agregado por palabras clave y aspectos."
        )
    if quality.noise_share > 0.5 and quality.topics_found > 0:
        warnings.append(
            f"El {quality.noise_share:.0%} de los comentarios no encaja en ningún tema claro."
        )

    # --- Sesgos --------------------------------------------------------
    if quality.dominant_video_share >= 0.5:
        biases.append(
            f"El {quality.dominant_video_share:.0%} de los comentarios analizados procede de un "
            "solo vídeo, así que la muestra refleja sobre todo la reacción a ese vídeo."
        )
    if quality.viral_view_concentration >= 0.5:
        biases.append(
            f"Un único vídeo concentra el {quality.viral_view_concentration:.0%} de las "
            "visualizaciones. Las medianas del canal están dominadas por ese vídeo."
        )
    if quality.sampling_strategy == "relevant":
        biases.append(
            "La muestra prioriza los comentarios más votados, que suelen ser más positivos "
            "y más antiguos que el conjunto real."
        )
    if quality.sampling_strategy == "recent":
        biases.append(
            "La muestra prioriza los comentarios recientes, así que refleja mejor la reacción "
            "a los últimos vídeos que la opinión histórica de la audiencia."
        )
    if quality.sampling_strategy == "mixed":
        biases.append(
            "La muestra combina comentarios recientes y populares. Aun así, no es una muestra "
            "aleatoria de todos los comentarios del canal."
        )
    languages = quality.language_distribution
    if languages:
        total_langs = sum(languages.values())
        top_lang, top_count = next(iter(languages.items()))
        if total_langs and top_count / total_langs < 0.6:
            biases.append(
                "Los comentarios están repartidos entre varios idiomas, lo que puede reducir "
                "la precisión de la clasificación de sentimiento."
            )
        if top_lang == "und" and top_count / max(1, total_langs) > 0.3:
            biases.append(
                "Una parte importante de los comentarios es demasiado corta para detectar "
                "su idioma con fiabilidad."
            )
    span = quality.date_coverage.get("span_days")
    if isinstance(span, (int, float)) and span < 7:
        biases.append(
            "Todos los comentarios analizados son de un periodo muy corto: no se puede "
            "distinguir una tendencia de una reacción puntual."
        )
    if quality.is_demo:
        biases.append(
            "Estos son datos de demostración generados para probar el producto. "
            "No corresponden a ningún canal real."
        )

    quality.warnings_es = warnings
    quality.biases_es = biases
    return quality


__all__ = [
    "GOOD_COMMENT_SAMPLE",
    "GOOD_VIDEO_SAMPLE",
    "MIN_COMMENTS_FOR_TOPICS",
    "MIN_VIDEOS_FOR_ASSOCIATION",
    "DataQuality",
    "finalise_quality",
    "language_distribution",
]
