"""Orquestador: conecta la ingesta, el pipeline y la persistencia.

Es lo que ejecuta el worker. Actualiza el estado y el progreso de la ejecución
en cada etapa para que el frontend pueda mostrar el avance.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import ALGORITHM_VERSION, settings
from app.core.errors import AppError
from app.core.logging import bind_analysis_run_id, get_logger
from app.models.entities import (
    AnalysisRun,
    Comment,
    CommentAnalysis,
    ContentIdea,
    Recommendation,
    TopicCluster,
    Video,
    VideoMetric,
)
from app.models.enums import (
    RECOMMENDATION_LABELS_ES,
    AnalysisStatus,
    DataSource,
    IntentLabel,
    SamplingStrategy,
    SentimentLabel,
    TrendDirection,
)
from app.repositories.analysis import AnalysisRunRepository, ApiUsageRepository, ResultsRepository
from app.repositories.channels import ChannelRepository, CommentRepository, VideoRepository
from app.services.ai.enrichment import apply_enrichment
from app.services.ai.providers import build_provider
from app.services.analysis.dtos import AnalysisContext
from app.services.analysis.pipeline import (
    AnalysisPipeline,
    PipelineResult,
    RawComment,
    RawVideo,
    apply_topic_confidence,
)
from app.services.recommendations.generator import generate_recommendations
from app.services.recommendations.ideas import build_ideas_from_recommendations
from app.services.youtube.client import UsageLedger, YouTubeClient
from app.services.youtube.ingest import YouTubeIngestService

logger = get_logger(__name__)


class AnalysisOrchestrator:
    """Ejecuta una `AnalysisRun` de principio a fin."""

    def __init__(
        self,
        session: Session,
        *,
        pipeline: AnalysisPipeline | None = None,
        youtube_client: YouTubeClient | None = None,
    ) -> None:
        self.session = session
        self.runs = AnalysisRunRepository(session)
        self.results = ResultsRepository(session)
        self.channels = ChannelRepository(session)
        self.videos = VideoRepository(session)
        self.comments = CommentRepository(session)
        self.usage = ApiUsageRepository(session)
        self._pipeline = pipeline
        self._youtube_client = youtube_client

    @property
    def pipeline(self) -> AnalysisPipeline:
        if self._pipeline is None:
            self._pipeline = AnalysisPipeline()
        return self._pipeline

    # -- Entrada principal -------------------------------------------------

    def execute(self, run_id: uuid.UUID) -> AnalysisRun:
        """Ejecuta el análisis completo. Nunca propaga excepciones."""
        bind_analysis_run_id(str(run_id))
        run = self.runs.get(run_id)
        if run is None:
            raise AppError(f"La ejecución {run_id} no existe.", code="analisis_no_encontrado")

        started_total = time.perf_counter()
        try:
            return self._execute_inner(run, started_total)
        except AppError as exc:
            logger.warning("analysis_failed", code=exc.code, detail=exc.detail)
            self.runs.mark_failed(run, code=exc.code, message_es=exc.message, detail=exc.detail)
            self.session.commit()
            return run
        except Exception as exc:  # pragma: no cover - defensivo
            logger.exception("analysis_crashed")
            self.runs.mark_failed(
                run,
                code="analisis_fallido",
                message_es=(
                    "El análisis no ha podido completarse por un error inesperado. "
                    "Vuelve a intentarlo; si persiste, reduce el número de vídeos y comentarios."
                ),
                detail=str(exc),
            )
            self.session.commit()
            return run

    def _register_demo_sample(self, run: AnalysisRun, videos: list[Video]) -> dict[str, int]:
        """Construye y ancla la muestra de una ejecución de demostración.

        Los comentarios de demostración ya están cargados, así que aquí no se
        descarga nada: se **elige** un subconjunto aplicando los mismos límites
        y la misma estrategia que en un análisis real. Es determinista, de modo
        que dos ejecuciones con los mismos parámetros ven lo mismo.
        """
        strategy = SamplingStrategy(run.sampling_strategy)
        selections: list[tuple[uuid.UUID, str | None]] = []
        remaining = run.max_comments_per_channel

        for video in videos:
            if remaining <= 0:
                break
            comments = self.comments.list_for_videos([video.id])
            if strategy is SamplingStrategy.RELEVANT:
                bucket = "relevant"
                comments.sort(key=lambda c: (c.like_count, c.id.hex), reverse=True)
            else:
                bucket = "recent" if strategy is SamplingStrategy.RECENT else "demo"
                comments.sort(
                    key=lambda c: (c.published_at is not None, c.published_at, c.id.hex),
                    reverse=True,
                )

            take = min(run.max_comments_per_video, remaining)
            chosen = comments[:take]
            selections.extend((c.id, bucket) for c in chosen)
            remaining -= len(chosen)

        self.comments.register_run_sample(
            run.id, selections, max_comments=run.max_comments_per_channel
        )
        return self.comments.buckets_for_run(run.id)

    def _execute_inner(self, run: AnalysisRun, started_total: float) -> AnalysisRun:
        channel = self.channels.get(run.channel_id)
        if channel is None:
            raise AppError(
                "El canal asociado al análisis ya no existe.", code="canal_no_encontrado"
            )

        is_demo = channel.source == DataSource.DEMO
        ledger = UsageLedger()

        # --- Etapa de descarga --------------------------------------------
        self.runs.set_status(run, AnalysisStatus.FETCHING)
        self.session.commit()

        ingest_stats: dict[str, Any] = {
            "videos_with_comments_disabled": 0,
            "sampling_buckets": {},
            "replies_incomplete": False,
        }

        # Un reintento de una ejecución cuya muestra ya está cerrada no vuelve a
        # descargar nada: la muestra es inmutable, así que repetir la ingesta
        # sólo gastaría cuota para acabar reutilizando lo mismo.
        sample_already_closed = run.sample_finalized_at is not None
        if sample_already_closed:
            logger.info("reusing_finalised_sample", analysis_run_id=str(run.id))
            videos = self.videos.list_recent_for_channel(channel.id, run.max_videos)
            ingest_stats["videos_with_comments_disabled"] = sum(
                1 for v in videos if v.comments_disabled
            )
            ingest_stats["sampling_buckets"] = self.comments.buckets_for_run(run.id)
        elif is_demo:
            # Los datos de demostración ya están en la base de datos, pero la
            # ejecución necesita su propia muestra igual que una real: si no,
            # los límites solicitados no significarían nada en modo demo.
            videos = self.videos.list_recent_for_channel(channel.id, run.max_videos)
            ingest_stats["videos_with_comments_disabled"] = sum(
                1 for v in videos if v.comments_disabled
            )
            ingest_stats["sampling_buckets"] = self._register_demo_sample(run, videos)
        else:
            service = YouTubeIngestService(self.session, client=self._youtube_client, ledger=ledger)
            result = service.ingest_channel(
                channel,
                max_videos=run.max_videos,
                max_comments_per_video=run.max_comments_per_video,
                max_comments_per_channel=run.max_comments_per_channel,
                include_replies=run.include_replies,
                sampling_strategy=SamplingStrategy(run.sampling_strategy),
                run_id=run.id,
            )
            service.touch_channel(channel)
            videos = result.videos
            ingest_stats["videos_with_comments_disabled"] = result.videos_with_comments_disabled
            ingest_stats["sampling_buckets"] = result.sampling_buckets
            ingest_stats["replies_incomplete"] = result.replies_incomplete
            self.usage.record_many(run.id, ledger.records)

        # Sólo la muestra anclada a esta ejecución. Nunca «todo lo que haya en
        # la base de datos para estos vídeos»: eso arrastraría comentarios de
        # ejecuciones anteriores y saltaría los límites solicitados.
        db_comments = self.comments.list_for_run(run.id)

        # Integridad de la muestra: si los vídeos tienen comentarios guardados
        # pero esta ejecución no tiene ninguno asociado, algo ha fallado al
        # registrarla. No es un matiz de calidad, es un resultado no fiable.
        sample_bound = bool(db_comments) or not self.comments.list_for_videos(
            [v.id for v in videos], limit=1
        )

        run.videos_fetched = len(videos)
        run.comments_fetched = len(db_comments)
        self.session.commit()

        # --- Pipeline ------------------------------------------------------
        self.runs.set_status(run, AnalysisStatus.PREPROCESSING)
        self.session.commit()

        pipeline_result = self.pipeline.run(
            run_id=run.id,
            channel_title=channel.title,
            videos=[_to_raw_video(v) for v in videos],
            comments=[_to_raw_comment(c, videos) for c in db_comments],
            sampling_strategy=run.sampling_strategy,
            sampling_buckets=ingest_stats["sampling_buckets"],
            videos_with_comments_disabled=ingest_stats["videos_with_comments_disabled"],
            include_replies=run.include_replies,
            replies_incomplete=ingest_stats["replies_incomplete"],
            sample_bound_to_run=sample_bound,
            is_demo=is_demo,
        )
        context = pipeline_result.context

        self.runs.set_status(run, AnalysisStatus.CLUSTERING)
        self.session.commit()

        apply_topic_confidence(context)

        # --- Recomendaciones ------------------------------------------------
        self.runs.set_status(run, AnalysisStatus.SCORING)
        self.session.commit()

        recommendations = generate_recommendations(context)

        self.runs.set_status(run, AnalysisStatus.RECOMMENDING)
        self.session.commit()

        # --- Enriquecimiento opcional con LLM -------------------------------
        enrichment = apply_enrichment(build_provider(), context.topics, recommendations)
        context.quality.ai_used = enrichment.succeeded
        run.ai_enrichment_succeeded = enrichment.succeeded if enrichment.attempted else None

        ideas = build_ideas_from_recommendations(context, recommendations)

        # --- Persistencia ----------------------------------------------------
        self.results.clear_run_results(run.id)
        self._persist(run, context, pipeline_result, recommendations, ideas)

        run.comments_analysed = context.total_comments_analysed
        run.data_quality = context.quality.to_dict()
        run.summary = build_summary(context, recommendations)
        run.algorithm_version = ALGORITHM_VERSION
        run.ai_provider = settings.ai_provider
        run.ai_model = settings.ai_model_name or None
        run.model_config_snapshot = pipeline_result.model_config
        run.stage_durations = {
            **pipeline_result.stage_durations,
            "total": round(time.perf_counter() - started_total, 4),
        }
        run.source = DataSource.DEMO if is_demo else DataSource.YOUTUBE_API

        self.runs.set_status(run, AnalysisStatus.COMPLETED)
        self.session.commit()

        logger.info(
            "analysis_completed",
            videos=run.videos_fetched,
            comments_analysed=run.comments_analysed,
            topics=len([t for t in context.topics if not t.is_noise]),
            recommendations=len(recommendations),
            duration_seconds=run.stage_durations.get("total"),
        )
        return run

    # -- Persistencia -------------------------------------------------------

    def _persist(
        self,
        run: AnalysisRun,
        context: AnalysisContext,
        pipeline_result: PipelineResult,
        recommendations: list[Any],
        ideas: list[Any],
    ) -> None:
        objects: list[Any] = []

        for comment in context.comments:
            objects.append(
                CommentAnalysis(
                    run_id=run.id,
                    comment_id=comment.comment_id,
                    video_id=comment.video_id,
                    sentiment_label=comment.sentiment_label,
                    sentiment_score=comment.sentiment_score,
                    sentiment_confidence=comment.sentiment_confidence,
                    language=comment.language,
                    intents=comment.intents,
                    aspects=comment.aspects,
                    toxicity_score=comment.toxicity,
                    is_request=comment.is_request,
                    is_question=comment.is_question,
                    cluster_key=comment.cluster_key,
                    embedding=comment.embedding,
                    analysis_version=ALGORITHM_VERSION,
                )
            )

        for topic in context.topics:
            objects.append(
                TopicCluster(
                    run_id=run.id,
                    cluster_key=topic.cluster_key,
                    label_es=topic.label_es,
                    description_es=topic.description_es,
                    comment_count=topic.comment_count,
                    unique_video_count=topic.unique_video_count,
                    positive_count=topic.positive_count,
                    neutral_count=topic.neutral_count,
                    negative_count=topic.negative_count,
                    request_count=topic.request_count,
                    question_count=topic.question_count,
                    share_of_comments=topic.share_of_comments,
                    mentions_per_1000=topic.mentions_per_1000,
                    video_coverage=topic.video_coverage,
                    recent_share=topic.recent_share,
                    previous_share=topic.previous_share,
                    trend_score=topic.trend_change or 0.0,
                    trend_direction=topic.trend_direction,
                    coverage_score=topic.coverage_score,
                    confidence_score=topic.confidence_score,
                    confidence_level=topic.confidence_level,
                    dominant_video_share=topic.dominant_video_share,
                    top_aspects=topic.top_aspects,
                    keywords=topic.keywords,
                    representative_comments=topic.representative_comments,
                    centroid=topic.centroid,
                    is_noise=topic.is_noise,
                    ai_generated_label=topic.ai_generated_label,
                )
            )

        video_by_youtube_id = {
            v.youtube_video_id: v for v in self.videos.list_recent_for_channel(run.channel_id, 200)
        }
        comments_by_video: dict[str, list[Any]] = {}
        for comment in context.usable_comments:
            comments_by_video.setdefault(comment.youtube_video_id, []).append(comment)

        for youtube_video_id, performance in context.performances.items():
            video = video_by_youtube_id.get(youtube_video_id)
            if video is None:
                continue
            members = comments_by_video.get(youtube_video_id, [])
            objects.append(
                VideoMetric(
                    run_id=run.id,
                    video_id=video.id,
                    likes_per_1000_views=performance.likes_per_1000_views,
                    comments_per_1000_views=performance.comments_per_1000_views,
                    engagement_actions_per_1000_views=(
                        performance.engagement_actions_per_1000_views
                    ),
                    views_relative_to_median=performance.views_relative_to_median,
                    likes_relative_to_median=performance.likes_relative_to_median,
                    comments_relative_to_median=performance.comments_relative_to_median,
                    age_adjusted_view_velocity=performance.age_adjusted_view_velocity,
                    age_days=performance.age_days,
                    performance_band=performance.performance_band,
                    age_caveat=performance.age_caveat,
                    analysed_comment_count=len(members),
                    dominant_topics=_dominant_topics_for_video(context, youtube_video_id),
                    sentiment_breakdown=_sentiment_breakdown(members),
                )
            )

        for recommendation in recommendations:
            objects.append(
                Recommendation(
                    run_id=run.id,
                    category=recommendation.category,
                    title_es=recommendation.title_es,
                    explanation_es=recommendation.explanation_es,
                    reason_es=recommendation.reason_es,
                    evidence=recommendation.evidence.to_dict(),
                    confidence_score=recommendation.confidence.score,
                    confidence_level=recommendation.confidence.level,
                    priority=recommendation.priority,
                    suggested_format=recommendation.suggested_format,
                    suggested_hook_es=recommendation.suggested_hook_es,
                    suggested_experiment_es=recommendation.suggested_experiment_es,
                    kpi_es=recommendation.kpi_es,
                    caveat_es=recommendation.caveat_es,
                    topic_cluster_key=recommendation.topic_cluster_key,
                    ai_enriched=run.ai_enrichment_succeeded or False,
                    created_at=datetime.now(UTC),
                )
            )

        for idea in ideas:
            objects.append(
                ContentIdea(
                    run_id=run.id,
                    title_es=idea.title_es,
                    concept_es=idea.concept_es,
                    why_es=idea.why_es,
                    evidence=idea.evidence,
                    suggested_format=idea.suggested_format,
                    hook_es=idea.hook_es,
                    call_to_action_es=idea.call_to_action_es,
                    experiment_es=idea.experiment_es,
                    kpi_es=idea.kpi_es,
                    confidence_score=idea.confidence_score,
                    confidence_level=idea.confidence_level,
                    overinterpretation_risk_es=idea.overinterpretation_risk_es,
                    topic_cluster_key=idea.topic_cluster_key,
                    ai_enriched=run.ai_enrichment_succeeded or False,
                )
            )

        self.results.bulk_add(objects)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def _to_raw_video(video: Video) -> RawVideo:
    return RawVideo(
        video_id=video.id,
        youtube_video_id=video.youtube_video_id,
        title=video.title,
        published_at=video.published_at,
        view_count=video.view_count,
        like_count=video.like_count,
        comment_count=video.comment_count,
        comments_disabled=video.comments_disabled,
    )


def _to_raw_comment(comment: Comment, videos: list[Video]) -> RawComment:
    youtube_video_id = next((v.youtube_video_id for v in videos if v.id == comment.video_id), "")
    return RawComment(
        comment_id=comment.id,
        video_id=comment.video_id,
        youtube_video_id=youtube_video_id,
        text=comment.text,
        published_at=comment.published_at,
        like_count=comment.like_count,
        author_hash=comment.author_hash,
        is_top_level=comment.is_top_level,
    )


def _dominant_topics_for_video(
    context: AnalysisContext, youtube_video_id: str
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for comment in context.usable_comments:
        if comment.youtube_video_id != youtube_video_id or not comment.cluster_key:
            continue
        counts[comment.cluster_key] = counts.get(comment.cluster_key, 0) + 1

    labels = {t.cluster_key: t.label_es for t in context.topics if not t.is_noise}
    ranked = sorted(
        ((key, count) for key, count in counts.items() if key in labels),
        key=lambda item: -item[1],
    )
    return [
        {"cluster_key": key, "label_es": labels[key], "comment_count": count}
        for key, count in ranked[:3]
    ]


def _sentiment_breakdown(members: list[Any]) -> dict[str, int]:
    breakdown: dict[str, int] = {}
    for comment in members:
        breakdown[comment.sentiment_label] = breakdown.get(comment.sentiment_label, 0) + 1
    return breakdown


def build_summary(context: AnalysisContext, recommendations: list[Any]) -> dict[str, Any]:
    """Resumen que alimenta la pestaña «Resumen» del dashboard."""
    usable = context.usable_comments
    total = len(usable)

    positive = sum(1 for c in usable if c.sentiment_label == SentimentLabel.POSITIVE)
    negative = sum(1 for c in usable if c.sentiment_label == SentimentLabel.NEGATIVE)
    mixed = sum(1 for c in usable if c.sentiment_label == SentimentLabel.MIXED)
    neutral = sum(1 for c in usable if c.sentiment_label == SentimentLabel.NEUTRAL)
    uncertain = sum(1 for c in usable if c.sentiment_label == SentimentLabel.UNCERTAIN)

    real_topics = [t for t in context.topics if not t.is_noise]

    strength = max(
        (t for t in real_topics if t.positive_count >= 3),
        key=lambda t: t.positive_count,
        default=None,
    )
    demand = max(
        (t for t in real_topics if t.request_count >= 2),
        key=lambda t: t.request_count,
        default=None,
    )
    criticism = max(
        (t for t in real_topics if t.negative_count >= 2),
        key=lambda t: t.negative_count,
        default=None,
    )
    rising = max(
        (t for t in real_topics if t.trend_direction == TrendDirection.RISING),
        key=lambda t: t.trend_change or 0.0,
        default=None,
    )
    top_recommendation = recommendations[0] if recommendations else None

    overall = "neutral"
    if total:
        if positive / total >= 0.5 and positive > negative * 1.5:
            overall = "positivo"
        elif negative / total >= 0.35:
            overall = "critico"
        elif mixed / total >= 0.2:
            overall = "mixto"

    return {
        "videos_analysed": context.total_videos,
        "comments_analysed": total,
        "sentiment": {
            "positive": positive,
            "neutral": neutral,
            "negative": negative,
            "mixed": mixed,
            "uncertain": uncertain,
            "positive_share": round(positive / total, 4) if total else 0.0,
            "negative_share": round(negative / total, 4) if total else 0.0,
            "overall_es": overall,
        },
        "questions": sum(1 for c in usable if c.is_question),
        "requests": sum(1 for c in usable if c.is_request),
        "toxic_comments": sum(1 for c in usable if (c.toxicity or 0.0) >= 0.6),
        "spam_comments": sum(1 for c in context.comments if c.is_spam),
        "top_strength": _topic_brief(strength),
        "top_request": _topic_brief(demand),
        "top_criticism": _topic_brief(criticism),
        "fastest_growing": _topic_brief(rising),
        "top_recommendation": (
            {
                "title_es": top_recommendation.title_es,
                "category": top_recommendation.category,
                "category_label_es": RECOMMENDATION_LABELS_ES.get(
                    top_recommendation.category, top_recommendation.category
                ),
                "confidence_level": top_recommendation.confidence.level,
                "priority": top_recommendation.priority,
            }
            if top_recommendation
            else None
        ),
        "data_quality_level": context.quality.level,
        "data_quality_score": context.quality.score,
        "primary_warning_es": (
            context.quality.warnings_es[0] if context.quality.warnings_es else None
        ),
        "intent_counts": _intent_counts(usable),
        "median_views": context.baseline.median_views,
        "median_comments_per_1000": context.baseline.median_comments_per_1000,
        "median_likes_per_1000": context.baseline.median_likes_per_1000,
    }


def _topic_brief(topic: Any) -> dict[str, Any] | None:
    if topic is None:
        return None
    return {
        "cluster_key": topic.cluster_key,
        "label_es": topic.label_es,
        "comment_count": topic.comment_count,
        "unique_video_count": topic.unique_video_count,
        "positive_count": topic.positive_count,
        "negative_count": topic.negative_count,
        "request_count": topic.request_count,
        "share_of_comments": round(topic.share_of_comments, 4),
        "trend_direction": topic.trend_direction,
        "trend_change": topic.trend_change,
        "confidence_level": topic.confidence_level,
    }


def _intent_counts(comments: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for comment in comments:
        for intent in comment.intents:
            if intent == IntentLabel.OTHER:
                continue
            counts[intent] = counts.get(intent, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


__all__ = ["AnalysisOrchestrator", "build_summary"]
