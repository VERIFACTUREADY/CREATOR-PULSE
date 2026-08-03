"""Cola de trabajos basada en Redis (RQ).

Si Redis no está disponible, `enqueue_analysis` devuelve `False` y el llamador
decide qué hacer (la API responde con un error claro en español). El análisis
nunca se ejecuta dentro de la petición web.
"""

from __future__ import annotations

import uuid

from redis import Redis
from rq import Queue

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis: Redis | None = None
_queue: Queue | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, socket_connect_timeout=5)
    return _redis


def get_queue() -> Queue:
    global _queue
    if _queue is None:
        _queue = Queue(
            settings.rq_queue_name,
            connection=get_redis(),
            default_timeout=settings.rq_job_timeout_seconds,
        )
    return _queue


def check_redis() -> bool:
    try:
        return bool(get_redis().ping())
    except Exception as exc:
        logger.warning("redis_healthcheck_failed", error=str(exc))
        return False


def analysis_job_id(run_id: uuid.UUID) -> str:
    """ID de trabajo derivado de la ejecución.

    RQ sólo admite letras, números, guiones y guiones bajos, así que no se
    puede usar `:` como separador.
    """
    return f"analysis-{run_id}"


def enqueue_analysis(run_id: uuid.UUID, *, correlation_id: str | None = None) -> bool:
    """Encola una ejecución de análisis. Devuelve `False` si Redis falla."""
    try:
        get_queue().enqueue(
            "app.workers.jobs.run_analysis_job",
            str(run_id),
            correlation_id,
            job_id=analysis_job_id(run_id),
            result_ttl=3600,
            failure_ttl=86400,
        )
        return True
    except Exception as exc:
        logger.error("enqueue_failed", run_id=str(run_id), error=str(exc))
        return False


def queue_depth() -> int:
    try:
        return len(get_queue())
    except Exception:
        return 0


__all__ = [
    "analysis_job_id",
    "check_redis",
    "enqueue_analysis",
    "get_queue",
    "get_redis",
    "queue_depth",
]
