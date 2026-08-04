"""Envoltorios de respuesta y esquemas compartidos."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiError(BaseModel):
    """Error devuelto por la API."""

    code: str = Field(description="Código legible por máquina.")
    message: str = Field(description="Mensaje seguro en español para el usuario.")
    detail: str | None = Field(default=None, description="Detalle técnico (sólo en desarrollo).")
    context: dict[str, Any] | None = None


class ApiResponse(BaseModel, Generic[T]):
    """Envoltorio consistente de todas las respuestas."""

    model_config = ConfigDict(populate_by_name=True)

    ok: bool = True
    data: T | None = None
    error: ApiError | None = None
    request_id: str | None = None


class Message(BaseModel):
    message: str


class HealthComponent(BaseModel):
    name: str
    healthy: bool
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    components: list[HealthComponent]


class PublicConfig(BaseModel):
    """Configuración que el frontend necesita conocer. Nunca incluye secretos."""

    app_name: str
    app_env: str
    demo_mode_enabled: bool
    youtube_configured: bool
    ai_enabled: bool
    ai_provider: str
    owner_mode_enabled: bool
    toxicity_analysis_enabled: bool
    anonymize_comment_authors: bool
    data_retention_days: int
    comment_retention_days: int
    #: Fecha de la última purga real. `None` = nunca se ha ejecutado.
    last_purge_at: str | None = None
    algorithm_version: str
    embedding_backend: str
    sentiment_backend: str
    limits: dict[str, int]
    disclaimer_es: str
    criticism_notice_es: str


__all__ = [
    "ApiError",
    "ApiResponse",
    "HealthComponent",
    "HealthResponse",
    "Message",
    "PublicConfig",
]
