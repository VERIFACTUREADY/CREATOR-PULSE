"""Endpoints de canales y de lanzamiento de análisis."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSession, RateLimited
from app.core.config import ALGORITHM_VERSION, settings
from app.core.errors import (
    ConflictError,
    FeatureDisabledError,
    NotFoundError,
    ValidationError,
    YouTubeNotConfiguredError,
)
from app.core.logging import correlation_id_var, get_logger
from app.models.entities import AnalysisRun, Channel
from app.models.enums import STAGE_LABELS_ES, AnalysisStatus, DataSource, SamplingStrategy
from app.repositories.analysis import AnalysisRunRepository, channel_summary_rows
from app.repositories.channels import ChannelRepository
from app.schemas.channels import (
    AnalyseAccepted,
    AnalyseRequest,
    ChannelListItem,
    ChannelOut,
    DemoChannelOut,
    RefreshRequest,
    ResolvedChannel,
    ResolveRequest,
    WorkloadEstimate,
)
from app.services.demo import DemoLoader, list_demo_channels, resolve_demo_reference
from app.services.youtube.ingest import YouTubeIngestService
from app.services.youtube.parser import parse_channel_reference
from app.services.youtube.quota import DEFAULT_DAILY_QUOTA, estimate_analysis_cost
from app.workers.queue import enqueue_analysis

logger = get_logger(__name__)
router = APIRouter(prefix="/channels", tags=["canales"])


def _run_brief(run: AnalysisRun | None) -> dict | None:
    if run is None:
        return None
    return {
        "id": run.id,
        "status": run.status,
        "status_label_es": STAGE_LABELS_ES.get(AnalysisStatus(run.status), run.status),
        "progress": run.progress,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
        "videos_fetched": run.videos_fetched,
        "comments_analysed": run.comments_analysed,
        "error_code": run.error_code,
        "error_message_es": run.error_message_es,
        "source": run.source,
    }


@router.get("", response_model=list[ChannelListItem], summary="Lista de canales analizados")
def list_channels(session: DbSession) -> list[ChannelListItem]:
    rows = channel_summary_rows(session)
    return [
        ChannelListItem(
            channel=ChannelOut.model_validate(row["channel"]),
            latest_run=_run_brief(row["latest_run"]),
            latest_completed_run=_run_brief(row["latest_completed_run"]),
            top_opportunity_es=row["top_opportunity_es"],
        )
        for row in rows
    ]


@router.get("/demo", response_model=list[DemoChannelOut], summary="Canales de demostración")
def demo_channels() -> list[DemoChannelOut]:
    if not settings.enable_demo_mode:
        raise FeatureDisabledError(
            "El modo demostración está desactivado.", detail="ENABLE_DEMO_MODE=false"
        )
    return [
        DemoChannelOut(
            handle=info.handle,
            youtube_channel_id=info.youtube_channel_id,
            title=info.title,
            videos=info.videos,
            comments=info.comments,
        )
        for info in list_demo_channels()
    ]


@router.post(
    "/resolve",
    response_model=ResolvedChannel,
    dependencies=[RateLimited],
    summary="Valida y resuelve una referencia de canal",
)
def resolve_channel(payload: ResolveRequest, session: DbSession) -> ResolvedChannel:
    """Valida el formato y, si es posible, resuelve el canal contra la API."""
    demo_handle = resolve_demo_reference(payload.reference) if settings.enable_demo_mode else None
    if demo_handle:
        info = next(i for i in list_demo_channels() if i.handle == demo_handle)
        existing = ChannelRepository(session).get_by_youtube_id(info.youtube_channel_id)
        return ResolvedChannel(
            kind="demo",
            value=demo_handle,
            display=f"@{demo_handle}",
            is_demo=True,
            channel=ChannelOut.model_validate(existing) if existing else None,
            message_es="Canal de demostración con datos ficticios.",
        )

    reference = parse_channel_reference(payload.reference)

    if not settings.youtube_configured:
        return ResolvedChannel(
            kind=reference.kind,
            value=reference.value,
            display=reference.as_display(),
            is_demo=False,
            channel=None,
            message_es=(
                "El formato es válido, pero no hay ninguna clave de la API de YouTube "
                "configurada, así que no se puede comprobar si el canal existe."
            ),
        )

    service = YouTubeIngestService(session)
    channel = service.resolve_and_store_channel(payload.reference)
    session.commit()
    return ResolvedChannel(
        kind=reference.kind,
        value=reference.value,
        display=reference.as_display(),
        is_demo=False,
        channel=ChannelOut.model_validate(channel),
        message_es=None,
    )


@router.get(
    "/estimate",
    response_model=WorkloadEstimate,
    summary="Estimación de carga y cuota de un análisis",
)
def estimate(
    max_videos: int = Query(default=settings.youtube_max_videos_per_analysis, ge=1, le=50),
    max_comments_per_video: int = Query(
        default=settings.youtube_max_comments_per_video, ge=10, le=500
    ),
    include_replies: bool = Query(default=False),
) -> WorkloadEstimate:
    units = estimate_analysis_cost(
        max_videos, max_comments_per_video, include_replies=include_replies
    )
    # ~0,4 s por vídeo de descarga y ~1,5 ms por comentario analizado.
    seconds = int(max_videos * 0.4 + (max_videos * max_comments_per_video) * 0.0015) + 5
    return WorkloadEstimate(
        estimated_quota_units=units,
        daily_quota_reference=DEFAULT_DAILY_QUOTA,
        estimated_seconds=seconds,
        note_es=(
            f"Este análisis consumirá aproximadamente {units} unidades de la cuota diaria de "
            f"la API de YouTube (la cuota por defecto de un proyecto nuevo es de "
            f"{DEFAULT_DAILY_QUOTA} unidades al día) y tardará en torno a {seconds} segundos. "
            "Aumentar el número de vídeos y comentarios alarga el análisis, consume más cuota y, "
            "si tienes activada la IA externa, aumenta su coste."
        ),
    )


@router.post(
    "/analyse",
    response_model=AnalyseAccepted,
    status_code=202,
    dependencies=[RateLimited],
    summary="Lanza un análisis en segundo plano",
)
def analyse_channel(payload: AnalyseRequest, session: DbSession) -> AnalyseAccepted:
    """Crea la ejecución y la encola. Nunca analiza dentro de la petición web."""
    demo_handle = (
        resolve_demo_reference(payload.reference)
        if (payload.demo or settings.enable_demo_mode)
        else None
    )
    is_demo = bool(demo_handle) and (payload.demo or demo_handle is not None)

    if payload.demo and not demo_handle:
        raise NotFoundError(
            f"No existe ningún canal de demostración llamado «{payload.reference}».",
            detail=f"referencia demo desconocida: {payload.reference}",
        )

    if is_demo:
        if not settings.enable_demo_mode:
            raise FeatureDisabledError("El modo demostración está desactivado.")
        channel = DemoLoader(session).load(demo_handle or "", enabled=settings.enable_demo_mode)
    else:
        if not settings.youtube_configured:
            raise YouTubeNotConfiguredError()
        channel = YouTubeIngestService(session).resolve_and_store_channel(payload.reference)

    runs = AnalysisRunRepository(session)
    active = runs.has_active_run(channel.id)
    if active is not None:
        raise ConflictError(
            "Ya hay un análisis en curso para este canal. Espera a que termine.",
            code="analisis_en_curso",
            context={"run_id": str(active.id)},
        )

    max_videos, per_video, per_channel = settings.clamp_limits(
        payload.max_videos, payload.max_comments_per_video, payload.max_comments_per_channel
    )
    if payload.use_external_ai and not settings.ai_enabled:
        logger.info("external_ai_requested_but_unavailable", provider=settings.ai_provider)

    run = runs.create(
        channel_id=channel.id,
        status=AnalysisStatus.QUEUED,
        progress=0,
        max_videos=max_videos,
        max_comments_per_video=per_video,
        max_comments_per_channel=per_channel,
        include_replies=payload.include_replies,
        sampling_strategy=payload.sampling_strategy,
        algorithm_version=ALGORITHM_VERSION,
        ai_provider=settings.ai_provider if payload.use_external_ai else "none",
        source=DataSource.DEMO if is_demo else DataSource.YOUTUBE_API,
    )
    session.commit()

    queued = enqueue_analysis(run.id, correlation_id=correlation_id_var.get())
    if not queued:
        runs.mark_failed(
            run,
            code="cola_no_disponible",
            message_es=(
                "No se ha podido encolar el análisis porque el servicio de trabajos "
                "no está disponible. Comprueba que Redis y el worker están funcionando."
            ),
            detail="enqueue_analysis devolvió False",
        )
        session.commit()

    units = (
        0
        if is_demo
        else estimate_analysis_cost(max_videos, per_video, include_replies=payload.include_replies)
    )
    return AnalyseAccepted(
        run_id=run.id,
        channel_id=channel.id,
        status=run.status,
        queued=queued,
        is_demo=is_demo,
        estimated_quota_units=units,
        message_es=(
            "Análisis de demostración en cola. Los datos son ficticios."
            if is_demo
            else "Análisis en cola. Puedes seguir el progreso en esta pantalla."
        )
        if queued
        else "No se ha podido encolar el análisis.",
    )


@router.get("/{channel_id}", response_model=ChannelListItem, summary="Detalle de un canal")
def get_channel(channel_id: uuid.UUID, session: DbSession) -> ChannelListItem:
    repo = ChannelRepository(session)
    channel = repo.get(channel_id)
    if channel is None:
        raise NotFoundError("El canal solicitado no existe.", detail=f"channel_id={channel_id}")

    runs = AnalysisRunRepository(session)
    latest = runs.latest_for_channel(channel.id)
    completed = runs.latest_for_channel(channel.id, only_completed=True)
    return ChannelListItem(
        channel=ChannelOut.model_validate(channel),
        latest_run=_run_brief(latest),
        latest_completed_run=_run_brief(completed),
        top_opportunity_es=None,
    )


@router.delete("/{channel_id}", status_code=204, summary="Elimina un canal y sus análisis")
def delete_channel(channel_id: uuid.UUID, session: DbSession) -> None:
    """Borra el canal, sus vídeos, comentarios y análisis en cascada."""
    if not ChannelRepository(session).delete(channel_id):
        raise NotFoundError("El canal solicitado no existe.", detail=f"channel_id={channel_id}")
    session.commit()
    logger.info("channel_deleted", channel_id=str(channel_id))


@router.post(
    "/{channel_id}/refresh",
    response_model=AnalyseAccepted,
    status_code=202,
    dependencies=[RateLimited],
    summary="Vuelve a analizar un canal ya guardado",
)
def refresh_channel(
    channel_id: uuid.UUID, payload: RefreshRequest, session: DbSession
) -> AnalyseAccepted:
    """Relanza el análisis reutilizando los parámetros de la última ejecución."""
    channel = ChannelRepository(session).get(channel_id)
    if channel is None:
        raise NotFoundError("El canal solicitado no existe.", detail=f"channel_id={channel_id}")

    runs = AnalysisRunRepository(session)
    if runs.has_active_run(channel.id) is not None:
        raise ConflictError(
            "Ya hay un análisis en curso para este canal.", code="analisis_en_curso"
        )

    previous = runs.latest_for_channel(channel.id)
    is_demo = channel.source == DataSource.DEMO

    if is_demo:
        if not settings.enable_demo_mode:
            raise FeatureDisabledError("El modo demostración está desactivado.")
        DemoLoader(session).load(channel.handle or channel.youtube_channel_id)
    elif not settings.youtube_configured:
        raise YouTubeNotConfiguredError()

    max_videos, per_video, per_channel = settings.clamp_limits(
        payload.max_videos or (previous.max_videos if previous else None),
        payload.max_comments_per_video or (previous.max_comments_per_video if previous else None),
        payload.max_comments_per_channel
        or (previous.max_comments_per_channel if previous else None),
    )
    strategy = payload.sampling_strategy or (
        SamplingStrategy(previous.sampling_strategy) if previous else SamplingStrategy.MIXED
    )
    include_replies = (
        payload.include_replies
        if payload.include_replies is not None
        else (previous.include_replies if previous else False)
    )

    run = runs.create(
        channel_id=channel.id,
        status=AnalysisStatus.QUEUED,
        progress=0,
        max_videos=max_videos,
        max_comments_per_video=per_video,
        max_comments_per_channel=per_channel,
        include_replies=include_replies,
        sampling_strategy=strategy,
        algorithm_version=ALGORITHM_VERSION,
        source=DataSource.DEMO if is_demo else DataSource.YOUTUBE_API,
    )
    session.commit()

    queued = enqueue_analysis(run.id, correlation_id=correlation_id_var.get())
    return AnalyseAccepted(
        run_id=run.id,
        channel_id=channel.id,
        status=run.status,
        queued=queued,
        is_demo=is_demo,
        estimated_quota_units=0
        if is_demo
        else estimate_analysis_cost(max_videos, per_video, include_replies=include_replies),
        message_es=(
            "Actualización en cola. Los datos existentes se actualizarán sin duplicarse."
            if queued
            else "No se ha podido encolar la actualización."
        ),
    )


def _ensure_channel(session: DbSession, channel_id: uuid.UUID) -> Channel:
    channel = ChannelRepository(session).get(channel_id)
    if channel is None:
        raise ValidationError("El canal solicitado no existe.")
    return channel


__all__ = ["router"]
