"""Pipeline determinista de análisis.

Coordina las diez etapas y devuelve un `AnalysisContext` completo. No toca la
base de datos: recibe los datos ya cargados y devuelve objetos en memoria, de
modo que cada etapa se puede probar de forma aislada.
"""

from __future__ import annotations

import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from app.core.config import ALGORITHM_VERSION, settings
from app.core.logging import get_logger
from app.core.privacy import redact_personal_data, truncate_for_display
from app.models.enums import SentimentLabel, TrendDirection
from app.services.analysis.aspects import (
    aspect_label_es,
    build_document_frequency,
    distinctive_keywords,
    extract_aspects,
    top_keywords,
)
from app.services.analysis.clustering import ClusterAssignment, cluster_embeddings
from app.services.analysis.dtos import AnalysedComment, AnalysisContext, TopicSummary
from app.services.analysis.embeddings import (
    EmbeddingBackend,
    build_embedding_backend,
    resize_vector,
)
from app.services.analysis.intents import extract_intents
from app.services.analysis.performance import (
    ChannelBaseline,
    VideoPerformance,
    VideoStats,
    compute_baseline,
    compute_performance,
    topic_performance_association,
    viral_concentration,
)
from app.services.analysis.preprocessing import clean_comment, mark_duplicates
from app.services.analysis.quality import (
    DataQuality,
    finalise_quality,
    language_distribution,
)
from app.services.analysis.sentiment import SentimentBackend, build_sentiment_backend
from app.services.analysis.trends import (
    build_time_windows,
    compute_trend,
    coverage,
    date_coverage_summary,
    dominant_source_share,
    mentions_per_1000,
)

logger = get_logger(__name__)

#: Ejemplos representativos que se guardan por tema.
REPRESENTATIVE_LIMIT = 5


@dataclass
class RawComment:
    """Comentario tal como sale de la base de datos."""

    comment_id: uuid.UUID
    video_id: uuid.UUID
    youtube_video_id: str
    text: str
    published_at: datetime | None
    like_count: int
    author_hash: str | None = None
    is_top_level: bool = True


@dataclass
class RawVideo:
    """Vídeo tal como sale de la base de datos."""

    video_id: uuid.UUID
    youtube_video_id: str
    title: str
    published_at: datetime | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    comments_disabled: bool = False


@dataclass
class PipelineResult:
    """Salida completa del pipeline."""

    context: AnalysisContext
    cluster_assignment: ClusterAssignment
    stage_durations: dict[str, float] = field(default_factory=dict)
    model_config: dict[str, Any] = field(default_factory=dict)


