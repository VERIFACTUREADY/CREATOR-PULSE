"""Endpoints del comparador de canales y del uso de API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.repositories.analysis import ApiUsageRepository, ComparisonRepository
from app.schemas.analysis import ComparisonOut, ComparisonRequest
from app.schemas.channels import UsageSummary
from app.services.dashboard import DashboardService
from app.services.youtube.quota import DEFAULT_DAILY_QUOTA

router = APIRouter(tags=["comparador"])


@router.post("/comparisons", response_model=ComparisonOut, summary="Compara canales analizados")
def create_comparison(payload: ComparisonRequest, session: DbSession) -> Any:
    result = DashboardService(session).compare(payload.run_ids)
    stored = ComparisonRepository(session).create(
        [str(rid) for rid in payload.run_ids], result, payload.name
    )
    session.commit()
    return {**result, "id": stored.id, "created_at": stored.created_at}


@router.get("/comparisons", response_model=list[ComparisonOut], summary="Comparaciones guardadas")
def list_comparisons(session: DbSession) -> Any:
    rows = ComparisonRepository(session).list_recent()
    return [
        {
            "id": row.id,
            "channels": (row.result or {}).get("channels", []),
            "warnings_es": (row.result or {}).get("warnings_es", []),
            "created_at": row.created_at,
        }
        for row in rows
    ]


usage_router = APIRouter(prefix="/usage", tags=["uso de api"])


@router.get("/usage/youtube", response_model=UsageSummary, summary="Uso aproximado de la API")
def youtube_usage(
    session: DbSession,
    days: int = Query(default=7, ge=1, le=90),
) -> Any:
    summary = ApiUsageRepository(session).summary(days=days)
    return {
        **summary,
        "daily_quota_reference": DEFAULT_DAILY_QUOTA,
        "note_es": (
            "Estas cifras son una estimación calculada por Creator Signal AI a partir de las "
            "llamadas que ella misma ha realizado. No reflejan la cuota real restante de tu "
            "proyecto de Google Cloud: consúltala en la consola de Google."
        ),
    }


__all__ = ["router", "usage_router"]
