"""Repositorios de ejecuciones de análisis y sus resultados."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    AnalysisRun,
    ApiUsage,
    Channel,
    CommentAnalysis,
    Comparison,
    ContentIdea,
    Recommendation,
    TopicCluster,
    VideoMetric,
)
from app.models.enums import STAGE_PROGRESS, AnalysisStatus


class AnalysisRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **kwargs: Any) -> AnalysisRun:
        run = AnalysisRun(**kwargs)
        self.session.add(run)
        self.session.flush()
        return run

    def get(self, run_id: uuid.UUID) -> AnalysisRun | None:
        return self.session.get(AnalysisRun, run_id)

    def latest_for_channel(
        self, channel_id: uuid.UUID, *, only_completed: bool = False
    ) -> AnalysisRun | None:
        stmt = select(AnalysisRun).where(AnalysisRun.channel_id == channel_id)
        if only_completed:
            stmt = stmt.where(AnalysisRun.status == AnalysisStatus.COMPLETED)
        stmt = stmt.order_by(AnalysisRun.created_at.desc()).limit(1)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_completed(self, limit: int = 100) -> list[AnalysisRun]:
        stmt = (
            select(AnalysisRun)
            .where(AnalysisRun.status == AnalysisStatus.COMPLETED)
            .order_by(AnalysisRun.created_at.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def has_active_run(self, channel_id: uuid.UUID) -> AnalysisRun | None:
        active = [
            s for s in AnalysisStatus if s not in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED)
        ]
        stmt = (
            select(AnalysisRun)
            .where(AnalysisRun.channel_id == channel_id, AnalysisRun.status.in_(active))
            .order_by(AnalysisRun.created_at.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def set_status(
        self,
        run: AnalysisRun,
        status: AnalysisStatus,
        *,
        progress: int | None = None,
    ) -> AnalysisRun:
        run.status = status
        run.progress = (
            progress if progress is not None else STAGE_PROGRESS.get(status, run.progress)
        )
        if status is AnalysisStatus.FETCHING and run.started_at is None:
            run.started_at = datetime.now(UTC)
        if status in (AnalysisStatus.COMPLETED, AnalysisStatus.FAILED):
            run.completed_at = datetime.now(UTC)
        self.session.add(run)
        self.session.flush()
        return run

    def mark_failed(
        self, run: AnalysisRun, *, code: str, message_es: str, detail: str | None = None
    ) -> AnalysisRun:
        run.error_code = code
        run.error_message_es = message_es
        run.error_detail = detail
        return self.set_status(run, AnalysisStatus.FAILED, progress=100)

    def delete(self, run_id: uuid.UUID) -> bool:
        run = self.get(run_id)
        if run is None:
            return False
        self.session.delete(run)
        self.session.flush()
        return True

    def purge_older_than(self, days: int) -> int:
        """Aplica la política de retención de datos."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = self.session.execute(delete(AnalysisRun).where(AnalysisRun.created_at < cutoff))
        return int(result.rowcount or 0)  # type: ignore[attr-defined]


