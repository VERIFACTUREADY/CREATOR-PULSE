"""Construcción de las vistas del dashboard a partir de los datos persistidos."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.entities import AnalysisRun, Channel, CommentAnalysis, Video
from app.models.enums import (
    CONTENT_FORMAT_LABELS_ES,
    INTENT_LABELS_ES,
    RECOMMENDATION_LABELS_ES,
    STAGE_LABELS_ES,
    TREND_LABELS_ES,
    AnalysisStatus,
    DataSource,
    IntentLabel,
    SentimentLabel,
)
from app.repositories.analysis import AnalysisRunRepository, ResultsRepository
from app.repositories.channels import VideoRepository
from app.services.analysis.aspects import aspect_label_es

DISCLAIMER_ES = (
    "CreatorPulse AI ofrece análisis automatizados basados en una muestra de comentarios y "
    "métricas públicas. Las clasificaciones y recomendaciones pueden contener errores y no "
    "garantizan crecimiento. Las asociaciones estadísticas no demuestran causalidad."
)

CRITICISM_NOTICE_ES = (
    "Prioriza los patrones repetidos y accionables. Un comentario aislado no representa "
    "necesariamente a tu audiencia."
)

#: Tipos de petición que se muestran en la pestaña «Peticiones».
REQUEST_KINDS: dict[str, str] = {
    IntentLabel.QUESTION: "Preguntas repetidas",
    IntentLabel.TUTORIAL_REQUEST: "Peticiones de tutorial",
    IntentLabel.CONTENT_REQUEST: "Peticiones de contenido",
    IntentLabel.PRODUCT_REQUEST: "Peticiones de producto o enlace",
}

#: Umbral de toxicidad a partir del cual un comentario se clasifica como acoso.
TOXICITY_THRESHOLD = 0.6


class DashboardService:
    """Ensambla las respuestas del dashboard."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.runs = AnalysisRunRepository(session)
        self.results = ResultsRepository(session)
        self.video_repo = VideoRepository(session)

    # -- Utilidades --------------------------------------------------------

    def get_run(self, run_id: uuid.UUID, *, require_completed: bool = False) -> AnalysisRun:
        run = self.runs.get(run_id)
        if run is None:
            raise NotFoundError(
                "El análisis solicitado no existe o ha sido eliminado.",
                detail=f"run_id={run_id}",
            )
        if require_completed and run.status != AnalysisStatus.COMPLETED:
            raise NotFoundError(
                "Este análisis todavía no ha terminado.",
                code="analisis_no_completado",
                detail=f"estado actual: {run.status}",
            )
        return run

    def get_channel(self, run: AnalysisRun) -> Channel:
        channel = self.session.get(Channel, run.channel_id)
        if channel is None:
            raise NotFoundError("El canal del análisis ya no existe.")
        return channel

    # -- Vistas -------------------------------------------------------------

    def run_status(self, run: AnalysisRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "channel_id": run.channel_id,
            "status": run.status,
            "status_label_es": STAGE_LABELS_ES.get(AnalysisStatus(run.status), run.status),
            "progress": run.progress,
            "created_at": run.created_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "videos_fetched": run.videos_fetched,
            "comments_fetched": run.comments_fetched,
            "comments_analysed": run.comments_analysed,
            "error_code": run.error_code,
            "error_message_es": run.error_message_es,
            "is_demo": run.source == DataSource.DEMO,
        }

    def topics(self, run: AnalysisRun, *, include_noise: bool = False) -> list[dict[str, Any]]:
        rows = self.results.topics(run.id, include_noise=include_noise)
        return [
            {
                **{
                    key: getattr(topic, key)
                    for key in (
                        "cluster_key",
                        "label_es",
                        "description_es",
                        "comment_count",
                        "unique_video_count",
                        "positive_count",
                        "neutral_count",
                        "negative_count",
                        "request_count",
                        "question_count",
                        "share_of_comments",
                        "mentions_per_1000",
                        "video_coverage",
                        "recent_share",
                        "previous_share",
                        "trend_score",
                        "trend_direction",
                        "coverage_score",
                        "confidence_score",
                        "confidence_level",
                        "dominant_video_share",
                        "top_aspects",
                        "keywords",
                        "representative_comments",
                        "is_noise",
                        "ai_generated_label",
                    )
                },
                "trend_label_es": TREND_LABELS_ES.get(topic.trend_direction, "Sin datos"),
            }
            for topic in rows
        ]

    def recommendations(self, run: AnalysisRun) -> list[dict[str, Any]]:
        rows = self.results.recommendations(run.id)
        return [
            {
                "id": rec.id,
                "category": rec.category,
                "category_label_es": RECOMMENDATION_LABELS_ES.get(rec.category, rec.category),
                "title_es": rec.title_es,
                "explanation_es": rec.explanation_es,
                "reason_es": rec.reason_es,
                "evidence": rec.evidence,
                "confidence_score": rec.confidence_score,
                "confidence_level": rec.confidence_level,
                "priority": rec.priority,
                "suggested_format": rec.suggested_format,
                "suggested_format_label_es": (
                    CONTENT_FORMAT_LABELS_ES.get(rec.suggested_format)
                    if rec.suggested_format
                    else None
                ),
                "suggested_hook_es": rec.suggested_hook_es,
                "suggested_experiment_es": rec.suggested_experiment_es,
                "kpi_es": rec.kpi_es,
                "caveat_es": rec.caveat_es,
                "topic_cluster_key": rec.topic_cluster_key,
                "ai_enriched": rec.ai_enriched,
            }
            for rec in rows
        ]

    def content_ideas(self, run: AnalysisRun) -> list[dict[str, Any]]:
        rows = self.results.content_ideas(run.id)
        return [
            {
                "id": idea.id,
                "title_es": idea.title_es,
                "concept_es": idea.concept_es,
                "why_es": idea.why_es,
                "evidence": idea.evidence,
                "suggested_format": idea.suggested_format,
                "suggested_format_label_es": CONTENT_FORMAT_LABELS_ES.get(
                    idea.suggested_format, idea.suggested_format
                ),
                "hook_es": idea.hook_es,
                "call_to_action_es": idea.call_to_action_es,
                "experiment_es": idea.experiment_es,
                "kpi_es": idea.kpi_es,
                "confidence_score": idea.confidence_score,
                "confidence_level": idea.confidence_level,
                "overinterpretation_risk_es": idea.overinterpretation_risk_es,
                "topic_cluster_key": idea.topic_cluster_key,
            }
            for idea in rows
        ]

    def videos(self, run: AnalysisRun) -> list[dict[str, Any]]:
        metrics = {m.video_id: m for m in self.results.video_metrics(run.id)}
        videos = self.video_repo.list_recent_for_channel(run.channel_id, run.max_videos)
        rows: list[dict[str, Any]] = []
        for video in videos:
            metric = metrics.get(video.id)
            rows.append(
                {
                    "youtube_video_id": video.youtube_video_id,
                    "title": video.title,
                    "thumbnail_url": video.thumbnail_url,
                    "published_at": video.published_at,
                    "duration_seconds": video.duration_seconds,
                    "view_count": video.view_count,
                    "like_count": video.like_count,
                    "comment_count": video.comment_count,
                    "comments_disabled": video.comments_disabled,
                    "likes_per_1000_views": metric.likes_per_1000_views if metric else None,
                    "comments_per_1000_views": metric.comments_per_1000_views if metric else None,
                    "engagement_actions_per_1000_views": (
                        metric.engagement_actions_per_1000_views if metric else None
                    ),
                    "views_relative_to_median": (
                        metric.views_relative_to_median if metric else None
                    ),
                    "performance_band": metric.performance_band if metric else "normal",
                    "age_caveat": metric.age_caveat if metric else False,
                    "age_days": metric.age_days if metric else None,
                    "analysed_comment_count": metric.analysed_comment_count if metric else 0,
                    "dominant_topics": metric.dominant_topics if metric else [],
                    "sentiment_breakdown": metric.sentiment_breakdown if metric else {},
                    "youtube_url": f"https://www.youtube.com/watch?v={video.youtube_video_id}",
                }
            )
        return rows

    # -- Peticiones, fortalezas y críticas ---------------------------------

    def _analyses_with_text(self, run: AnalysisRun) -> list[dict[str, Any]]:
        """Análisis de comentario unidos a su texto y a su vídeo."""
        from app.models.entities import Comment

        stmt = (
            select(CommentAnalysis, Comment, Video)
            .join(Comment, Comment.id == CommentAnalysis.comment_id)
            .join(Video, Video.id == CommentAnalysis.video_id)
            .where(CommentAnalysis.run_id == run.id)
        )
        rows: list[dict[str, Any]] = []
        for analysis, comment, video in self.session.execute(stmt).all():
            rows.append(
                {
                    "analysis": analysis,
                    "text": comment.text,
                    "likes": comment.like_count,
                    "published_at": comment.published_at,
                    "youtube_video_id": video.youtube_video_id,
                    "video_title": video.title,
                    "is_spam": comment.is_spam,
                    "is_duplicate": comment.is_duplicate,
                }
            )
        return rows

    @staticmethod
    def _example(row: dict[str, Any]) -> dict[str, Any]:
        from app.core.privacy import redact_personal_data, truncate_for_display

        return {
            "text": truncate_for_display(redact_personal_data(row["text"])),
            "likes": row["likes"],
            "sentiment": row["analysis"].sentiment_label,
            "video_title": row["video_title"],
            "youtube_video_id": row["youtube_video_id"],
            "published_at": (row["published_at"].isoformat() if row["published_at"] else None),
        }

    def requests(self, run: AnalysisRun) -> list[dict[str, Any]]:
        """Peticiones y preguntas agrupadas por tema y por tipo."""
        rows = self._analyses_with_text(run)
        topics = {t.cluster_key: t for t in self.results.topics(run.id, include_noise=True)}

        grouped: dict[tuple[str | None, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            analysis = row["analysis"]
            intents = analysis.intents or []
            for kind in REQUEST_KINDS:
                if kind in intents:
                    grouped[(analysis.cluster_key, kind)].append(row)

        items: list[dict[str, Any]] = []
        for (cluster_key, kind), members in grouped.items():
            if len(members) < 2:
                # Una petición aislada no es un patrón.
                continue
            topic = topics.get(cluster_key or "")
            items.append(
                {
                    "cluster_key": cluster_key,
                    "label_es": (topic.label_es if topic else "Peticiones sin un tema concreto"),
                    "kind": kind,
                    "kind_label_es": REQUEST_KINDS[kind],
                    "count": len(members),
                    "unique_video_count": len({m["youtube_video_id"] for m in members}),
                    "confidence_level": topic.confidence_level if topic else "baja",
                    "examples": [
                        self._example(m) for m in sorted(members, key=lambda m: -m["likes"])[:3]
                    ],
                }
            )
        items.sort(key=lambda item: -item["count"])
        return items

    def strengths(self, run: AnalysisRun) -> list[dict[str, Any]]:
        """Feedback positivo recurrente agrupado por aspecto."""
        rows = self._analyses_with_text(run)
        positives = [
            row
            for row in rows
            if row["analysis"].sentiment_label in (SentimentLabel.POSITIVE, SentimentLabel.MIXED)
            and not row["is_spam"]
            and not row["is_duplicate"]
        ]
        total_positive = len(positives) or 1

        by_aspect: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in positives:
            for aspect in row["analysis"].aspects or []:
                by_aspect[aspect].append(row)
            if not (row["analysis"].aspects or []):
                by_aspect["general"].append(row)

        items: list[dict[str, Any]] = []
        for aspect, members in by_aspect.items():
            if len(members) < 3:
                continue
            videos = {m["youtube_video_id"] for m in members}
            level = (
                "alta"
                if len(members) >= 15 and len(videos) >= 3
                else ("media" if len(members) >= 6 and len(videos) >= 2 else "baja")
            )
            items.append(
                {
                    "aspect": aspect,
                    "label_es": (
                        "Valoración general" if aspect == "general" else aspect_label_es(aspect)
                    ),
                    "count": len(members),
                    "unique_video_count": len(videos),
                    "share_of_positive": round(len(members) / total_positive, 4),
                    "confidence_level": level,
                    "examples": [
                        self._example(m) for m in sorted(members, key=lambda m: -m["likes"])[:3]
                    ],
                }
            )
        items.sort(key=lambda item: -item["count"])
        return items

    def criticism(self, run: AnalysisRun) -> list[dict[str, Any]]:
        """Críticas separadas por tipo, priorizando lo repetido y accionable."""
        rows = self._analyses_with_text(run)

        constructive: list[dict[str, Any]] = []
        subjective: list[dict[str, Any]] = []
        harassment: list[dict[str, Any]] = []
        spam: list[dict[str, Any]] = []

        for row in rows:
            analysis = row["analysis"]
            intents = analysis.intents or []
            toxicity = analysis.toxicity_score or 0.0

            if row["is_spam"] or IntentLabel.SPAM in intents:
                spam.append(row)
            elif toxicity >= TOXICITY_THRESHOLD or IntentLabel.INSULT in intents:
                harassment.append(row)
            elif IntentLabel.CONSTRUCTIVE_CRITICISM in intents and (analysis.aspects or []):
                constructive.append(row)
            elif analysis.sentiment_label == SentimentLabel.NEGATIVE:
                subjective.append(row)

        # La crítica constructiva se ordena por aspecto repetido, no por comentario.
        by_aspect: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in constructive:
            for aspect in row["analysis"].aspects or []:
                by_aspect[aspect].append(row)

        constructive_items = [
            {
                "label_es": aspect_label_es(aspect),
                "count": len(members),
                "unique_video_count": len({m["youtube_video_id"] for m in members}),
                "actionable": len(members) >= 3
                and len({m["youtube_video_id"] for m in members}) >= 2,
                "examples": [
                    self._example(m) for m in sorted(members, key=lambda m: -m["likes"])[:3]
                ],
            }
            for aspect, members in sorted(by_aspect.items(), key=lambda kv: -len(kv[1]))
            if len(members) >= 2
        ]

        return [
            {
                "kind": "constructive",
                "label_es": "Crítica constructiva",
                "description_es": (
                    "Comentarios que señalan un aspecto concreto y mejorable. Son los que "
                    "merecen tu atención: prioriza los que se repiten en varios vídeos."
                ),
                "count": len(constructive),
                "items": constructive_items,
            },
            {
                "kind": "subjective",
                "label_es": "No gusta (subjetivo)",
                "description_es": (
                    "Comentarios negativos sin una propuesta concreta de mejora. "
                    "Reflejan gustos personales, no necesariamente un problema del vídeo."
                ),
                "count": len(subjective),
                "items": [
                    self._example(m) for m in sorted(subjective, key=lambda m: -m["likes"])[:6]
                ],
            },
            {
                "kind": "harassment",
                "label_es": "Acoso o insultos",
                "description_es": (
                    "Comentarios ofensivos detectados automáticamente. Se muestran para que "
                    "puedas revisar la moderación, no para que respondas a cada uno. "
                    "Ninguna recomendación de contenido de este informe se basa en ellos."
                ),
                "count": len(harassment),
                "items": [self._example(m) for m in harassment[:6]],
            },
            {
                "kind": "spam",
                "label_es": "Posible spam",
                "description_es": (
                    "Comentarios que parecen autopromoción o estafa. Se excluyen de todas "
                    "las conclusiones del análisis."
                ),
                "count": len(spam),
                "items": [self._example(m) for m in spam[:6]],
            },
        ]

    # -- Dashboard completo -------------------------------------------------

    def dashboard(self, run_id: uuid.UUID) -> dict[str, Any]:
        run = self.get_run(run_id, require_completed=True)
        channel = self.get_channel(run)
        return {
            "run": self.run_status(run),
            "channel": channel,
            "summary": run.summary or {},
            "topics": self.topics(run),
            "recommendations": self.recommendations(run),
            "content_ideas": self.content_ideas(run),
            "videos": self.videos(run),
            "requests": self.requests(run),
            "strengths": self.strengths(run),
            "criticism": self.criticism(run),
            "data_quality": run.data_quality or {},
            "disclaimer_es": DISCLAIMER_ES,
        }

    # -- Comparador ---------------------------------------------------------

    def compare(self, run_ids: list[uuid.UUID]) -> dict[str, Any]:
        """Compara métricas públicas de varios canales ya analizados."""
        rows: list[dict[str, Any]] = []
        for run_id in run_ids:
            run = self.get_run(run_id, require_completed=True)
            channel = self.get_channel(run)
            summary = run.summary or {}
            quality = run.data_quality or {}
            sentiment = summary.get("sentiment", {})
            topics = self.results.topics(run.id)[:3]

            comments_analysed = int(summary.get("comments_analysed", 0) or 0)
            rows.append(
                {
                    # Se serializan como texto porque el resultado se persiste
                    # en una columna JSONB; Pydantic los vuelve a convertir a
                    # UUID al construir la respuesta.
                    "run_id": str(run.id),
                    "channel_id": str(channel.id),
                    "channel_title": channel.title,
                    "handle": channel.handle,
                    "thumbnail_url": channel.thumbnail_url,
                    "is_demo": channel.source == DataSource.DEMO,
                    "subscriber_count": channel.subscriber_count,
                    "subscriber_count_hidden": channel.subscriber_count_hidden,
                    "videos_analysed": int(summary.get("videos_analysed", 0) or 0),
                    "comments_analysed": comments_analysed,
                    "median_views": float(summary.get("median_views", 0.0) or 0.0),
                    "median_likes_per_1000": float(
                        summary.get("median_likes_per_1000", 0.0) or 0.0
                    ),
                    "median_comments_per_1000": float(
                        summary.get("median_comments_per_1000", 0.0) or 0.0
                    ),
                    "positive_share": float(sentiment.get("positive_share", 0.0) or 0.0),
                    "negative_share": float(sentiment.get("negative_share", 0.0) or 0.0),
                    "request_share": round(
                        int(summary.get("requests", 0) or 0) / comments_analysed, 4
                    )
                    if comments_analysed
                    else 0.0,
                    "top_topics": [
                        {
                            "label_es": t.label_es,
                            "comment_count": t.comment_count,
                            "share_of_comments": t.share_of_comments,
                        }
                        for t in topics
                    ],
                    "data_quality_score": float(quality.get("score", 0.0) or 0.0),
                    "data_quality_level": str(quality.get("level", "baja")),
                }
            )

        warnings = [
            "Los canales tienen audiencias, tamaños y fechas de publicación distintos: "
            "esta comparación es orientativa y no es una clasificación de calidad.",
            "Las muestras de comentarios pueden tener tamaños muy diferentes. Fíjate en la "
            "puntuación de calidad de datos de cada canal antes de sacar conclusiones.",
        ]
        if any(row["is_demo"] for row in rows) and not all(row["is_demo"] for row in rows):
            warnings.append(
                "Estás comparando datos de demostración con datos reales de la API. "
                "Los datos de demostración son ficticios."
            )
        if any(row["subscriber_count_hidden"] for row in rows):
            warnings.append(
                "Algún canal oculta su número de suscriptores, así que no se puede "
                "normalizar por tamaño de audiencia."
            )

        return {"id": None, "channels": rows, "warnings_es": warnings, "created_at": None}


def intent_label_es(intent: str) -> str:
    return INTENT_LABELS_ES.get(intent, intent)


__all__ = [
    "CRITICISM_NOTICE_ES",
    "DISCLAIMER_ES",
    "REQUEST_KINDS",
    "TOXICITY_THRESHOLD",
    "DashboardService",
    "intent_label_es",
]