class AnalysisPipeline:
    """Ejecuta las etapas 1-9 del análisis."""

    def __init__(
        self,
        *,
        embedding_backend: EmbeddingBackend | None = None,
        sentiment_backend: SentimentBackend | None = None,
    ) -> None:
        self.embeddings = embedding_backend or build_embedding_backend()
        self.sentiment = sentiment_backend or build_sentiment_backend()

    # -- Punto de entrada --------------------------------------------------

    def run(
        self,
        *,
        run_id: uuid.UUID,
        channel_title: str,
        videos: list[RawVideo],
        comments: list[RawComment],
        sampling_strategy: str = "mixed",
        sampling_buckets: dict[str, int] | None = None,
        videos_with_comments_disabled: int = 0,
        include_replies: bool = False,
        replies_incomplete: bool = False,
        is_demo: bool = False,
        now: datetime | None = None,
    ) -> PipelineResult:
        durations: dict[str, float] = {}

        # --- Etapa 1: validación de datos ---------------------------------
        started = time.perf_counter()
        videos, comments = self._validate(videos, comments)
        durations["validation"] = _elapsed(started)

        # --- Etapa 2-5: limpieza, sentimiento, intención, aspectos --------
        started = time.perf_counter()
        analysed, discarded = self._analyse_comments(comments)
        durations["preprocessing"] = _elapsed(started)

        usable = [c for c in analysed if c.is_usable]

        # --- Etapa 6: embeddings y temas ----------------------------------
        started = time.perf_counter()
        assignment = self._cluster(usable)
        durations["embedding_clustering"] = _elapsed(started)

        # --- Etapa 8: métricas de rendimiento -----------------------------
        started = time.perf_counter()
        baseline, performances = self._performance(videos, now=now)
        durations["performance"] = _elapsed(started)

        # --- Etapa 7 y 9: tendencias y asociaciones -----------------------
        started = time.perf_counter()
        topics = self._build_topics(
            usable,
            assignment,
            performances=performances,
            total_videos=len(videos),
        )
        durations["topics_trends"] = _elapsed(started)

        # --- Calidad de datos ---------------------------------------------
        quality = self._quality(
            videos=videos,
            analysed=analysed,
            usable=usable,
            discarded=discarded,
            assignment=assignment,
            topics=topics,
            sampling_strategy=sampling_strategy,
            sampling_buckets=sampling_buckets or {},
            videos_with_comments_disabled=videos_with_comments_disabled,
            include_replies=include_replies,
            replies_incomplete=replies_incomplete,
            is_demo=is_demo,
        )

        context = AnalysisContext(
            run_id=run_id,
            channel_title=channel_title,
            comments=analysed,
            topics=topics,
            baseline=baseline,
            performances=performances,
            video_titles={v.youtube_video_id: v.title for v in videos},
            quality=quality,
            sentiment_counts=Counter(c.sentiment_label for c in usable),
            total_videos=len(videos),
            total_comments_analysed=len(usable),
            is_demo=is_demo,
        )

        return PipelineResult(
            context=context,
            cluster_assignment=assignment,
            stage_durations=durations,
            model_config={
                "algorithm_version": ALGORITHM_VERSION,
                "embedding_backend": self.embeddings.name,
                "embedding_dim": self.embeddings.dimension,
                "sentiment_backend": type(self.sentiment).__name__,
                "clustering_strategy": assignment.strategy,
                "clustering_parameters": assignment.parameters,
                "toxicity_enabled": settings.enable_toxicity_analysis,
            },
        )

    # -- Etapa 1 -----------------------------------------------------------

    @staticmethod
    def _validate(
        videos: list[RawVideo], comments: list[RawComment]
    ) -> tuple[list[RawVideo], list[RawComment]]:
        """Deduplica y sanea los valores imposibles antes de analizar."""
        seen_videos: set[str] = set()
        clean_videos: list[RawVideo] = []
        for video in videos:
            if video.youtube_video_id in seen_videos:
                continue
            seen_videos.add(video.youtube_video_id)
            # Un contador negativo es dato corrupto: se trata como desconocido.
            if video.view_count is not None and video.view_count < 0:
                video.view_count = None
            if video.like_count is not None and video.like_count < 0:
                video.like_count = None
            if video.comment_count is not None and video.comment_count < 0:
                video.comment_count = None
            clean_videos.append(video)

        known_video_ids = {v.video_id for v in clean_videos}
        seen_comments: set[uuid.UUID] = set()
        clean_comments: list[RawComment] = []
        for comment in comments:
            if comment.comment_id in seen_comments:
                continue
            if comment.video_id not in known_video_ids:
                continue
            seen_comments.add(comment.comment_id)
            comment.like_count = max(0, comment.like_count)
            clean_comments.append(comment)

        return clean_videos, clean_comments

    # -- Etapas 2-5 --------------------------------------------------------

    def _analyse_comments(
        self, comments: list[RawComment]
    ) -> tuple[list[AnalysedComment], dict[str, int]]:
        cleaned = [clean_comment(c.text) for c in comments]
        duplicate_flags = mark_duplicates(cleaned, [c.youtube_video_id for c in comments])

        analysed: list[AnalysedComment] = []
        discarded = {"spam": 0, "duplicate": 0, "empty": 0}

        for raw, clean, is_duplicate in zip(comments, cleaned, duplicate_flags, strict=True):
            sentiment = self.sentiment.analyse(clean.text, emojis=clean.emojis)
            aspects = extract_aspects(clean.normalised)
            intents = extract_intents(
                clean.normalised,
                sentiment_label=sentiment.label,
                toxicity=sentiment.toxicity,
                is_spam=clean.is_spam,
                has_aspect=bool(aspects.aspects),
            )

            if clean.is_spam:
                discarded["spam"] += 1
            elif is_duplicate:
                discarded["duplicate"] += 1
            elif clean.is_empty:
                discarded["empty"] += 1

            analysed.append(
                AnalysedComment(
                    comment_id=raw.comment_id,
                    video_id=raw.video_id,
                    youtube_video_id=raw.youtube_video_id,
                    text=clean.text,
                    normalised=clean.normalised,
                    published_at=raw.published_at,
                    like_count=raw.like_count,
                    language=clean.language,
                    sentiment_label=sentiment.label,
                    sentiment_score=sentiment.score,
                    sentiment_confidence=sentiment.confidence,
                    intents=intents.labels,
                    aspects=aspects.aspects,
                    keywords=aspects.keywords,
                    toxicity=sentiment.toxicity,
                    is_question=intents.is_question,
                    is_request=intents.is_request,
                    is_spam=clean.is_spam,
                    is_duplicate=is_duplicate or clean.is_empty,
                    author_hash=raw.author_hash,
                )
            )
        return analysed, discarded

    # -- Etapa 6 -----------------------------------------------------------

    def _cluster(self, usable: list[AnalysedComment]) -> ClusterAssignment:
        if not usable:
            return ClusterAssignment(labels=[], strategy="none", n_clusters=0, noise_count=0)

        texts = [c.normalised or c.text for c in usable]
        vectors = self.embeddings.encode(texts)
        assignment = cluster_embeddings(vectors)

        target_dim = settings.embedding_dim
        for comment, label, vector in zip(usable, assignment.labels, vectors, strict=True):
            comment.cluster_key = f"c{label}" if label >= 0 else None
            comment.embedding = resize_vector(vector, target_dim)

        # Respaldo por aspectos. El clustering por densidad deja fuera muchos
        # comentarios como ruido; los que mencionan un aspecto reconocible de la
        # taxonomía se agrupan por él para no perder esa evidencia. Los que no
        # tienen aspecto siguen contando como ruido y se informa de ello.
        self._assign_by_aspect(usable)
        return assignment

    @staticmethod
    def _assign_by_aspect(usable: list[AnalysedComment]) -> None:
        """Asigna un tema por aspecto a los comentarios sin grupo semántico."""
        for comment in usable:
            if comment.cluster_key is None and comment.aspects:
                comment.cluster_key = f"a_{comment.aspects[0]}"

    # -- Etapa 8 -----------------------------------------------------------

    @staticmethod
    def _performance(
        videos: list[RawVideo], *, now: datetime | None = None
    ) -> tuple[ChannelBaseline, dict[str, VideoPerformance]]:
        stats = [
            VideoStats(
                video_id=v.youtube_video_id,
                views=v.view_count,
                likes=v.like_count,
                comments=v.comment_count,
                published_at=v.published_at,
                title=v.title,
            )
            for v in videos
        ]
        baseline = compute_baseline(stats)
        performances = {s.video_id: compute_performance(s, baseline, now=now) for s in stats}
        return baseline, performances

    # -- Etapas 7 y 9 ------------------------------------------------------

    def _build_topics(
        self,
        usable: list[AnalysedComment],
        assignment: ClusterAssignment,
        *,
        performances: dict[str, VideoPerformance],
        total_videos: int,
    ) -> list[TopicSummary]:
        if not usable:
            return []

        groups: dict[str, list[AnalysedComment]] = defaultdict(list)
        for comment in usable:
            key = comment.cluster_key or "ruido"
            groups[key].append(comment)

        windows = build_time_windows([c.published_at for c in usable])
        total_comments = len(usable)
        # Frecuencia global: permite quedarse con las palabras que distinguen
        # a cada tema en lugar de las que son comunes a todo el canal.
        corpus_df = build_document_frequency([c.keywords for c in usable])
        topics: list[TopicSummary] = []

        for key, members in groups.items():
            is_noise = key == "ruido"
            video_ids = {c.youtube_video_id for c in members}
            counts_by_video = Counter(c.youtube_video_id for c in members)

            positive = sum(1 for c in members if c.sentiment_label == SentimentLabel.POSITIVE)
            negative = sum(1 for c in members if c.sentiment_label == SentimentLabel.NEGATIVE)
            mixed = sum(1 for c in members if c.sentiment_label == SentimentLabel.MIXED)
            neutral = len(members) - positive - negative - mixed
            # Los comentarios mixtos suman a ambos lados: contienen las dos señales.
            positive += mixed
            negative += mixed

            trend = compute_trend([c.published_at for c in members], windows)
            aspects = top_keywords([c.aspects for c in members], limit=4)
            keywords = distinctive_keywords(
                [c.keywords for c in members], corpus_df, total_comments, limit=8
            )
            association = (
                topic_performance_association(video_ids, performances) if not is_noise else {}
            )

            confidence_source = float(
                np.mean([c.sentiment_confidence for c in members]) if members else 0.5
            )
            spam_share = 0.0  # `usable` ya excluye spam y duplicados.

            label_es, description_es = self._label_for(key, aspects, keywords, is_noise)

            topics.append(
                TopicSummary(
                    cluster_key=key,
                    label_es=label_es,
                    description_es=description_es,
                    comment_count=len(members),
                    unique_video_count=len(video_ids),
                    positive_count=positive,
                    neutral_count=max(0, neutral),
                    negative_count=negative,
                    request_count=sum(1 for c in members if c.is_request),
                    question_count=sum(1 for c in members if c.is_question),
                    share_of_comments=len(members) / total_comments,
                    mentions_per_1000=mentions_per_1000(len(members), total_comments),
                    video_coverage=coverage(len(video_ids), total_videos),
                    recent_share=trend.recent_share,
                    previous_share=trend.previous_share,
                    trend_change=trend.change,
                    trend_direction=trend.direction,
                    trend_confidence=trend.confidence,
                    trend_note_es=trend.note_es,
                    coverage_score=coverage(len(video_ids), total_videos),
                    confidence_score=0.0,
                    confidence_level="baja",
                    confidence_factors={},
                    confidence_penalties_es=[],
                    dominant_video_share=dominant_source_share(counts_by_video),
                    top_aspects=aspects,
                    keywords=keywords,
                    representative_comments=self._representatives(members),
                    centroid=self._centroid_for(key, assignment),
                    is_noise=is_noise,
                    video_ids=video_ids,
                    association=association,
                    toxic_count=sum(1 for c in members if (c.toxicity or 0) >= 0.6),
                    spam_share=spam_share,
                    mean_sentiment_confidence=round(confidence_source, 4),
                )
            )

        topics.sort(key=lambda t: (t.is_noise, -t.comment_count))
        self._disambiguate_labels(topics)
        return topics

    @staticmethod
    def _disambiguate_labels(topics: list[TopicSummary]) -> None:
        """Evita que dos temas distintos compartan la misma etiqueta.

        Dos grupos semánticos pueden girar en torno al mismo aspecto (por
        ejemplo dos formas distintas de hablar del audio). Mostrarlos con el
        mismo nombre haría el panel ilegible, así que el segundo y siguientes se
        matizan con sus palabras clave más distintivas.
        """
        seen: dict[str, int] = {}
        for topic in topics:
            if topic.is_noise:
                continue
            base = topic.label_es
            count = seen.get(base, 0)
            seen[base] = count + 1
            if count == 0:
                continue

            distinctive = [k for k in topic.keywords if k.lower() not in base.lower()][:2]
            if distinctive:
                topic.label_es = f"{base}: {', '.join(distinctive)}"
            elif topic.top_aspects[1:2]:
                topic.label_es = f"{base} y {aspect_label_es(topic.top_aspects[1]).lower()}"
            else:
                topic.label_es = f"{base} ({count + 1})"

    @staticmethod
    def _centroid_for(key: str, assignment: ClusterAssignment) -> list[float] | None:
        if not key.startswith("c") or not key[1:].isdigit():
            return None
        centroid = assignment.centroids.get(int(key[1:]))
        if centroid is None:
            return None
        return resize_vector(centroid, settings.embedding_dim)

    @staticmethod
    def _label_for(
        key: str, aspects: list[str], keywords: list[str], is_noise: bool
    ) -> tuple[str, str]:
        """Etiqueta determinista del tema (el LLM puede reescribirla después)."""
        if is_noise:
            return (
                "Comentarios sin tema claro",
                "Comentarios que no encajan en ningún grupo temático identificable.",
            )
        if key.startswith("a_"):
            aspect = key[2:]
            return (
                aspect_label_es(aspect),
                f"Comentarios que mencionan {aspect_label_es(aspect).lower()}.",
            )
        if aspects:
            label = aspect_label_es(aspects[0])
            if len(aspects) > 1:
                extra = ", ".join(aspect_label_es(a).lower() for a in aspects[1:3])
                return label, f"Comentarios sobre {label.lower()}, con menciones a {extra}."
            return label, f"Comentarios centrados en {label.lower()}."
        if keywords:
            label = ", ".join(keywords[:3]).capitalize()
            return label, f"Comentarios que giran en torno a: {', '.join(keywords[:5])}."
        return "Tema sin etiqueta clara", "Grupo de comentarios semánticamente próximos."

    @staticmethod
    def _representatives(members: list[AnalysedComment]) -> list[dict[str, Any]]:
        """Ejemplos anonimizados y variados en sentimiento del tema."""
        by_sentiment: dict[str, list[AnalysedComment]] = defaultdict(list)
        for comment in members:
            by_sentiment[comment.sentiment_label].append(comment)

        chosen: list[AnalysedComment] = []
        for label in (
            SentimentLabel.POSITIVE,
            SentimentLabel.NEGATIVE,
            SentimentLabel.NEUTRAL,
            SentimentLabel.MIXED,
        ):
            bucket = sorted(by_sentiment.get(label, []), key=lambda c: -c.like_count)
            if bucket:
                chosen.append(bucket[0])

        remaining = sorted((c for c in members if c not in chosen), key=lambda c: -c.like_count)
        chosen.extend(remaining[: max(0, REPRESENTATIVE_LIMIT - len(chosen))])

        return [
            {
                "text": truncate_for_display(redact_personal_data(c.text)),
                "sentiment": c.sentiment_label,
                "likes": c.like_count,
                "video_id": c.youtube_video_id,
                "published_at": c.published_at.isoformat() if c.published_at else None,
            }
            for c in chosen[:REPRESENTATIVE_LIMIT]
        ]

    # -- Calidad -----------------------------------------------------------

    @staticmethod
    def _quality(
        *,
        videos: list[RawVideo],
        analysed: list[AnalysedComment],
        usable: list[AnalysedComment],
        discarded: dict[str, int],
        assignment: ClusterAssignment,
        topics: list[TopicSummary],
        sampling_strategy: str,
        sampling_buckets: dict[str, int],
        videos_with_comments_disabled: int,
        include_replies: bool,
        replies_incomplete: bool,
        is_demo: bool,
    ) -> DataQuality:
        counts_by_video = Counter(c.youtube_video_id for c in usable)
        videos_with_comments = set(counts_by_video)
        noise_topics = [t for t in topics if t.is_noise]
        noise_count = noise_topics[0].comment_count if noise_topics else 0

        quality = DataQuality(
            videos_sampled=len(videos),
            comments_sampled=len(analysed),
            comments_analysed=len(usable),
            comments_discarded_spam=discarded.get("spam", 0),
            comments_discarded_duplicate=discarded.get("duplicate", 0),
            comments_discarded_empty=discarded.get("empty", 0),
            videos_with_comments_disabled=videos_with_comments_disabled
            or sum(1 for v in videos if v.comments_disabled),
            include_replies=include_replies,
            replies_incomplete=replies_incomplete,
            videos_with_zero_comments=sum(
                1
                for v in videos
                if not v.comments_disabled and v.youtube_video_id not in videos_with_comments
            ),
            videos_missing_views=sum(1 for v in videos if v.view_count is None),
            videos_missing_likes=sum(1 for v in videos if v.like_count is None),
            sampling_strategy=sampling_strategy,
            sampling_buckets=sampling_buckets,
            date_coverage=date_coverage_summary([c.published_at for c in usable]),
            language_distribution=language_distribution([c.language for c in usable]),
            dominant_video_share=dominant_source_share(counts_by_video),
            viral_view_concentration=viral_concentration([v.view_count for v in videos]),
            clustering_strategy=assignment.strategy,
            topics_found=sum(1 for t in topics if not t.is_noise),
            noise_share=round(noise_count / len(usable), 4) if usable else 0.0,
            ai_used=False,
            ai_provider=settings.ai_provider,
            algorithm_version=ALGORITHM_VERSION,
            embedding_backend=settings.embedding_backend,
            sentiment_backend=settings.sentiment_backend,
            is_demo=is_demo,
        )
        return finalise_quality(quality)


