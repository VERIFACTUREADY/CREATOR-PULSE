"""Esquemas de canales y de solicitud de análisis."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import SamplingStrategy


class ChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    youtube_channel_id: str
    handle: str | None
    title: str
    description: str | None
    thumbnail_url: str | None
    subscriber_count: int | None
    subscriber_count_hidden: bool
    video_count: int | None
    view_count: int | None
    country: str | None
    published_at: datetime | None
    source: str
    last_fetched_at: datetime | None
    created_at: datetime


class AnalysisRunBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    status_label_es: str = ""
    progress: int
    created_at: datetime
    completed_at: datetime | None
    videos_fetched: int
    comments_analysed: int
    error_code: str | None
    error_message_es: str | None
    source: str


class ChannelListItem(BaseModel):
    """Fila de la pantalla «Canales»."""

    channel: ChannelOut
    latest_run: AnalysisRunBrief | None
    latest_completed_run: AnalysisRunBrief | None
    top_opportunity_es: str | None


class ResolveRequest(BaseModel):
    reference: str = Field(
        min_length=1,
        max_length=2048,
        description="URL del canal, @handle o ID que empieza por UC.",
    )

    @field_validator("reference")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class ResolvedChannel(BaseModel):
    kind: str
    value: str
    display: str
    is_demo: bool
    channel: ChannelOut | None = None
    message_es: str | None = None


class AnalyseRequest(BaseModel):
    """Petición de análisis desde el formulario «Nuevo análisis»."""

    reference: str = Field(min_length=1, max_length=2048)
    max_videos: int | None = Field(default=None, ge=1, le=50)
    max_comments_per_video: int | None = Field(default=None, ge=10, le=500)
    max_comments_per_channel: int | None = Field(default=None, ge=10, le=10_000)
    include_replies: bool = False
    sampling_strategy: SamplingStrategy = SamplingStrategy.MIXED
    use_external_ai: bool = False
    demo: bool = Field(default=False, description="Fuerza el uso de un canal de demostración.")

    @field_validator("reference")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class AnalyseAccepted(BaseModel):
    run_id: uuid.UUID
    channel_id: uuid.UUID
    status: str
    queued: bool
    is_demo: bool
    estimated_quota_units: int
    message_es: str


class WorkloadEstimate(BaseModel):
    """Aviso de carga estimada mostrado en el formulario."""

    estimated_quota_units: int
    daily_quota_reference: int
    estimated_seconds: int
    note_es: str


class DemoChannelOut(BaseModel):
    handle: str
    youtube_channel_id: str
    title: str
    videos: int
    comments: int


class RefreshRequest(BaseModel):
    max_videos: int | None = Field(default=None, ge=1, le=50)
    max_comments_per_video: int | None = Field(default=None, ge=10, le=500)
    max_comments_per_channel: int | None = Field(default=None, ge=10, le=10_000)
    include_replies: bool | None = None
    sampling_strategy: SamplingStrategy | None = None


class UsageSummary(BaseModel):
    window_days: int
    by_endpoint: list[dict[str, Any]]
    estimated_units_today: int
    estimated_units_window: int
    failed_calls_window: int
    cached_calls_window: int
    daily_quota_reference: int
    note_es: str


__all__ = [
    "AnalyseAccepted",
    "AnalyseRequest",
    "AnalysisRunBrief",
    "ChannelListItem",
    "ChannelOut",
    "DemoChannelOut",
    "RefreshRequest",
    "ResolveRequest",
    "ResolvedChannel",
    "UsageSummary",
    "WorkloadEstimate",
]
