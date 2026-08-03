"""Repositorios de canal, vídeo y comentario con upserts idempotentes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.entities import Channel, Comment, Video
from app.models.enums import DataSource

_CHANNEL_UPDATABLE = (
    "handle",
    "title",
    "description",
    "thumbnail_url",
    "subscriber_count",
    "subscriber_count_hidden",
    "video_count",
    "view_count",
    "country",
    "published_at",
    "uploads_playlist_id",
    "last_fetched_at",
    "source",
)

_VIDEO_UPDATABLE = (
    "title",
    "description",
    "published_at",
    "thumbnail_url",
    "duration_seconds",
    "view_count",
    "like_count",
    "comment_count",
    "tags",
    "category_id",
    "is_live_content",
    "live_broadcast_content",
    "comments_disabled",
    "last_fetched_at",
    "source",
)


class ChannelRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, channel_id: uuid.UUID) -> Channel | None:
        return self.session.get(Channel, channel_id)

    def get_by_youtube_id(self, youtube_channel_id: str) -> Channel | None:
        stmt = select(Channel).where(Channel.youtube_channel_id == youtube_channel_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[Channel]:
        stmt = select(Channel).order_by(Channel.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def upsert(self, data: dict[str, Any], *, source: str = DataSource.YOUTUBE_API) -> Channel:
        """Inserta o actualiza el canal por su ID de YouTube. Idempotente."""
        payload = {
            k: v for k, v in data.items() if k in {*_CHANNEL_UPDATABLE, "youtube_channel_id"}
        }
        payload["source"] = source
        payload.setdefault("last_fetched_at", datetime.now(UTC))

        insert_stmt = pg_insert(Channel).values(id=uuid.uuid4(), **payload)
        update_set = {
            key: getattr(insert_stmt.excluded, key) for key in _CHANNEL_UPDATABLE if key in payload
        }
        update_set["updated_at"] = datetime.now(UTC)
        returning_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[Channel.youtube_channel_id], set_=update_set
        ).returning(Channel.id)
        channel_id = self.session.execute(returning_stmt).scalar_one()
        self.session.flush()
        channel = self.session.get(Channel, channel_id)
        assert channel is not None
        self.session.refresh(channel)
        return channel

    def delete(self, channel_id: uuid.UUID) -> bool:
        channel = self.get(channel_id)
        if channel is None:
            return False
        self.session.delete(channel)
        self.session.flush()
        return True

    def is_fresh(self, channel: Channel, ttl_hours: int) -> bool:
        """Indica si los datos del canal siguen dentro de la ventana de frescura."""
        if channel.last_fetched_at is None:
            return False
        reference = channel.last_fetched_at
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=UTC)
        return datetime.now(UTC) - reference < timedelta(hours=ttl_hours)


class VideoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(
        self,
        channel_id: uuid.UUID,
        videos: list[dict[str, Any]],
        *,
        source: str = DataSource.YOUTUBE_API,
    ) -> list[Video]:
        """Inserta o actualiza vídeos. Un refresco no duplica registros."""
        if not videos:
            return []
        now = datetime.now(UTC)
        rows = []
        for video in videos:
            payload = {
                k: v for k, v in video.items() if k in {*_VIDEO_UPDATABLE, "youtube_video_id"}
            }
            payload["channel_id"] = channel_id
            payload["source"] = source
            payload["last_fetched_at"] = now
            payload["id"] = uuid.uuid4()
            rows.append(payload)

        stmt = pg_insert(Video).values(rows)
        update_set = {key: getattr(stmt.excluded, key) for key in _VIDEO_UPDATABLE}
        update_set["updated_at"] = now
        stmt = stmt.on_conflict_do_update(index_elements=[Video.youtube_video_id], set_=update_set)
        self.session.execute(stmt)
        self.session.flush()

        ids = [row["youtube_video_id"] for row in rows]
        return self.list_by_youtube_ids(ids)

    def list_by_youtube_ids(self, youtube_ids: list[str]) -> list[Video]:
        if not youtube_ids:
            return []
        stmt = select(Video).where(Video.youtube_video_id.in_(youtube_ids))
        return list(self.session.execute(stmt).scalars().all())

    def list_recent_for_channel(self, channel_id: uuid.UUID, limit: int) -> list[Video]:
        stmt = (
            select(Video)
            .where(Video.channel_id == channel_id)
            .order_by(Video.published_at.desc().nullslast())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def count_for_channel(self, channel_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Video).where(Video.channel_id == channel_id)
        return int(self.session.execute(stmt).scalar_one())


class CommentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(
        self,
        video_id: uuid.UUID,
        comments: list[dict[str, Any]],
        *,
        source: str = DataSource.YOUTUBE_API,
    ) -> int:
        """Inserta comentarios deduplicando por `youtube_comment_id`.

        Devuelve el número de filas enviadas. El conflicto sólo actualiza los
        contadores volátiles (likes y respuestas), no el texto original.
        """
        if not comments:
            return 0
        deduped: dict[str, dict[str, Any]] = {}
        for comment in comments:
            key = comment.get("youtube_comment_id")
            if not key:
                continue
            payload = dict(comment)
            payload["video_id"] = video_id
            payload["source"] = source
            payload["id"] = uuid.uuid4()
            payload.setdefault("created_at", datetime.now(UTC))
            deduped[str(key)] = payload

        rows = list(deduped.values())
        if not rows:
            return 0

        stmt = pg_insert(Comment).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Comment.youtube_comment_id],
            set_={
                "like_count": stmt.excluded.like_count,
                "reply_count": stmt.excluded.reply_count,
                "updated_at_source": stmt.excluded.updated_at_source,
                "sampling_bucket": stmt.excluded.sampling_bucket,
            },
        )
        self.session.execute(stmt)
        self.session.flush()
        return len(rows)

    def list_for_videos(
        self, video_ids: list[uuid.UUID], limit: int | None = None
    ) -> list[Comment]:
        if not video_ids:
            return []
        stmt = (
            select(Comment)
            .where(Comment.video_id.in_(video_ids))
            .order_by(Comment.published_at.desc().nullslast())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def count_for_videos(self, video_ids: list[uuid.UUID]) -> int:
        if not video_ids:
            return 0
        stmt = select(func.count()).select_from(Comment).where(Comment.video_id.in_(video_ids))
        return int(self.session.execute(stmt).scalar_one())

    def delete_for_videos(self, video_ids: list[uuid.UUID]) -> int:
        if not video_ids:
            return 0
        result = self.session.execute(delete(Comment).where(Comment.video_id.in_(video_ids)))
        return int(result.rowcount or 0)  # type: ignore[attr-defined]


__all__ = ["ChannelRepository", "CommentRepository", "VideoRepository"]
