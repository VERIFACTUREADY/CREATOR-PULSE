"""Andamiaje del futuro modo propietario (OAuth de Google).

**Estado: desactivado.** Las rutas existen para fijar el contrato y el
almacenamiento cifrado de tokens, pero devuelven un error claro mientras
`ENABLE_OWNER_MODE=false`. No se pide nunca la contraseña del creador, y el MVP
no muestra ninguna métrica de propietario: en modo público esos datos no
existen y no se inventan.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.core.errors import FeatureDisabledError
from app.schemas.common import Message

router = APIRouter(prefix="/oauth", tags=["modo propietario (desactivado)"])

#: Permisos de sólo lectura que pedirá el modo propietario cuando se active.
PLANNED_SCOPES = (
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
)

#: Métricas que sólo estarán disponibles con autorización del propietario.
OWNER_ONLY_METRICS = (
    "estimatedMinutesWatched",
    "averageViewDuration",
    "averageViewPercentage",
    "subscribersGained",
    "subscribersLost",
    "impressions",
    "impressionsClickThroughRate",
    "insightTrafficSourceType",
    "audienceGeography",
)


def _disabled() -> FeatureDisabledError:
    return FeatureDisabledError(
        "El modo propietario todavía no está disponible en esta versión. "
        "Creator Signal AI sólo analiza datos públicos.",
        detail="ENABLE_OWNER_MODE=false",
        code="modo_propietario_desactivado",
    )


@router.get("/google/start", response_model=Message, summary="Inicia el flujo OAuth (desactivado)")
def start_oauth() -> Message:
    if not settings.enable_owner_mode:
        raise _disabled()
    # El intercambio real de código se implementará en la fase de modo propietario.
    raise FeatureDisabledError(
        "El flujo OAuth está activado pero aún no implementado en esta versión.",
        code="modo_propietario_no_implementado",
    )


@router.get("/google/callback", response_model=Message, summary="Callback de OAuth (desactivado)")
def oauth_callback() -> Message:
    if not settings.enable_owner_mode:
        raise _disabled()
    raise FeatureDisabledError(
        "El flujo OAuth está activado pero aún no implementado en esta versión.",
        code="modo_propietario_no_implementado",
    )


@router.get("/status", summary="Estado del modo propietario")
def oauth_status() -> dict[str, object]:
    """Informa de si el modo propietario está activo y qué aportará."""
    return {
        "enabled": settings.enable_owner_mode,
        "implemented": False,
        "planned_scopes": list(PLANNED_SCOPES),
        "owner_only_metrics": list(OWNER_ONLY_METRICS),
        "message_es": (
            "El modo propietario permitirá conectar tu canal con permisos de sólo lectura "
            "para acceder a métricas privadas de YouTube Analytics (tiempo de visualización, "
            "impresiones, CTR, fuentes de tráfico). Nunca se te pedirá tu contraseña. "
            "Mientras esté desactivado, la aplicación sólo usa datos públicos y no muestra "
            "ninguna métrica de propietario."
        ),
    }


__all__ = ["OWNER_ONLY_METRICS", "PLANNED_SCOPES", "router"]