def apply_topic_confidence(context: AnalysisContext) -> None:
    """Rellena la confianza de cada tema a partir de su evidencia."""
    from app.services.recommendations.confidence import ConfidenceInput, compute_confidence

    for topic in context.topics:
        association = topic.association or {}
        outcome = compute_confidence(
            ConfidenceInput(
                supporting_comments=topic.comment_count,
                supporting_videos=topic.unique_video_count,
                total_videos=context.total_videos,
                total_comments=context.total_comments_analysed,
                dominant_video_share=topic.dominant_video_share,
                trend_confidence=topic.trend_confidence,
                trend_consistent=topic.trend_direction
                in (TrendDirection.RISING, TrendDirection.FALLING),
                classifier_confidence=topic.mean_sentiment_confidence,
                cluster_quality=1.0 - min(1.0, topic.spam_share * 2),
                recency_share=topic.recent_share or 0.0,
                spam_or_duplicate_share=topic.spam_share,
                association_available=bool(association.get("available")),
                association_strength=float(association.get("strength") or 0.0),
            )
        )
        topic.confidence_score = outcome.score
        topic.confidence_level = outcome.level
        topic.confidence_factors = outcome.factors
        topic.confidence_penalties_es = outcome.penalties_es + outcome.caps_es


def _elapsed(started: float) -> float:
    return round(time.perf_counter() - started, 4)


__all__ = [
    "REPRESENTATIVE_LIMIT",
    "AnalysisPipeline",
    "PipelineResult",
    "RawComment",
    "RawVideo",
    "apply_topic_confidence",
]
