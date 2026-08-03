"""Esquemas de resultados de análisis."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.channels import ChannelOut


class RunStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    channel_id: uuid.UUID
    status: str
    status_label_es: str
    progress: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    videos_fetched: int
    comments_fetched: int
    comments_analysed: int
    error_code: str | None
    error_message_es: str | None
    is_demo: bool


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cluster_key: str
    label_es: str
    description_es: str | None
    comment_count: int
    unique_video_count: int
    positive_count: int
    neutral_count: int
    negative_count: int
    request_count: int
    question_count: int
    share_of_comments: float
    mentions_per_1000: float
    video_coverage: float
    recent_share: float | None
    previous_share: float | None
    trend_score: float
    trend_direction: str
    trend_label_es: str = ""
    coverage_score: float
    confidence_score: float
    confidence_level: str
    dominant_video_share: float
    top_aspects: list[str] | None
    keywords: list[str] | None
    representative_comments: list[dict[str, Any]] | None
    is_noise: bool
    ai_generated_label: bool


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    category_label_es: str = ""
    title_es: str
    explanation_es: str
    reason_es: str
    evidence: dict[str, Any]
    confidence_score: float
    confidence_level: str
    priority: int
    suggested_format: str | None
    suggested_format_label_es: str | None = None
    suggested_hook_es: str | None
    suggested_experiment_es: str | None
    kpi_es: str | None
    caveat_es: str | None
    topic_cluster_key: str | None
    ai_enriched: bool


class ContentIdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title_es: str
    concept_es: str
    why_es: str
    evidence: dict[str, Any]
    suggested_format: str
    suggested_format_label_es: str = ""
    hook_es: str
    call_to_action_es: str
    experiment_es: str
    kpi_es: str
    confidence_score: float
    confidence_level: str
    overinterpretation_risk_es: str
    topic_cluster_key: str | None


class VideoRow(BaseModel):
    """Fila de la pestaña «Vídeos»."""

    youtube_video_id: str
    title: str
    thumbnail_url: str | None
    published_at: datetime | None
    duration_seconds: int | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    comments_disabled: bool
    likes_per_1000_views: float | None
    comments_per_1000_views: float | None
    engagement_actions_per_1000_views: float | None
    views_relative_to_median: float | None
    performance_band: str
    age_caveat: bool
    age_days: float | None
    analysed_comment_count: int
    dominant_topics: list[dict[str, Any]] | None
    sentiment_breakdown: dict[str, Any] | None
    youtube_url: str


class RequestItem(BaseModel):
    """Petición o pregunta repetida agrupada por tema."""

    cluster_key: str | None
    label_es: str
    kind: str
    kind_label_es: str
    count: int
    unique_video_count: int
    confidence_level: str
    examples: list[dict[str, Any]]


class CriticismGroup(BaseModel):
    kind: str
    label_es: str
    description_es: str
    count: int
    items: list[dict[str, Any]]


class StrengthItem(BaseModel):
    aspect: str
    label_es: str
    count: int
    unique_video_count: int
    share_of_positive: float
    confidence_level: str
    examples: list[dict[str, Any]]


class DataQualityOut(BaseModel):
    videos_sampled: int
    comments_sampled: int
    comments_analysed: int
    comments_discarded_spam: int
    comments_discarded_duplicate: int
    comments_discarded_empty: int
    videos_with_comments_disabled: int
    videos_with_zero_comments: int
    videos_missing_views: int
    videos_missing_likes: int
    sampling_strategy: str
    sampling_buckets: dict[str, int]
    date_coverage: dict[str, Any]
    language_distribution: dict[str, int]
    dominant_video_share: float
    viral_view_concentration: float
    clustering_strategy: str
    topics_found: int
    noise_share: float
    ai_used: bool
    ai_provider: str
    algorithm_version: str
    embedding_backend: str
    sentiment_backend: str
    is_demo: bool
    score: float
    level: str
    warnings_es: list[str]
    biases_es: list[str]


class DashboardOut(BaseModel):
    """Respuesta completa del dashboard."""

    run: RunStatus
    channel: ChannelOut
    summary: dict[str, Any]
    topics: list[TopicOut]
    recommendations: list[RecommendationOut]
    content_ideas: list[ContentIdeaOut]
    videos: list[VideoRow]
    requests: list[RequestItem]
    strengths: list[StrengthItem]
    criticism: list[CriticismGroup]
    data_quality: DataQualityOut
    disclaimer_es: str


class ComparisonRequest(BaseModel):
    run_ids: list[uuid.UUID] = Field(min_length=2, max_length=4)
    name: str | None = Field(default=None, max_length=256)


class ComparisonChannelRow(BaseModel):
    run_id: uuid.UUID
    channel_id: uuid.UUID
    channel_title: str
    handle: str | None
    thumbnail_url: str | None
    is_demo: bool
    subscriber_count: int | None
    subscriber_count_hidden: bool
    videos_analysed: int
    comments_analysed: int
    median_views: float
    median_likes_per_1000: float
    median_comments_per_1000: float
    positive_share: float
    negative_share: float
    request_share: float
    top_topics: list[dict[str, Any]]
    data_quality_score: float
    data_quality_level: str


class ComparisonOut(BaseModel):
    id: uuid.UUID | None
    channels: list[ComparisonChannelRow]
    warnings_es: list[str]
    created_at: datetime | None


__all__ = [
    "ComparisonChannelRow",
    "ComparisonOut",
    "ComparisonRequest",
    "ContentIdeaOut",
    "CriticismGroup",
    "DashboardOut",
    "DataQualityOut",
    "RecommendationOut",
    "RequestItem",
    "RunStatus",
    "StrengthItem",
    "TopicOut",
    "VideoRow",
]
