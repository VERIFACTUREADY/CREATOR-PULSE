"""Flujo OAuth 2.0 de Google para el modo propietario.

Sólo se piden permisos de **lectura**. En ningún momento se pide ni se almacena
la contraseña del creador: Google es quien autentica, y la aplicación sólo
recibe un token que puede revocarse en cualquier momento desde
https://myaccount.google.com/permissions.

El parámetro `state` se guarda en Redis con caducidad y se comprueba en el
retorno, para que un tercero no pueda inducir a la víctima a conectar una
cuenta que no es la suya (CSRF sobre el flujo de autorización).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.errors import AppError, FeatureDisabledError
from app.core.logging import get_logger

logger = get_logger(__name__)

#: Permisos solicitados. Ambos son de sólo lectura.
SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
)

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"  # noqa: S105 (URL pública, no un secreto)
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

#: Prefijo de las claves de `state` en Redis.
STATE_KEY_PREFIX = "oauth:state:"
#: Un flujo de autorización no debería tardar más de 10 minutos.
STATE_TTL_SECONDS = 600
#: Margen antes de considerar caducado un token, para no usarlo justo al expirar.
EXPIRY_MARGIN_SECONDS = 120


class OAuthNotConfiguredError(AppError):
    code = "oauth_no_configurado"
    status_code = 400
    message = (
        "El modo propietario no tiene credenciales de Google configuradas. "
        "Añade GOOGLE_OAUTH_CLIENT_ID y GOOGLE_OAUTH_CLIENT_SECRET al fichero .env."
    )


class OAuthStateError(AppError):
    code = "oauth_estado_invalido"
    status_code = 400
    message = (
        "La solicitud de conexión ha caducado o no es válida. "
        "Vuelve a iniciar la conexión desde la aplicación."
    )


class OAuthExchangeError(AppError):
    code = "oauth_intercambio_fallido"
    status_code = 502
    message = "Google no ha aceptado la autorización. Vuelve a intentarlo."


class OAuthDeniedError(AppError):
    code = "oauth_denegado"
    status_code = 400
    message = "Has cancelado la autorización o Google la ha denegado."


class OAuthChannelMismatchError(AppError):
    code = "oauth_canal_no_coincide"
    status_code = 403
    message = (
        "La cuenta de Google que has autorizado no es la propietaria del canal "
        "seleccionado. Conéctate con la cuenta dueña del canal."
    )


class OAuthIdentityIncompleteError(AppError):
    code = "oauth_identidad_incompleta"
    status_code = 502
    message = (
        "No se ha podido comprobar por completo qué canales pertenecen a tu cuenta. "
        "Vuelve a intentarlo."
    )


class OAuthNoChannelError(AppError):
    code = "oauth_sin_canal"
    status_code = 403
    message = "La cuenta de Google autorizada no tiene ningún canal de YouTube asociado."


@dataclass(frozen=True, slots=True)
class TokenBundle:
    """Tokens devueltos por Google."""

    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scopes: list[str]
    token_type: str = "Bearer"  # noqa: S105 (el esquema del token, no un secreto)

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at - timedelta(seconds=EXPIRY_MARGIN_SECONDS)


def ensure_enabled() -> None:
    """Comprueba que el modo propietario está activo y configurado."""
    if not settings.enable_owner_mode:
        raise FeatureDisabledError(
            "El modo propietario está desactivado en esta instalación. "
            "Actívalo con ENABLE_OWNER_MODE=true.",
            code="modo_propietario_desactivado",
            detail="ENABLE_OWNER_MODE=false",
        )
    if not (settings.google_oauth_client_id and settings.google_oauth_client_secret):
        raise OAuthNotConfiguredError()


def create_state(store: Any) -> str:
    """Genera y guarda un `state` de un solo uso.

    `store` es un cliente de Redis. Se usa Redis y no memoria de proceso para
    que el flujo funcione con varias réplicas de la API.
    """
    state = secrets.token_urlsafe(32)
    store.setex(f"{STATE_KEY_PREFIX}{state}", STATE_TTL_SECONDS, "1")
    return state


def consume_state(store: Any, state: str | None) -> None:
    """Valida y consume el `state`. Lanza si no existe o ya se usó."""
    if not state:
        raise OAuthStateError(detail="falta el parámetro state")
    # `delete` devuelve el número de claves borradas: 1 sólo la primera vez,
    # lo que impide reutilizar un mismo `state`.
    deleted = store.delete(f"{STATE_KEY_PREFIX}{state}")
    if not deleted:
        raise OAuthStateError(detail="state desconocido, caducado o ya utilizado")


def build_authorization_url(state: str) -> str:
    """URL de consentimiento de Google a la que redirigir al creador."""
    ensure_enabled()
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        # `offline` es lo que hace que Google entregue un refresh token.
        "access_type": "offline",
        # Fuerza la pantalla de consentimiento: sin esto Google omite el
        # refresh token en las reconexiones y la conexión duraría una hora.
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTHORIZATION_ENDPOINT}?{urlencode(params)}"


def _parse_token_response(
    payload: dict[str, Any], *, fallback_refresh: str | None = None
) -> TokenBundle:
    access_token = payload.get("access_token")
    if not access_token:
        raise OAuthExchangeError(detail="la respuesta de Google no incluye access_token")

    expires_in = int(payload.get("expires_in", 3600))
    scope_raw = payload.get("scope") or " ".join(SCOPES)

    return TokenBundle(
        access_token=str(access_token),
        # Google sólo envía el refresh token en la primera autorización.
        refresh_token=payload.get("refresh_token") or fallback_refresh,
        expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        scopes=str(scope_raw).split(),
        token_type=str(payload.get("token_type", "Bearer")),
    )


def exchange_code(code: str, *, client: httpx.Client | None = None) -> TokenBundle:
    """Canjea el código de autorización por tokens."""
    ensure_enabled()
    owns_client = client is None
    http = client or httpx.Client(timeout=settings.ai_request_timeout_seconds)
    try:
        response = http.post(
            TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    except httpx.HTTPError as exc:
        raise OAuthExchangeError(detail=f"red: {exc}") from exc
    finally:
        if owns_client:
            http.close()

    if response.status_code != 200:
        # El cuerpo puede contener el client_secret en el eco del error: no se registra.
        logger.warning("oauth_exchange_failed", status=response.status_code)
        raise OAuthExchangeError(detail=f"HTTP {response.status_code}")

    return _parse_token_response(response.json())


def refresh_access_token(refresh_token: str, *, client: httpx.Client | None = None) -> TokenBundle:
    """Renueva el token de acceso a partir del refresh token."""
    ensure_enabled()
    owns_client = client is None
    http = client or httpx.Client(timeout=settings.ai_request_timeout_seconds)
    try:
        response = http.post(
            TOKEN_ENDPOINT,
            data={
                "refresh_token": refresh_token,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "grant_type": "refresh_token",
            },
        )
    except httpx.HTTPError as exc:
        raise OAuthExchangeError(detail=f"red: {exc}") from exc
    finally:
        if owns_client:
            http.close()

    if response.status_code != 200:
        logger.warning("oauth_refresh_failed", status=response.status_code)
        raise OAuthExchangeError(
            "La conexión con tu canal ha dejado de ser válida. Vuelve a conectarlo.",
            code="oauth_refresh_invalido",
            detail=f"HTTP {response.status_code}",
        )

    # La respuesta de refresco no repite el refresh token: se conserva el actual.
    return _parse_token_response(response.json(), fallback_refresh=refresh_token)


#: Tope de páginas de `channels.list(mine=true)`. Una cuenta con más canales
#: que esto es tan improbable que seguir pidiendo sería un bucle disfrazado.
MAX_IDENTITY_PAGES = 5
#: Canales por página. Google acepta hasta 50.
IDENTITY_PAGE_SIZE = 50


def fetch_authorised_channel_ids(
    access_token: str, *, client: httpx.Client | None = None
) -> set[str]:
    """Devuelve **todos** los canales que pertenecen a la cuenta autorizada.

    Es el control que impide asociar el token de una cuenta al canal de otra:
    quien elige el canal en la pantalla es el usuario, y esa elección no prueba
    nada. La respuesta de Google sí.

    Se recorren todas las páginas porque una cuenta puede administrar varios
    canales (cuentas de marca, por ejemplo) y el canal buscado no tiene por qué
    ser el primero. Mirar sólo `items[0]` rechazaba a propietarios legítimos.
    """
    owns_client = client is None
    http = client or httpx.Client(timeout=settings.ai_request_timeout_seconds)
    ids: set[str] = set()
    page_token: str | None = None

    try:
        for _ in range(MAX_IDENTITY_PAGES):
            params: dict[str, Any] = {
                "part": "id",
                "mine": "true",
                "maxResults": IDENTITY_PAGE_SIZE,
            }
            if page_token:
                params["pageToken"] = page_token
            try:
                response = http.get(
                    f"{settings.youtube_api_base_url}/channels",
                    params=params,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            except httpx.HTTPError as exc:
                logger.warning("oauth_identity_request_failed", error=str(exc))
                raise OAuthExchangeError(
                    detail="no se ha podido consultar el canal autorizado"
                ) from exc

            if response.status_code != 200:
                # Nunca se registra el token, sólo el código de estado.
                logger.warning("oauth_identity_rejected", status_code=response.status_code)
                raise OAuthExchangeError(
                    detail=f"channels.list(mine=true) devolvió {response.status_code}"
                )

            try:
                payload = response.json() or {}
            except ValueError as exc:
                # Un cuerpo que no es JSON no puede darse por bueno: sin la
                # lista completa no se puede afirmar que el canal sea suyo.
                logger.warning("oauth_identity_invalid_payload")
                raise OAuthExchangeError(
                    detail="channels.list(mine=true) devolvió un cuerpo no interpretable"
                ) from exc
            if not isinstance(payload, dict):
                raise OAuthExchangeError(
                    detail="channels.list(mine=true) devolvió una estructura inesperada"
                )

            items = payload.get("items") or []
            if not isinstance(items, list):
                raise OAuthExchangeError(detail="`items` no es una lista")
            for item in items:
                if not isinstance(item, dict):
                    continue
                channel_id = str(item.get("id") or "")
                if channel_id:
                    ids.add(channel_id)

            page_token = payload.get("nextPageToken")
            if not page_token:
                break
        else:
            # Se agotaron las páginas permitidas y Google dice que hay más. Un
            # conjunto truncado haría rechazar a un propietario legítimo, así
            # que se falla en lugar de devolver una respuesta a medias.
            if page_token:
                logger.warning("oauth_identity_too_many_pages", pages=MAX_IDENTITY_PAGES)
                raise OAuthIdentityIncompleteError(
                    detail=f"channels.list(mine=true) supera {MAX_IDENTITY_PAGES} páginas"
                )
    finally:
        if owns_client:
            http.close()

    if not ids:
        raise OAuthNoChannelError(detail="channels.list(mine=true) no devolvió canales")
    # Se registra cuántos hay, nunca cuáles: son identificadores de terceros.
    logger.info("oauth_identity_resolved", channels=len(ids))
    return ids


def revoke_token(token: str, *, client: httpx.Client | None = None) -> bool:
    """Revoca el token en Google. Devuelve si la revocación fue aceptada.

    Un fallo aquí no impide borrar el token local: es preferible dejar de
    guardarlo aunque Google siga considerándolo válido.
    """
    owns_client = client is None
    http = client or httpx.Client(timeout=settings.ai_request_timeout_seconds)
    try:
        response = http.post(REVOKE_ENDPOINT, data={"token": token})
        return response.status_code == 200
    except httpx.HTTPError as exc:
        logger.warning("oauth_revoke_failed", error=str(exc))
        return False
    finally:
        if owns_client:
            http.close()


__all__ = [
    "AUTHORIZATION_ENDPOINT",
    "EXPIRY_MARGIN_SECONDS",
    "REVOKE_ENDPOINT",
    "SCOPES",
    "STATE_KEY_PREFIX",
    "STATE_TTL_SECONDS",
    "TOKEN_ENDPOINT",
    "OAuthChannelMismatchError",
    "OAuthDeniedError",
    "OAuthExchangeError",
    "OAuthIdentityIncompleteError",
    "OAuthNoChannelError",
    "OAuthNotConfiguredError",
    "OAuthStateError",
    "TokenBundle",
    "build_authorization_url",
    "consume_state",
    "create_state",
    "ensure_enabled",
    "exchange_code",
    "fetch_authorised_channel_ids",
    "refresh_access_token",
    "revoke_token",
]
