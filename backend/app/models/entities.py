"""Modelos SQLAlchemy del dominio."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.db.types import EmbeddingVector
from app.models.enums import AnalysisStatus, DataSource, SamplingStrategy


class Channel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Canal público de YouTube (o canal ficticio en modo demostración)."""

    __tablename__ = "channel"
    __table_args__ = (UniqueConstraint("youtube_channel_id", name="uq_channel_youtube_channel_id"),)

    youtube_channel_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    handle: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    subscriber_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    subscriber_count_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    video_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    view_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    country: Mapped[str | None] = mapped_column(String(8), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploads_playlist_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(
        String(32), default=DataSource.YOUTUBE_API, nullable=False, index=True
    )
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    videos: Mapped[list[Video]] = relationship(
        back_populates="channel", cascade="all, delete-orphan", passive_deletes=True
    )
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(
        back_populates="channel", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def is_demo(self) -> bool:
        return self.source == DataSource.DEMO


class Video(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Vídeo público de un canal."""

    __tablename__ = "video"
    __table_args__ = (
        UniqueConstraint("youtube_video_id", name="uq_video_youtube_video_id"),
        Index("ix_video_channel_published", "channel_id", "published_at"),
    )

    youtube_video_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("channel.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    like_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    comment_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    category_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_live_content: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    live_broadcast_content: Mapped[str | None] = mapped_column(String(32), nullable=True)
    comments_disabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default=DataSource.YOUTUBE_API, nullable=False)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    channel: Mapped[Channel] = relationship(back_populates="videos")
    comments: Mapped[list[Comment]] = relationship(
        back_populates="video", cascade="all, delete-orphan", passive_deletes=True
    )


class Comment(UUIDPrimaryKeyMixin, Base):
    """Comentario público de nivel superior o respuesta.

    El nombre público del autor no se almacena: sólo un identificador con hash
    (`author_hash`) que permite deduplicar y detectar spam.
    """

    __tablename__ = "comment"
    __table_args__ = (
        UniqueConstraint("youtube_comment_id", name="uq_comment_youtube_comment_id"),
        Index("ix_comment_video_published", "video_id", "published_at"),
    )

    youtube_comment_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    video_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("video.id", ondelete="CASCADE"), nullable=False
    )
    parent_comment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    original_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    updated_at_source: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_top_level: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    author_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_spam: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sampling_bucket: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default=DataSource.YOUTUBE_API, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    video: Mapped[Video] = relationship(back_populates="comments")


class AnalysisRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Una ejecución completa del pipeline de análisis."""

    __tablename__ = "analysis_run"
    __table_args__ = (Index("ix_analysis_run_channel_created", "channel_id", "created_at"),)

    channel_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("channel.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default=AnalysisStatus.QUEUED, nullable=False, index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Límites solicitados
    max_videos: Mapped[int] = mapped_column(Integer, nullable=False)
    max_comments_per_video: Mapped[int] = mapped_column(Integer, nullable=False)
    max_comments_per_channel: Mapped[int] = mapped_column(Integer, nullable=False)
    include_replies: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sampling_strategy: Mapped[str] = mapped_column(
        String(32), default=SamplingStrategy.MIXED, nullable=False
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message_es: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    videos_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments_analysed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    ai_provider: Mapped[str] = mapped_column(String(32), default="none", nullable=False)
    ai_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ai_enrichment_succeeded: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    model_config_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    data_quality: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default=DataSource.YOUTUBE_API, nullable=False)
    stage_durations: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    channel: Mapped[Channel] = relationship(back_populates="analysis_runs")
    topics: Mapped[list[TopicCluster]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )
    content_ideas: Mapped[list[ContentIdea]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )
    video_metrics: Mapped[list[VideoMetric]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def is_demo(self) -> bool:
        return self.source == DataSource.DEMO


class CommentAnalysis(UUIDPrimaryKeyMixin, Base):
    """Resultado del análisis lingüístico de un comentario en una ejecución."""

    __tablename__ = "comment_analysis"
    __table_args__ = (
        UniqueConstraint("run_id", "comment_id", name="uq_comment_analysis_run_comment"),
        Index("ix_comment_analysis_run_sentiment", "run_id", "sentiment_label"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("analysis_run.id", ondelete="CASCADE"), nullable=False
    )
    comment_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("comment.id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("video.id", ondelete="CASCADE"), nullable=False
    )
    sentiment_label: Mapped[str] = mapped_column(String(16), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sentiment_confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    intents: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    aspects: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    toxicity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_request: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_question: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cluster_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingVector(), nullable=True)
    analysis_version: Mapped[str] = mapped_column(String(32), nullable=False)


class TopicCluster(UUIDPrimaryKeyMixin, Base):
    """Tema detectado en los comentarios de una ejecución."""

    __tablename__ = "topic_cluster"
    __table_args__ = (UniqueConstraint("run_id", "cluster_key", name="uq_topic_cluster_run_key"),)

    run_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("analysis_run.id", ondelete="CASCADE"), nullable=False
    )
    cluster_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label_es: Mapped[str] = mapped_column(String(256), nullable=False)
    description_es: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_video_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    positive_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    neutral_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    negative_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    share_of_comments: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mentions_per_1000: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    video_coverage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recent_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    trend_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trend_direction: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(16), default="baja", nullable=False)
    dominant_video_share: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    top_aspects: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    keywords: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    representative_comments: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    centroid: Mapped[list[float] | None] = mapped_column(EmbeddingVector(), nullable=True)
    is_noise: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_generated_label: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    run: Mapped[AnalysisRun] = relationship(back_populates="topics")


class Recommendation(UUIDPrimaryKeyMixin, Base):
    """Recomendación accionable respaldada por evidencia numérica."""

    __tablename__ = "recommendation"

    run_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("analysis_run.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    title_es: Mapped[str] = mapped_column(String(512), nullable=False)
    explanation_es: Mapped[str] = mapped_column(Text, nullable=False)
    reason_es: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(16), default="baja", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False, index=True)
    suggested_format: Mapped[str | None] = mapped_column(String(32), nullable=True)
    suggested_hook_es: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_experiment_es: Mapped[str | None] = mapped_column(Text, nullable=True)
    kpi_es: Mapped[str | None] = mapped_column(String(256), nullable=True)
    caveat_es: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic_cluster_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_enriched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    run: Mapped[AnalysisRun] = relationship(back_populates="recommendations")


class ContentIdea(UUIDPrimaryKeyMixin, Base):
    """Idea de vídeo concreta derivada de una oportunidad detectada."""

    __tablename__ = "content_idea"

    run_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("analysis_run.id", ondelete="CASCADE"), nullable=False
    )
    title_es: Mapped[str] = mapped_column(String(512), nullable=False)
    concept_es: Mapped[str] = mapped_column(Text, nullable=False)
    why_es: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    suggested_format: Mapped[str] = mapped_column(String(32), nullable=False)
    hook_es: Mapped[str] = mapped_column(Text, nullable=False)
    call_to_action_es: Mapped[str] = mapped_column(Text, nullable=False)
    experiment_es: Mapped[str] = mapped_column(Text, nullable=False)
    kpi_es: Mapped[str] = mapped_column(String(256), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_level: Mapped[str] = mapped_column(String(16), default="baja", nullable=False)
    overinterpretation_risk_es: Mapped[str] = mapped_column(Text, nullable=False)
    topic_cluster_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_enriched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    run: Mapped[AnalysisRun] = relationship(back_populates="content_ideas")


class VideoMetric(UUIDPrimaryKeyMixin, Base):
    """Métricas de rendimiento calculadas para un vídeo en una ejecución."""

    __tablename__ = "video_metric"
    __table_args__ = (UniqueConstraint("run_id", "video_id", name="uq_video_metric_run_video"),)

    run_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("analysis_run.id", ondelete="CASCADE"), nullable=False
    )
    video_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("video.id", ondelete="CASCADE"), nullable=False
    )
    likes_per_1000_views: Mapped[float | None] = mapped_column(Float, nullable=True)
    comments_per_1000_views: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_actions_per_1000_views: Mapped[float | None] = mapped_column(Float, nullable=True)
    views_relative_to_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    likes_relative_to_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    comments_relative_to_median: Mapped[float | None] = mapped_column(Float, nullable=True)
    age_adjusted_view_velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    age_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    performance_band: Mapped[str] = mapped_column(String(24), default="normal", nullable=False)
    age_caveat: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analysed_comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dominant_topics: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    sentiment_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    run: Mapped[AnalysisRun] = relationship(back_populates="video_metrics")


class ApiUsage(UUIDPrimaryKeyMixin, Base):
    """Libro mayor aproximado de consumo de la API externa."""

    __tablename__ = "api_usage"
    __table_args__ = (Index("ix_api_usage_provider_created", "provider", "created_at"),)

    run_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("analysis_run.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(32), default="youtube", nullable=False)
    endpoint: Mapped[str] = mapped_column(String(64), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    estimated_quota_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cache_status: Mapped[str] = mapped_column(String(16), default="miss", nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class Comparison(UUIDPrimaryKeyMixin, Base):
    """Comparación guardada entre canales analizados."""

    __tablename__ = "comparison"

    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    run_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class OAuthToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Andamiaje para el futuro modo propietario (OAuth de Google).

    Los tokens se cifran con Fernet antes de almacenarse. Esta tabla no se usa
    en el MVP: el modo propietario está detrás de `ENABLE_OWNER_MODE=false`.
    Nunca se almacena la contraseña del creador.
    """

    __tablename__ = "oauth_token"
    __table_args__ = (
        UniqueConstraint("provider", "external_account_id", name="uq_oauth_token_provider_account"),
    )

    provider: Mapped[str] = mapped_column(String(32), default="google", nullable=False)
    external_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("channel.id", ondelete="CASCADE"), nullable=True
    )
    #: Cifrados con Fernet (`app.core.crypto`). Nunca se guardan en claro.
    access_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    refresh_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    token_type: Mapped[str] = mapped_column(String(32), default="Bearer", nullable=False)
    scopes: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


__all__ = [
    "AnalysisRun",
    "ApiUsage",
    "Channel",
    "Comment",
    "CommentAnalysis",
    "Comparison",
    "ContentIdea",
    "OAuthToken",
    "Recommendation",
    "TopicCluster",
    "Video",
    "VideoMetric",
]
