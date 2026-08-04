"""Modo propietario: conexión OAuth con Google y analíticas privadas.

Sólo se piden permisos de **lectura** (`youtube.readonly` y
`yt-analytics.readonly`). Nunca se pide la contraseña del creador: autentica
Google, y la autorización puede revocarse desde
https://myaccount.google.com/permissions o desde esta misma aplicación.

Cuando `ENABLE_OWNER_MODE=false`, todos los endpoints responden con un error
claro y la aplicación sigue funcionando en modo público, sin mostrar ninguna
métrica de propietario.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.api.deps import DbSession, RateLimited
from app.core.config import settings
from app.core.crypto import encryption_available
from app.core.errors import FeatureDisabledError, NotFoundError
from app.core.logging import get_logger
from app.repositories.channels import ChannelRepository
from app.repositories.oauth import OAuthTokenRepository, describe
from app.schemas.owner import (
    OwnerAnalyticsOut,
    OwnerConnection,
    OwnerStatus,
    StartAuthorization,
)
from app.services.youtube.analytics import (
    DEFAULT_WINDOW_DAYS,
    YouTubeAnalyticsClient,
)
from app.services.youtube.oauth import (
    SCOPES,
    OAuthChannelMismatchError,
    OAuthDeniedError,
    OAuthExchangeError,
    OAuthNoChannelError,
    build_authorization_url,
    consume_state,
    create_state,
    ensure_enabled,
    exchange_code,
    fetch_authorised_channel_id,
    revoke_token,
)
from app.workers.queue import get_redis

logger = get_logger(__name__)
router = APIRouter(prefix="/oauth", tags=["modo propietario"])

#: Métricas que sólo existen con autorización del propietario.
OWNER_ONLY_METRICS = (
    "estimatedMinutesWatched",
    "averageViewDuration",
    "averageViewPercentage",
    "subscribersGained",
    "subscribersLost",
    "impressions",
    "impressionsClickThroughRate",
    "insightTrafficSourceType",
    "country",
)


@router.get("/status", response_model=OwnerStatus, summary="Estado del modo propietario")
def oauth_status(session: DbSession) -> Any:
    """Informa de si el modo propietario está listo y qué canales hay conectados."""
    configured = bool(settings.google_oauth_client_id and settings.google_oauth_client_secret)
    encryption = encryption_available()

    connections: list[dict[str, Any]] = []
    if settings.enable_owner_mode and encryption:
        repo = OAuthTokenRepository(session)
        channels = ChannelRepository(session)
        for token in repo.list_connected():
            info = describe(token)
            channel = channels.get(token.channel_id) if token.channel_id else None
            info["channel_title"] = channel.title if channel else None
            connections.append(info)

    missing: list[str] = []
    if not settings.enable_owner_mode:
        missing.append("ENABLE_OWNER_MODE=true")
    if not configured:
        missing.append("GOOGLE_OAUTH_CLIENT_ID y GOOGLE_OAUTH_CLIENT_SECRET")
    if not encryption:
        missing.append("OAUTH_TOKEN_ENCRYPTION_KEY")

    return {
        "enabled": settings.enable_owner_mode,
        "configured": configured,
        "encryption_ready": encryption,
        "ready": settings.enable_owner_mode and configured and encryption,
        "missing_config": missing,
        "scopes": list(SCOPES),
        "owner_only_metrics": list(OWNER_ONLY_METRICS),
        "connections": connections,
        "message_es": (
            "El modo propietario conecta tu canal con permisos de sólo lectura para acceder a "
            "métricas privadas de YouTube Analytics (tiempo de visualización, duración media, "
            "impresiones, CTR, fuentes de tráfico y geografía). Nunca se te pedirá tu "
            "contraseña, y puedes revocar el acceso cuando quieras."
        ),
    }


@router.get(
    "/google/start",
    response_model=StartAuthorization,
    dependencies=[RateLimited],
    summary="Inicia la autorización con Google",
)
def start_oauth(
    session: DbSession,
    channel_id: uuid.UUID = Query(description="Canal que se quiere conectar."),
    redirect: bool = Query(default=False, description="Redirige en lugar de devolver la URL."),
) -> Any:
    """Devuelve la URL de consentimiento de Google."""
    ensure_enabled()
    if not encryption_available():
        raise FeatureDisabledError(
            "Falta la clave de cifrado de tokens. Genera una con "
            "`python -m app.cli generar-clave` y añádela a OAUTH_TOKEN_ENCRYPTION_KEY.",
            code="cifrado_no_configurado",
        )

    channel = ChannelRepository(session).get(channel_id)
    if channel is None:
        raise NotFoundError("El canal que quieres conectar no existe.")

    # El `state` lleva el canal para saber a cuál asociar el token al volver.
    state = create_state(get_redis())
    get_redis().setex(f"oauth:channel:{state}", 600, str(channel_id))
    url = build_authorization_url(state)

    if redirect:
        return RedirectResponse(url, status_code=307)
    return {
        "authorization_url": url,
        "state": state,
        "scopes": list(SCOPES),
        "message_es": (
            "Se te pedirá autorizar el acceso de sólo lectura a las analíticas de tu canal. "
            "Google no comparte tu contraseña con esta aplicación."
        ),
    }


@router.get("/google/callback", summary="Retorno de la autorización de Google")
def oauth_callback(
    session: DbSession,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse:
    """Canjea el código por tokens y los guarda cifrados.

    Termina redirigiendo al frontend: es una URL a la que llega el navegador
    del creador, no una llamada de la aplicación.
    """
    ensure_enabled()
    frontend = settings.frontend_url.rstrip("/")

    if error:
        logger.info("oauth_denied", reason=error)
        return RedirectResponse(f"{frontend}/configuracion?oauth=denegado", status_code=303)

    if not code:
        raise OAuthDeniedError(detail="Google no ha devuelto ningún código")

    redis = get_redis()
    # Consume el `state`: si no es válido o ya se usó, aquí se corta.
    consume_state(redis, state)

    raw_channel = redis.get(f"oauth:channel:{state}")
    redis.delete(f"oauth:channel:{state}")
    if raw_channel is None:
        return RedirectResponse(f"{frontend}/configuracion?oauth=caducado", status_code=303)

    channel_id = uuid.UUID(
        raw_channel.decode() if isinstance(raw_channel, bytes) else str(raw_channel)
    )
    channel = ChannelRepository(session).get(channel_id)
    if channel is None:
        return RedirectResponse(
            f"{frontend}/configuracion?oauth=canal_no_encontrado", status_code=303
        )

    bundle = exchange_code(code)

    # Que el usuario haya elegido un canal en la pantalla no prueba que sea
    # suyo. Antes de guardar nada se le pregunta a Google de quién es la cuenta
    # autorizada, y si no coincide el token no llega a persistirse.
    try:
        authorised_channel_id = fetch_authorised_channel_id(bundle.access_token)
    except (OAuthNoChannelError, OAuthExchangeError) as exc:
        revoke_token(bundle.access_token)
        logger.warning("oauth_identity_check_failed", code=exc.code, channel_id=str(channel.id))
        return RedirectResponse(f"{frontend}/configuracion?oauth={exc.code}", status_code=303)

    if authorised_channel_id != channel.youtube_channel_id:
        # Se revoca lo que se acaba de recibir: no se guarda ni un token que no
        # corresponde al canal. No se registra ningún identificador ajeno.
        revoked = revoke_token(bundle.access_token)
        logger.warning(
            "oauth_channel_mismatch",
            channel_id=str(channel.id),
            revoked=revoked,
        )
        return RedirectResponse(
            f"{frontend}/configuracion?oauth={OAuthChannelMismatchError.code}",
            status_code=303,
        )

    OAuthTokenRepository(session).store(
        provider="google",
        external_account_id=channel.youtube_channel_id,
        channel_id=channel.id,
        bundle=bundle,
    )
    session.commit()

    logger.info("oauth_connected", channel_id=str(channel.id))
    return RedirectResponse(f"{frontend}/configuracion?oauth=conectado", status_code=303)


@router.delete(
    "/google/{channel_id}",
    response_model=OwnerConnection,
    summary="Desconecta un canal y revoca el acceso",
)
def disconnect(channel_id: uuid.UUID, session: DbSession) -> Any:
    """Revoca el token en Google y lo elimina de la base de datos."""
    ensure_enabled()
    repo = OAuthTokenRepository(session)
    token = repo.get_for_channel(channel_id)
    if token is None:
        raise NotFoundError("Ese canal no está conectado.")

    revoked = repo.disconnect(token)
    session.commit()
    return {
        "channel_id": str(channel_id),
        "connected": False,
        "revoked_remotely": revoked,
        "message_es": (
            "Canal desconectado y acceso revocado en Google."
            if revoked
            else "Canal desconectado. Revisa también "
            "https://myaccount.google.com/permissions para retirar el acceso."
        ),
    }


@router.get(
    "/analytics/{channel_id}",
    response_model=OwnerAnalyticsOut,
    dependencies=[RateLimited],
    summary="Analíticas privadas del canal conectado",
)
def owner_analytics(
    channel_id: uuid.UUID,
    session: DbSession,
    days: int = Query(default=DEFAULT_WINDOW_DAYS, ge=7, le=365),
) -> Any:
    """Consulta la YouTube Analytics API con el token del propietario."""
    ensure_enabled()
    repo = OAuthTokenRepository(session)
    token = repo.get_for_channel(channel_id)
    if token is None:
        raise NotFoundError(
            "Este canal no está conectado. Conéctalo para ver sus métricas privadas.",
            code="canal_no_conectado",
        )

    channel = ChannelRepository(session).get(channel_id)
    if channel is None:
        raise NotFoundError("El canal ya no existe.")

    access_token = repo.access_token_for(token)
    session.commit()

    with YouTubeAnalyticsClient(access_token) as client:
        report = client.fetch_report(channel.youtube_channel_id, days=days)

    payload = report.to_dict()
    payload["channel_id"] = str(channel_id)
    payload["channel_title"] = channel.title
    payload["note_es"] = (
        "Estos datos proceden de YouTube Analytics y sólo son visibles porque has "
        "autorizado el acceso. YouTube publica las analíticas con dos o tres días de "
        "retraso, así que el periodo termina antes de hoy."
    )
    return payload


__all__ = ["OWNER_ONLY_METRICS", "router"]
