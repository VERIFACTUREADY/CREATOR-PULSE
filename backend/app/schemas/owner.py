"""Esquemas del modo propietario.

Ningún esquema expone tokens: sólo metadatos de la conexión.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OwnerConnectionInfo(BaseModel):
    """Metadatos de un canal conectado. Nunca incluye el token."""

    provider: str
    channel_id: str | None
    channel_title: str | None = None
    external_account_id: str
    scopes: list[str]
    expires_at: str | None
    last_refreshed_at: str | None
    connected_at: str | None
    has_refresh_token: bool


class OwnerStatus(BaseModel):
    enabled: bool = Field(description="ENABLE_OWNER_MODE")
    configured: bool = Field(description="Hay credenciales de Google.")
    encryption_ready: bool = Field(description="Hay clave de cifrado de tokens.")
    ready: bool = Field(description="Se puede conectar un canal.")
    missing_config: list[str]
    scopes: list[str]
    owner_only_metrics: list[str]
    connections: list[OwnerConnectionInfo]
    message_es: str


class StartAuthorization(BaseModel):
    authorization_url: str
    state: str
    scopes: list[str]
    message_es: str


class OwnerConnection(BaseModel):
    channel_id: str
    connected: bool
    revoked_remotely: bool
    message_es: str


class OwnerAnalyticsOut(BaseModel):
    """Informe de propietario. `None` significa «no disponible», nunca cero."""

    channel_id: str
    channel_title: str
    start_date: str
    end_date: str
    views: int | None
    estimated_minutes_watched: int | None
    average_view_duration_seconds: float | None
    average_view_percentage: float | None
    subscribers_gained: int | None
    subscribers_lost: int | None
    net_subscribers: int | None
    likes: int | None
    comments: int | None
    shares: int | None
    impressions: int | None
    impressions_ctr: float | None
    daily: list[dict[str, Any]]
    traffic_sources: list[dict[str, Any]]
    geography: list[dict[str, Any]]
    top_videos: list[dict[str, Any]]
    unavailable_es: list[str]
    note_es: str


__all__ = [
    "OwnerAnalyticsOut",
    "OwnerConnection",
    "OwnerConnectionInfo",
    "OwnerStatus",
    "StartAuthorization",
]
