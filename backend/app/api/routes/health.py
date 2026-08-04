"""Endpoints de salud y configuración pública."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import Protected
from app.core.config import ALGORITHM_VERSION, settings
from app.db.session import check_database
from app.schemas.common import HealthComponent, HealthResponse, PublicConfig
from app.services.dashboard import CRITICISM_NOTICE_ES, DISCLAIMER_ES
from app.workers.queue import check_redis, queue_depth

router = APIRouter(tags=["sistema"])

API_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse, summary="Estado del sistema")
def health(response: Response) -> HealthResponse:
    """Comprueba la API, la base de datos y Redis."""
    db_ok = check_database()
    redis_ok = check_redis()

    components = [
        HealthComponent(name="api", healthy=True),
        HealthComponent(
            name="database",
            healthy=db_ok,
            detail=None if db_ok else "No se ha podido conectar con PostgreSQL.",
        ),
        HealthComponent(
            name="redis",
            healthy=redis_ok,
            detail=None if redis_ok else "No se ha podido conectar con Redis.",
        ),
        HealthComponent(
            name="queue", healthy=redis_ok, detail=f"trabajos en cola: {queue_depth()}"
        ),
    ]

    healthy = db_ok and redis_ok
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="healthy" if healthy else "degraded",
        version=API_VERSION,
        components=components,
    )


@router.get(
    "/config/public",
    response_model=PublicConfig,
    summary="Configuración pública (sin secretos)",
    dependencies=[Protected],
)
def public_config() -> PublicConfig:
    """Configuración que necesita el frontend. Nunca expone claves."""
    return PublicConfig(
        app_name=settings.app_name,
        app_env=settings.app_env,
        demo_mode_enabled=settings.enable_demo_mode,
        youtube_configured=settings.youtube_configured,
        ai_enabled=settings.ai_enabled,
        ai_provider=settings.ai_provider,
        owner_mode_enabled=settings.enable_owner_mode,
        toxicity_analysis_enabled=settings.enable_toxicity_analysis,
        anonymize_comment_authors=settings.anonymize_comment_authors,
        data_retention_days=settings.data_retention_days,
        algorithm_version=ALGORITHM_VERSION,
        embedding_backend=settings.embedding_backend,
        sentiment_backend=settings.sentiment_backend,
        limits={
            "default_max_videos": settings.youtube_max_videos_per_analysis,
            "default_max_comments_per_video": settings.youtube_max_comments_per_video,
            "default_max_comments_per_channel": settings.youtube_max_comments_per_channel,
            "hard_max_videos": settings.youtube_hard_max_videos,
            "hard_max_comments_per_video": settings.youtube_hard_max_comments_per_video,
            "hard_max_comments_per_channel": settings.youtube_hard_max_comments_per_channel,
        },
        disclaimer_es=DISCLAIMER_ES,
        criticism_notice_es=CRITICISM_NOTICE_ES,
    )


__all__ = ["router"]
