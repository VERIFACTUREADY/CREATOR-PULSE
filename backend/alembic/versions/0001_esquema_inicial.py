"""Esquema inicial de Creator Signal AI.

Crea la extensión `vector` cuando está disponible. Si no lo está, las columnas
de embeddings se materializan como JSONB gracias al tipo `EmbeddingVector`,
de modo que la migración funciona también en un PostgreSQL sin pgvector.

Revision ID: 0001
Revises:
Create Date: 2024-01-01
"""

from __future__ import annotations

from collections.abc import Sequence

import app.db.types
import sqlalchemy as sa
from alembic import op
from app.core.logging import get_logger
from app.db.types import set_pgvector_available
from sqlalchemy.dialects import postgresql

logger = get_logger(__name__)

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enable_pgvector() -> bool:
    """Intenta activar la extensión `vector`; devuelve si está disponible."""
    from app.core.config import settings

    if settings.pgvector_mode == "false":
        set_pgvector_available(False)
        return False
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception as exc:  # pragma: no cover - depende del servidor
        if settings.pgvector_mode == "true":
            raise
        logger.warning("pgvector_extension_unavailable", error=str(exc))
        set_pgvector_available(False)
        return False
    set_pgvector_available(True)
    return True


def upgrade() -> None:
    _enable_pgvector()

    op.create_table(
        "channel",
        sa.Column("youtube_channel_id", sa.String(length=64), nullable=False),
        sa.Column("handle", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=1024), nullable=True),
        sa.Column("subscriber_count", sa.BigInteger(), nullable=True),
        sa.Column("subscriber_count_hidden", sa.Boolean(), nullable=False),
        sa.Column("video_count", sa.BigInteger(), nullable=True),
        sa.Column("view_count", sa.BigInteger(), nullable=True),
        sa.Column("country", sa.String(length=8), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploads_playlist_id", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_channel")),
        sa.UniqueConstraint("youtube_channel_id", name="uq_channel_youtube_channel_id"),
    )
    op.create_index(op.f("ix_channel_handle"), "channel", ["handle"], unique=False)
    op.create_index(op.f("ix_channel_source"), "channel", ["source"], unique=False)
    op.create_index(
        op.f("ix_channel_youtube_channel_id"), "channel", ["youtube_channel_id"], unique=False
    )
    op.create_table(
        "comparison",
        sa.Column("name", sa.String(length=256), nullable=True),
        sa.Column("run_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comparison")),
    )
    op.create_table(
        "analysis_run",
        sa.Column("channel_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("max_videos", sa.Integer(), nullable=False),
        sa.Column("max_comments_per_video", sa.Integer(), nullable=False),
        sa.Column("max_comments_per_channel", sa.Integer(), nullable=False),
        sa.Column("include_replies", sa.Boolean(), nullable=False),
        sa.Column("sampling_strategy", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message_es", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("videos_fetched", sa.Integer(), nullable=False),
        sa.Column("comments_fetched", sa.Integer(), nullable=False),
        sa.Column("comments_analysed", sa.Integer(), nullable=False),
        sa.Column("ai_provider", sa.String(length=32), nullable=False),
        sa.Column("ai_model", sa.String(length=128), nullable=True),
        sa.Column("ai_enrichment_succeeded", sa.Boolean(), nullable=True),
        sa.Column("algorithm_version", sa.String(length=32), nullable=False),
        sa.Column("model_config_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("data_quality", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("stage_durations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["channel.id"],
            name=op.f("fk_analysis_run_channel_id_channel"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_run")),
    )
    op.create_index(
        "ix_analysis_run_channel_created",
        "analysis_run",
        ["channel_id", "created_at"],
        unique=False,
    )
    op.create_index(op.f("ix_analysis_run_status"), "analysis_run", ["status"], unique=False)
    op.create_table(
        "oauth_token",
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_account_id", sa.String(length=128), nullable=False),
        sa.Column("channel_id", sa.UUID(), nullable=True),
        sa.Column("access_token_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["channel.id"],
            name=op.f("fk_oauth_token_channel_id_channel"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_token")),
        sa.UniqueConstraint(
            "provider", "external_account_id", name="uq_oauth_token_provider_account"
        ),
    )
    op.create_table(
        "video",
        sa.Column("youtube_video_id", sa.String(length=32), nullable=False),
        sa.Column("channel_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=1024), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.BigInteger(), nullable=True),
        sa.Column("like_count", sa.BigInteger(), nullable=True),
        sa.Column("comment_count", sa.BigInteger(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("category_id", sa.String(length=16), nullable=True),
        sa.Column("is_live_content", sa.Boolean(), nullable=False),
        sa.Column("live_broadcast_content", sa.String(length=32), nullable=True),
        sa.Column("comments_disabled", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["channel.id"],
            name=op.f("fk_video_channel_id_channel"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_video")),
        sa.UniqueConstraint("youtube_video_id", name="uq_video_youtube_video_id"),
    )
    op.create_index(
        "ix_video_channel_published", "video", ["channel_id", "published_at"], unique=False
    )
    op.create_index(op.f("ix_video_published_at"), "video", ["published_at"], unique=False)
    op.create_index(op.f("ix_video_youtube_video_id"), "video", ["youtube_video_id"], unique=False)
    op.create_table(
        "api_usage",
        sa.Column("run_id", sa.UUID(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("endpoint", sa.String(length=64), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("estimated_quota_units", sa.Integer(), nullable=False),
        sa.Column("cache_status", sa.String(length=16), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["analysis_run.id"],
            name=op.f("fk_api_usage_run_id_analysis_run"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_usage")),
    )
    op.create_index(op.f("ix_api_usage_created_at"), "api_usage", ["created_at"], unique=False)
    op.create_index(
        "ix_api_usage_provider_created", "api_usage", ["provider", "created_at"], unique=False
    )
    op.create_table(
        "comment",
        sa.Column("youtube_comment_id", sa.String(length=128), nullable=False),
        sa.Column("video_id", sa.UUID(), nullable=False),
        sa.Column("parent_comment_id", sa.String(length=128), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("original_language", sa.String(length=16), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at_source", sa.DateTime(timezone=True), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=False),
        sa.Column("reply_count", sa.Integer(), nullable=False),
        sa.Column("is_top_level", sa.Boolean(), nullable=False),
        sa.Column("author_hash", sa.String(length=64), nullable=True),
        sa.Column("is_spam", sa.Boolean(), nullable=False),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False),
        sa.Column("sampling_bucket", sa.String(length=32), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["video_id"], ["video.id"], name=op.f("fk_comment_video_id_video"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comment")),
        sa.UniqueConstraint("youtube_comment_id", name="uq_comment_youtube_comment_id"),
    )
    op.create_index(op.f("ix_comment_author_hash"), "comment", ["author_hash"], unique=False)
    op.create_index(op.f("ix_comment_published_at"), "comment", ["published_at"], unique=False)
    op.create_index(
        "ix_comment_video_published", "comment", ["video_id", "published_at"], unique=False
    )
    op.create_index(
        op.f("ix_comment_youtube_comment_id"), "comment", ["youtube_comment_id"], unique=False
    )
    op.create_table(
        "content_idea",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("title_es", sa.String(length=512), nullable=False),
        sa.Column("concept_es", sa.Text(), nullable=False),
        sa.Column("why_es", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("suggested_format", sa.String(length=32), nullable=False),
        sa.Column("hook_es", sa.Text(), nullable=False),
        sa.Column("call_to_action_es", sa.Text(), nullable=False),
        sa.Column("experiment_es", sa.Text(), nullable=False),
        sa.Column("kpi_es", sa.String(length=256), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("confidence_level", sa.String(length=16), nullable=False),
        sa.Column("overinterpretation_risk_es", sa.Text(), nullable=False),
        sa.Column("topic_cluster_key", sa.String(length=64), nullable=True),
        sa.Column("ai_enriched", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["analysis_run.id"],
            name=op.f("fk_content_idea_run_id_analysis_run"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_idea")),
    )
    op.create_table(
        "recommendation",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=48), nullable=False),
        sa.Column("title_es", sa.String(length=512), nullable=False),
        sa.Column("explanation_es", sa.Text(), nullable=False),
        sa.Column("reason_es", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("confidence_level", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("suggested_format", sa.String(length=32), nullable=True),
        sa.Column("suggested_hook_es", sa.Text(), nullable=True),
        sa.Column("suggested_experiment_es", sa.Text(), nullable=True),
        sa.Column("kpi_es", sa.String(length=256), nullable=True),
        sa.Column("caveat_es", sa.Text(), nullable=True),
        sa.Column("topic_cluster_key", sa.String(length=64), nullable=True),
        sa.Column("ai_enriched", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["analysis_run.id"],
            name=op.f("fk_recommendation_run_id_analysis_run"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation")),
    )
    op.create_index(
        op.f("ix_recommendation_category"), "recommendation", ["category"], unique=False
    )
    op.create_index(
        op.f("ix_recommendation_priority"), "recommendation", ["priority"], unique=False
    )
    op.create_table(
        "topic_cluster",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("cluster_key", sa.String(length=64), nullable=False),
        sa.Column("label_es", sa.String(length=256), nullable=False),
        sa.Column("description_es", sa.Text(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=False),
        sa.Column("unique_video_count", sa.Integer(), nullable=False),
        sa.Column("positive_count", sa.Integer(), nullable=False),
        sa.Column("neutral_count", sa.Integer(), nullable=False),
        sa.Column("negative_count", sa.Integer(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("share_of_comments", sa.Float(), nullable=False),
        sa.Column("mentions_per_1000", sa.Float(), nullable=False),
        sa.Column("video_coverage", sa.Float(), nullable=False),
        sa.Column("recent_share", sa.Float(), nullable=True),
        sa.Column("previous_share", sa.Float(), nullable=True),
        sa.Column("trend_score", sa.Float(), nullable=False),
        sa.Column("trend_direction", sa.String(length=16), nullable=False),
        sa.Column("coverage_score", sa.Float(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("confidence_level", sa.String(length=16), nullable=False),
        sa.Column("dominant_video_share", sa.Float(), nullable=False),
        sa.Column("top_aspects", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "representative_comments", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("centroid", app.db.types.EmbeddingVector(), nullable=True),
        sa.Column("is_noise", sa.Boolean(), nullable=False),
        sa.Column("ai_generated_label", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["analysis_run.id"],
            name=op.f("fk_topic_cluster_run_id_analysis_run"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topic_cluster")),
        sa.UniqueConstraint("run_id", "cluster_key", name="uq_topic_cluster_run_key"),
    )
    op.create_table(
        "video_metric",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("video_id", sa.UUID(), nullable=False),
        sa.Column("likes_per_1000_views", sa.Float(), nullable=True),
        sa.Column("comments_per_1000_views", sa.Float(), nullable=True),
        sa.Column("engagement_actions_per_1000_views", sa.Float(), nullable=True),
        sa.Column("views_relative_to_median", sa.Float(), nullable=True),
        sa.Column("likes_relative_to_median", sa.Float(), nullable=True),
        sa.Column("comments_relative_to_median", sa.Float(), nullable=True),
        sa.Column("age_adjusted_view_velocity", sa.Float(), nullable=True),
        sa.Column("age_days", sa.Float(), nullable=True),
        sa.Column("performance_band", sa.String(length=24), nullable=False),
        sa.Column("age_caveat", sa.Boolean(), nullable=False),
        sa.Column("analysed_comment_count", sa.Integer(), nullable=False),
        sa.Column("dominant_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sentiment_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["analysis_run.id"],
            name=op.f("fk_video_metric_run_id_analysis_run"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["video.id"],
            name=op.f("fk_video_metric_video_id_video"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_video_metric")),
        sa.UniqueConstraint("run_id", "video_id", name="uq_video_metric_run_video"),
    )
    op.create_table(
        "comment_analysis",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("comment_id", sa.UUID(), nullable=False),
        sa.Column("video_id", sa.UUID(), nullable=False),
        sa.Column("sentiment_label", sa.String(length=16), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("sentiment_confidence", sa.Float(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("intents", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("aspects", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("toxicity_score", sa.Float(), nullable=True),
        sa.Column("is_request", sa.Boolean(), nullable=False),
        sa.Column("is_question", sa.Boolean(), nullable=False),
        sa.Column("cluster_key", sa.String(length=64), nullable=True),
        sa.Column("embedding", app.db.types.EmbeddingVector(), nullable=True),
        sa.Column("analysis_version", sa.String(length=32), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["comment_id"],
            ["comment.id"],
            name=op.f("fk_comment_analysis_comment_id_comment"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["analysis_run.id"],
            name=op.f("fk_comment_analysis_run_id_analysis_run"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["video.id"],
            name=op.f("fk_comment_analysis_video_id_video"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comment_analysis")),
        sa.UniqueConstraint("run_id", "comment_id", name="uq_comment_analysis_run_comment"),
    )
    op.create_index(
        op.f("ix_comment_analysis_cluster_key"), "comment_analysis", ["cluster_key"], unique=False
    )
    op.create_index(
        "ix_comment_analysis_run_sentiment",
        "comment_analysis",
        ["run_id", "sentiment_label"],
        unique=False,
    )


def downgrade() -> None:
    # La extensión `vector` no se elimina: puede estar en uso por otros esquemas.
    op.drop_index("ix_comment_analysis_run_sentiment", table_name="comment_analysis")
    op.drop_index(op.f("ix_comment_analysis_cluster_key"), table_name="comment_analysis")
    op.drop_table("comment_analysis")
    op.drop_table("video_metric")
    op.drop_table("topic_cluster")
    op.drop_index(op.f("ix_recommendation_priority"), table_name="recommendation")
    op.drop_index(op.f("ix_recommendation_category"), table_name="recommendation")
    op.drop_table("recommendation")
    op.drop_table("content_idea")
    op.drop_index(op.f("ix_comment_youtube_comment_id"), table_name="comment")
    op.drop_index("ix_comment_video_published", table_name="comment")
    op.drop_index(op.f("ix_comment_published_at"), table_name="comment")
    op.drop_index(op.f("ix_comment_author_hash"), table_name="comment")
    op.drop_table("comment")
    op.drop_index("ix_api_usage_provider_created", table_name="api_usage")
    op.drop_index(op.f("ix_api_usage_created_at"), table_name="api_usage")
    op.drop_table("api_usage")
    op.drop_index(op.f("ix_video_youtube_video_id"), table_name="video")
    op.drop_index(op.f("ix_video_published_at"), table_name="video")
    op.drop_index("ix_video_channel_published", table_name="video")
    op.drop_table("video")
    op.drop_table("oauth_token")
    op.drop_index(op.f("ix_analysis_run_status"), table_name="analysis_run")
    op.drop_index("ix_analysis_run_channel_created", table_name="analysis_run")
    op.drop_table("analysis_run")
    op.drop_table("comparison")
    op.drop_index(op.f("ix_channel_youtube_channel_id"), table_name="channel")
    op.drop_index(op.f("ix_channel_source"), table_name="channel")
    op.drop_index(op.f("ix_channel_handle"), table_name="channel")
    op.drop_table("channel")
