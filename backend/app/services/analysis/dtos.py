"""Estructuras intermedias que circulan entre las etapas del pipeline.

Son objetos en memoria (no filas de la base de datos) para que cada etapa se
pueda probar de forma aislada sin necesidad de PostgreSQL.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.services.analysis.performance import ChannelBaseline, VideoPerformance
from app.services.analysis.quality import DataQuality


@dataclass
class AnalysedComment:
    """Un comentario tras pasar por limpieza, sentimiento, intención y aspectos."""

    comment_id: uuid.UUID
    video_id: uuid.UUID
    youtube_video_id: str
    text: str
    normalised: str
    published_at: datetime | None
    like_count: int
    language: str
    sentiment_label: str
    sentiment_score: float
    sentiment_confidence: float
    intents: list[str]
    aspects: list[str]
    keywords: list[str]
    toxicity: float | None
    is_question: bool
    is_request: bool
    is_spam: bool
    is_duplicate: bool
    author_hash: str | None = None
    cluster_key: str | None = None
    embedding: list[float] | None = None

    @property
    def is_usable(self) -> bool:
        """Un comentario entra en las conclusiones si no es spam ni duplicado."""
        return not self.is_spam and not self.is_duplicate


@dataclass
class TopicSummary:
    """Tema detectado con todas sus métricas agregadas."""

    cluster_key: str
    label_es: str
    description_es: str
    comment_count: int
    unique_video_count: int
    positive_count: int
    neutral_count: int
    negative_count: int
    request_count: int
    question_count: int
    share_of_comments: float
    mentions_per_1000: float
    video_coverage: float
    recent_share: float | None
    previous_share: float | None
    trend_change: float | None
    trend_direction: str
    trend_confidence: float
    trend_note_es: str | None
    coverage_score: float
    confidence_score: float
    confidence_level: str
    confidence_factors: dict[str, float]
    confidence_penalties_es: list[str]
    dominant_video_share: float
    top_aspects: list[str]
    keywords: list[str]
    representative_comments: list[dict[str, Any]]
    centroid: list[float] | None
    is_noise: bool
    video_ids: set[str] = field(default_factory=set)
    association: dict[str, Any] = field(default_factory=dict)
    toxic_count: int = 0
    spam_share: float = 0.0
    mean_sentiment_confidence: float = 0.5
    ai_generated_label: bool = False

    @property
    def negative_share(self) -> float:
        total = self.positive_count + self.neutral_count + self.negative_count
        return self.negative_count / total if total else 0.0

    @property
    def positive_share(self) -> float:
        total = self.positive_count + self.neutral_count + self.negative_count
        return self.positive_count / total if total else 0.0


@dataclass
class AnalysisContext:
    """Todo lo que necesita el motor de recomendaciones."""

    run_id: uuid.UUID
    channel_title: str
    comments: list[AnalysedComment]
    topics: list[TopicSummary]
    baseline: ChannelBaseline
    performances: dict[str, VideoPerformance]
    video_titles: dict[str, str]
    quality: DataQuality
    sentiment_counts: dict[str, int] = field(default_factory=dict)
    total_videos: int = 0
    total_comments_analysed: int = 0
    is_demo: bool = False

    @property
    def usable_comments(self) -> list[AnalysedComment]:
        return [c for c in self.comments if c.is_usable]


__all__ = ["AnalysedComment", "AnalysisContext", "TopicSummary"]
