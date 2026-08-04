"""Almacenamiento de tokens OAuth, siempre cifrados.

Esta capa es la única que ve los tokens en claro. Ni la API ni los registros
los exponen: `describe()` devuelve metadatos, nunca el token.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt, encrypt
from app.core.logging import get_logger
from app.models.entities import OAuthToken
from app.services.youtube.oauth import TokenBundle, refresh_access_token, revoke_token

logger = get_logger(__name__)


class OAuthTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # -- Lectura -----------------------------------------------------------

    def get_for_channel(self, channel_id: uuid.UUID) -> OAuthToken | None:
        stmt = select(OAuthToken).where(
            OAuthToken.channel_id == channel_id, OAuthToken.revoked.is_(False)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_account(self, provider: str, external_account_id: str) -> OAuthToken | None:
        stmt = select(OAuthToken).where(
            OAuthToken.provider == provider,
            OAuthToken.external_account_id == external_account_id,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_connected(self) -> list[OAuthToken]:
        stmt = select(OAuthToken).where(OAuthToken.revoked.is_(False))
        return list(self.session.execute(stmt).scalars().all())

    # -- Escritura ---------------------------------------------------------

    def store(
        self,
        *,
        provider: str,
        external_account_id: str,
        channel_id: uuid.UUID | None,
        bundle: TokenBundle,
    ) -> OAuthToken:
        """Guarda o actualiza los tokens de una cuenta. Idempotente."""
        token = self.get_by_account(provider, external_account_id)
        if token is None:
            token = OAuthToken(provider=provider, external_account_id=external_account_id)
            self.session.add(token)

        token.channel_id = channel_id
        token.access_token_encrypted = encrypt(bundle.access_token)
        if bundle.refresh_token:
            # Google sólo envía el refresh token en la primera autorización:
            # si no llega uno nuevo, se conserva el que ya había.
            token.refresh_token_encrypted = encrypt(bundle.refresh_token)
        token.token_type = bundle.token_type
        token.scopes = bundle.scopes
        token.expires_at = bundle.expires_at
        token.last_refreshed_at = datetime.now(UTC)
        token.revoked = False

        self.session.flush()
        logger.info(
            "oauth_token_stored",
            provider=provider,
            channel_id=str(channel_id) if channel_id else None,
            scopes=bundle.scopes,
        )
        return token

    def disconnect(self, token: OAuthToken, *, client: httpx.Client | None = None) -> bool:
        """Revoca en Google y elimina el token local.

        Si la revocación remota falla, el token local se borra igualmente: es
        preferible dejar de custodiarlo.
        """
        revoked_remotely = False
        try:
            refresh = decrypt(token.refresh_token_encrypted)
            access = decrypt(token.access_token_encrypted)
            secret = refresh or access
            if secret:
                revoked_remotely = revoke_token(secret, client=client)
        except Exception as exc:
            logger.warning("oauth_revoke_skipped", error=type(exc).__name__)

        self.session.delete(token)
        self.session.flush()
        logger.info("oauth_token_deleted", revoked_remotely=revoked_remotely)
        return revoked_remotely

    # -- Uso ---------------------------------------------------------------

    def access_token_for(self, token: OAuthToken, *, client: httpx.Client | None = None) -> str:
        """Devuelve un token de acceso válido, renovándolo si hace falta."""
        expires_at = token.expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        bundle = TokenBundle(
            access_token=decrypt(token.access_token_encrypted) or "",
            refresh_token=decrypt(token.refresh_token_encrypted),
            expires_at=expires_at or datetime.now(UTC),
            scopes=token.scopes or [],
            token_type=token.token_type,
        )

        if not bundle.is_expired and bundle.access_token:
            return bundle.access_token

        if not bundle.refresh_token:
            from app.services.youtube.oauth import OAuthExchangeError

            raise OAuthExchangeError(
                "La conexión con tu canal ha caducado y no se puede renovar. Vuelve a conectarlo.",
                code="oauth_sin_refresh",
                detail="no hay refresh token almacenado",
            )

        refreshed = refresh_access_token(bundle.refresh_token, client=client)
        token.access_token_encrypted = encrypt(refreshed.access_token)
        token.expires_at = refreshed.expires_at
        token.last_refreshed_at = datetime.now(UTC)
        self.session.flush()
        logger.info("oauth_token_refreshed", channel_id=str(token.channel_id))
        return refreshed.access_token


def describe(token: OAuthToken) -> dict[str, Any]:
    """Metadatos seguros de una conexión. **Nunca** incluye el token."""
    return {
        "provider": token.provider,
        "channel_id": str(token.channel_id) if token.channel_id else None,
        "external_account_id": token.external_account_id,
        "scopes": token.scopes or [],
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "last_refreshed_at": (
            token.last_refreshed_at.isoformat() if token.last_refreshed_at else None
        ),
        "connected_at": token.created_at.isoformat() if token.created_at else None,
        "has_refresh_token": token.refresh_token_encrypted is not None,
    }


__all__ = ["OAuthTokenRepository", "describe"]
