"""Trabajos que ejecuta el worker."""

from __future__ import annotations

import time
import uuid

from app.core.config import settings
from app.core.logging import (
    bind_analysis_run_id,
    bind_correlation_id,
    configure_logging,
    get_logger,
)
from app.db.session import detect_pgvector, session_scope
from app.repositories.analysis import AnalysisRunRepository
from app.services.analysis.orchestrator import AnalysisOrchestrator

logger = get_logger(__name__)

_configured = False


def _ensure_configured() -> None:
    """Configura logging y detección de pgvector una vez por proceso."""
    global _configured
    if _configured:
        return
    configure_logging(settings.log_level, settings.log_json)
    detect_pgvector()
    _configured = True


def run_analysis_job(run_id: str, correlation_id: str | None = None) -> dict[str, object]:
    """Ejecuta el pipeline completo de una `AnalysisRun`."""
    _ensure_configured()
    bind_correlation_id(correlation_id)
    bind_analysis_run_id(run_id)

    started = time.perf_counter()
    logger.info("job_started", job="run_analysis")

    with session_scope() as session:
        orchestrator = AnalysisOrchestrator(session)
        run = orchestrator.execute(uuid.UUID(run_id))
        outcome = {
            "run_id": run_id,
            "status": run.status,
            "videos": run.videos_fetched,
            "comments_analysed": run.comments_analysed,
        }

    duration = round(time.perf_counter() - started, 3)
    logger.info("job_finished", job="run_analysis", duration_seconds=duration, **outcome)
    return outcome


def purge_expired_data_job() -> dict[str, int]:
    """Aplica la política de retención configurada."""
    _ensure_configured()
    with session_scope() as session:
        deleted = AnalysisRunRepository(session).purge_older_than(settings.data_retention_days)
    logger.info("retention_purge", deleted_runs=deleted, days=settings.data_retention_days)
    return {"deleted_runs": deleted}


__all__ = ["purge_expired_data_job", "run_analysis_job"]
