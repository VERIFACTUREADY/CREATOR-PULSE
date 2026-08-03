"""Endpoints de ejecuciones de análisis y del dashboard."""

from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import Response, StreamingResponse

from app.api.deps import DbSession
from app.schemas.analysis import (
    ContentIdeaOut,
    CriticismGroup,
    DashboardOut,
    DataQualityOut,
    RecommendationOut,
    RequestItem,
    RunStatus,
    StrengthItem,
    TopicOut,
    VideoRow,
)
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/analysis-runs", tags=["análisis"])


@router.get("/{run_id}", response_model=RunStatus, summary="Detalle de una ejecución")
def get_run(run_id: uuid.UUID, session: DbSession) -> Any:
    service = DashboardService(session)
    return service.run_status(service.get_run(run_id))


@router.get(
    "/{run_id}/status",
    response_model=RunStatus,
    summary="Estado y progreso (para sondeo)",
)
def get_status(run_id: uuid.UUID, session: DbSession) -> Any:
    service = DashboardService(session)
    return service.run_status(service.get_run(run_id))


@router.get("/{run_id}/dashboard", response_model=DashboardOut, summary="Dashboard completo")
def get_dashboard(run_id: uuid.UUID, session: DbSession) -> Any:
    return DashboardService(session).dashboard(run_id)


@router.get("/{run_id}/topics", response_model=list[TopicOut], summary="Temas detectados")
def get_topics(
    run_id: uuid.UUID,
    session: DbSession,
    include_noise: bool = Query(default=False, description="Incluye el grupo de ruido."),
) -> Any:
    service = DashboardService(session)
    run = service.get_run(run_id, require_completed=True)
    return service.topics(run, include_noise=include_noise)


@router.get(
    "/{run_id}/recommendations",
    response_model=list[RecommendationOut],
    summary="Recomendaciones",
)
def get_recommendations(run_id: uuid.UUID, session: DbSession) -> Any:
    service = DashboardService(session)
    return service.recommendations(service.get_run(run_id, require_completed=True))


@router.get(
    "/{run_id}/content-ideas",
    response_model=list[ContentIdeaOut],
    summary="Ideas de contenido",
)
def get_content_ideas(run_id: uuid.UUID, session: DbSession) -> Any:
    service = DashboardService(session)
    return service.content_ideas(service.get_run(run_id, require_completed=True))


@router.get("/{run_id}/videos", response_model=list[VideoRow], summary="Métricas por vídeo")
def get_videos(run_id: uuid.UUID, session: DbSession) -> Any:
    service = DashboardService(session)
    return service.videos(service.get_run(run_id, require_completed=True))


@router.get(
    "/{run_id}/requests", response_model=list[RequestItem], summary="Peticiones y preguntas"
)
def get_requests(run_id: uuid.UUID, session: DbSession) -> Any:
    service = DashboardService(session)
    return service.requests(service.get_run(run_id, require_completed=True))


@router.get("/{run_id}/strengths", response_model=list[StrengthItem], summary="Fortalezas")
def get_strengths(run_id: uuid.UUID, session: DbSession) -> Any:
    service = DashboardService(session)
    return service.strengths(service.get_run(run_id, require_completed=True))


@router.get("/{run_id}/criticism", response_model=list[CriticismGroup], summary="Críticas")
def get_criticism(run_id: uuid.UUID, session: DbSession) -> Any:
    service = DashboardService(session)
    return service.criticism(service.get_run(run_id, require_completed=True))


@router.get(
    "/{run_id}/data-quality",
    response_model=DataQualityOut,
    summary="Calidad y limitaciones de los datos",
)
def get_data_quality(run_id: uuid.UUID, session: DbSession) -> Any:
    service = DashboardService(session)
    run = service.get_run(run_id, require_completed=True)
    return run.data_quality or {}


@router.delete("/{run_id}", status_code=204, summary="Elimina un análisis")
def delete_run(run_id: uuid.UUID, session: DbSession) -> None:
    from app.core.errors import NotFoundError
    from app.repositories.analysis import AnalysisRunRepository

    if not AnalysisRunRepository(session).delete(run_id):
        raise NotFoundError("El análisis solicitado no existe.")
    session.commit()


# ---------------------------------------------------------------------------
# Exportación
# ---------------------------------------------------------------------------

export_router = APIRouter(prefix="/export", tags=["exportación"])


@export_router.get("/{run_id}.json", summary="Exporta el análisis en JSON")
def export_json(run_id: uuid.UUID, session: DbSession) -> Response:
    payload = DashboardService(session).dashboard(run_id)
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="analisis-{run_id}.json"'},
    )


@export_router.get("/{run_id}.csv", summary="Exporta los temas y vídeos en CSV")
def export_csv(run_id: uuid.UUID, session: DbSession) -> StreamingResponse:
    """CSV con una sección de temas y otra de vídeos."""
    service = DashboardService(session)
    run = service.get_run(run_id, require_completed=True)
    topics = service.topics(run)
    videos = service.videos(run)

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["seccion", "temas"])
    writer.writerow(
        [
            "tema",
            "comentarios",
            "videos_unicos",
            "cuota_muestra",
            "positivos",
            "negativos",
            "peticiones",
            "preguntas",
            "tendencia",
            "confianza",
        ]
    )
    for topic in topics:
        writer.writerow(
            [
                topic["label_es"],
                topic["comment_count"],
                topic["unique_video_count"],
                f"{topic['share_of_comments']:.4f}",
                topic["positive_count"],
                topic["negative_count"],
                topic["request_count"],
                topic["question_count"],
                topic["trend_direction"],
                topic["confidence_level"],
            ]
        )

    writer.writerow([])
    writer.writerow(["seccion", "videos"])
    writer.writerow(
        [
            "titulo",
            "video_id",
            "publicado",
            "visualizaciones",
            "likes",
            "comentarios",
            "likes_por_1000",
            "comentarios_por_1000",
            "rendimiento_relativo",
            "banda",
        ]
    )
    for video in videos:
        writer.writerow(
            [
                video["title"],
                video["youtube_video_id"],
                video["published_at"].isoformat() if video["published_at"] else "",
                video["view_count"] if video["view_count"] is not None else "",
                video["like_count"] if video["like_count"] is not None else "",
                video["comment_count"] if video["comment_count"] is not None else "",
                video["likes_per_1000_views"] if video["likes_per_1000_views"] is not None else "",
                video["comments_per_1000_views"]
                if video["comments_per_1000_views"] is not None
                else "",
                video["views_relative_to_median"]
                if video["views_relative_to_median"] is not None
                else "",
                video["performance_band"],
            ]
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="analisis-{run_id}.csv"'},
    )


__all__ = ["export_router", "router"]