class ResultsRepository:
    """Escritura y lectura de los resultados de una ejecución."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # -- Escritura ---------------------------------------------------------

    def clear_run_results(self, run_id: uuid.UUID) -> None:
        """Elimina resultados previos para que reejecutar sea idempotente."""
        for model in (CommentAnalysis, TopicCluster, Recommendation, ContentIdea, VideoMetric):
            self.session.execute(delete(model).where(model.run_id == run_id))
        self.session.flush()

    def bulk_add(self, objects: list[Any]) -> None:
        if not objects:
            return
        self.session.add_all(objects)
        self.session.flush()

    # -- Lectura -----------------------------------------------------------

    def topics(self, run_id: uuid.UUID, *, include_noise: bool = False) -> list[TopicCluster]:
        stmt = select(TopicCluster).where(TopicCluster.run_id == run_id)
        if not include_noise:
            stmt = stmt.where(TopicCluster.is_noise.is_(False))
        stmt = stmt.order_by(TopicCluster.comment_count.desc())
        return list(self.session.execute(stmt).scalars().all())

    def recommendations(self, run_id: uuid.UUID) -> list[Recommendation]:
        stmt = (
            select(Recommendation)
            .where(Recommendation.run_id == run_id)
            .order_by(Recommendation.priority.asc(), Recommendation.confidence_score.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def content_ideas(self, run_id: uuid.UUID) -> list[ContentIdea]:
        stmt = (
            select(ContentIdea)
            .where(ContentIdea.run_id == run_id)
            .order_by(ContentIdea.confidence_score.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def video_metrics(self, run_id: uuid.UUID) -> list[VideoMetric]:
        stmt = select(VideoMetric).where(VideoMetric.run_id == run_id)
        return list(self.session.execute(stmt).scalars().all())

    def comment_analyses(self, run_id: uuid.UUID) -> list[CommentAnalysis]:
        stmt = select(CommentAnalysis).where(CommentAnalysis.run_id == run_id)
        return list(self.session.execute(stmt).scalars().all())

    def sentiment_counts(self, run_id: uuid.UUID) -> dict[str, int]:
        stmt = (
            select(CommentAnalysis.sentiment_label, func.count())
            .where(CommentAnalysis.run_id == run_id)
            .group_by(CommentAnalysis.sentiment_label)
        )
        return {label: int(count) for label, count in self.session.execute(stmt).all()}


class ApiUsageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record_many(self, run_id: uuid.UUID | None, records: list[Any]) -> None:
        rows = [
            ApiUsage(
                run_id=run_id,
                provider="youtube",
                endpoint=rec.endpoint,
                request_count=rec.request_count,
                estimated_quota_units=rec.estimated_quota_units,
                cache_status=rec.cache_status,
                success=rec.success,
                error_code=rec.error_code,
                created_at=datetime.now(UTC),
            )
            for rec in records
        ]
        if rows:
            self.session.add_all(rows)
            self.session.flush()

    def summary(self, *, days: int = 7) -> dict[str, Any]:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(
                ApiUsage.endpoint,
                func.sum(ApiUsage.request_count),
                func.sum(ApiUsage.estimated_quota_units),
                func.count(),
            )
            .where(ApiUsage.created_at >= cutoff, ApiUsage.provider == "youtube")
            .group_by(ApiUsage.endpoint)
        )
        by_endpoint = [
            {
                "endpoint": endpoint,
                "requests": int(requests or 0),
                "estimated_quota_units": int(units or 0),
                "calls": int(calls or 0),
            }
            for endpoint, requests, units, calls in self.session.execute(stmt).all()
        ]

        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        today_units = self.session.execute(
            select(func.coalesce(func.sum(ApiUsage.estimated_quota_units), 0)).where(
                ApiUsage.created_at >= today_start, ApiUsage.provider == "youtube"
            )
        ).scalar_one()

        errors = self.session.execute(
            select(func.count())
            .select_from(ApiUsage)
            .where(ApiUsage.created_at >= cutoff, ApiUsage.success.is_(False))
        ).scalar_one()

        cached = self.session.execute(
            select(func.count())
            .select_from(ApiUsage)
            .where(ApiUsage.created_at >= cutoff, ApiUsage.cache_status == "hit")
        ).scalar_one()

        return {
            "window_days": days,
            "by_endpoint": sorted(by_endpoint, key=lambda r: -r["estimated_quota_units"]),
            "estimated_units_today": int(today_units or 0),
            "estimated_units_window": sum(r["estimated_quota_units"] for r in by_endpoint),
            "failed_calls_window": int(errors or 0),
            "cached_calls_window": int(cached or 0),
        }

    def recent(self, limit: int = 50) -> list[ApiUsage]:
        stmt = select(ApiUsage).order_by(ApiUsage.created_at.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())


class ComparisonRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self, run_ids: list[str], result: dict[str, Any], name: str | None = None
    ) -> Comparison:
        comparison = Comparison(
            run_ids=run_ids, result=result, name=name, created_at=datetime.now(UTC)
        )
        self.session.add(comparison)
        self.session.flush()
        return comparison

    def list_recent(self, limit: int = 20) -> list[Comparison]:
        stmt = select(Comparison).order_by(Comparison.created_at.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())


def channel_summary_rows(session: Session) -> list[dict[str, Any]]:
    """Datos agregados para la pantalla «Canales»."""
    channels = list(session.execute(select(Channel).order_by(Channel.created_at.desc())).scalars())
    rows: list[dict[str, Any]] = []
    runs_repo = AnalysisRunRepository(session)
    results_repo = ResultsRepository(session)

    for channel in channels:
        latest = runs_repo.latest_for_channel(channel.id)
        completed = runs_repo.latest_for_channel(channel.id, only_completed=True)
        top_opportunity = None
        if completed is not None:
            recs = results_repo.recommendations(completed.id)
            if recs:
                top_opportunity = recs[0].title_es
        rows.append(
            {
                "channel": channel,
                "latest_run": latest,
                "latest_completed_run": completed,
                "top_opportunity_es": top_opportunity,
            }
        )
    return rows


__all__ = [
    "AnalysisRunRepository",
    "ApiUsageRepository",
    "ComparisonRepository",
    "ResultsRepository",
    "channel_summary_rows",
]
