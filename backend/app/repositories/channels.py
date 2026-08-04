"""Repositorios de canal, vídeo y comentario con upserts idempotentes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.entities import AnalysisRun, AnalysisRunComment, Channel, Comment, Video
from app.models.enums import DataSource

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SampleRegistration:
    """Resultado de cerrar la muestra de una ejecución."""

    #: Comentarios que componen la muestra final.
    size: int
    #: Filas realmente insertadas. Cero si se reutilizó una muestra ya cerrada.
    inserted: int
    #: `True` si la ejecución ya tenía la muestra cerrada de un intento previo.
    reused: bool


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
    ) -> dict[str, uuid.UUID]:
        """Inserta comentarios deduplicando por `youtube_comment_id`.

        Devuelve `{youtube_comment_id: id}` con los identificadores reales de
        cada comentario, tanto de los recién insertados como de los que ya
        existían. Quien llama los necesita para anclar la muestra exacta a la
        ejecución. El conflicto sólo actualiza los contadores volátiles (likes y
        respuestas), nunca el texto original.
        """
        if not comments:
            return {}
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
            return {}

        insert_stmt = pg_insert(Comment).values(rows)
        # `DO UPDATE ... RETURNING` devuelve fila tanto si se insertó como si ya
        # existía, que es justo lo que hace falta aquí: el identificador real de
        # cada comentario para anclarlo a la ejecución. Con `DO NOTHING`, las
        # filas ya existentes no volverían y se perderían de la muestra.
        returning_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[Comment.youtube_comment_id],
            set_={
                "like_count": insert_stmt.excluded.like_count,
                "reply_count": insert_stmt.excluded.reply_count,
                "updated_at_source": insert_stmt.excluded.updated_at_source,
                # `sampling_bucket` NO se actualiza: es un campo compartido por
                # todas las ejecuciones y sobrescribirlo hacía que el bucket de
                # una ejecución pisara el de otra. El dato correcto, propio de
                # cada ejecución, vive en `analysis_run_comment`.
            },
        ).returning(Comment.youtube_comment_id, Comment.id)
        result = self.session.execute(returning_stmt)
        ids = {str(external): row_id for external, row_id in result.all()}
        self.session.flush()
        return ids

    def register_run_sample(
        self,
        run_id: uuid.UUID,
        selections: list[tuple[uuid.UUID, str | None]],
        *,
        max_comments: int | None = None,
    ) -> SampleRegistration:
        """Cierra la muestra de una ejecución. **Una sola vez.**

        `selections` son pares `(comment_id, sampling_bucket)` ya ordenados: la
        posición se guarda como `selection_order` y hace la muestra
        reproducible.

        Si la ejecución ya tiene la muestra cerrada (`sample_finalized_at`), no
        se toca nada y se devuelve la existente. Esto es lo que impide que un
        reintento con datos distintos amplíe la muestra: `ON CONFLICT DO
        NOTHING` evitaba duplicar pares, pero no evitaba **añadir** comentarios
        nuevos que no estaban en el primer intento.

        Si un intento anterior murió a medias, la muestra no quedó cerrada: en
        ese caso se descartan las filas parciales y se registra entera, para
        que el orden no tenga huecos ni posiciones repetidas.
        """
        # `FOR UPDATE` serializa el cierre de la muestra: si dos workers cogen
        # el mismo trabajo, el segundo espera aquí y, cuando entra, ya ve la
        # muestra cerrada por el primero. Sin el bloqueo ambos verían
        # `sample_finalized_at=NULL` y competirían por borrar e insertar, con
        # el resultado de una muestra corrupta o un IntegrityError.
        run = self.session.execute(
            select(AnalysisRun).where(AnalysisRun.id == run_id).with_for_update()
        ).scalar_one_or_none()
        if run is None:
            raise ValueError(f"la ejecución {run_id} no existe")

        if run.sample_finalized_at is not None:
            existing = self.count_for_run(run_id)
            logger.info("sample_reused", run_id=str(run_id), size=existing)
            return SampleRegistration(size=existing, inserted=0, reused=True)

        # Restos de un intento fallido: la muestra no llegó a cerrarse, así que
        # se rehace desde cero en lugar de mezclarse con la nueva selección.
        self.session.execute(delete(AnalysisRunComment).where(AnalysisRunComment.run_id == run_id))

        seen: set[uuid.UUID] = set()
        rows: list[dict[str, Any]] = []
        now = datetime.now(UTC)
        for comment_id, bucket in selections:
            if comment_id in seen:
                continue
            seen.add(comment_id)
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "run_id": run_id,
                    "comment_id": comment_id,
                    "sampling_bucket": bucket,
                    "selection_order": len(rows),
                    "selected_at": now,
                }
            )

        # Red de seguridad: una ejecución no puede analizar más comentarios de
        # los que pidió, pase lo que pase aguas arriba.
        limit = max_comments if max_comments is not None else run.max_comments_per_channel
        if limit is not None and len(rows) > limit:
            logger.error(
                "sample_exceeds_limit",
                run_id=str(run_id),
                selected=len(rows),
                limit=limit,
            )
            rows = rows[:limit]

        inserted = 0
        if rows:
            result = self.session.execute(
                pg_insert(AnalysisRunComment).values(rows).returning(AnalysisRunComment.id)
            )
            inserted = len(result.all())

        # Cerrar la muestra y escribirla ocurren en la misma transacción: o
        # queda todo, o no queda nada que un reintento pueda heredar a medias.
        run.sample_finalized_at = now
        self.session.add(run)
        self.session.flush()
        return SampleRegistration(size=len(rows), inserted=inserted, reused=False)

    def list_for_run(self, run_id: uuid.UUID) -> list[Comment]:
        """Devuelve **sólo** los comentarios muestreados por esa ejecución."""
        stmt = (
            select(Comment)
            .join(AnalysisRunComment, AnalysisRunComment.comment_id == Comment.id)
            .where(AnalysisRunComment.run_id == run_id)
            .order_by(AnalysisRunComment.selection_order)
        )
        return list(self.session.execute(stmt).scalars().all())

    def buckets_for_run(self, run_id: uuid.UUID) -> dict[str, int]:
        """Recuento por bucket de la muestra ya anclada a la ejecución.

        Se lee de la base y no de la selección en memoria, para que un reintento
        que reutiliza la muestra informe exactamente de lo mismo.
        """
        stmt = (
            select(AnalysisRunComment.sampling_bucket, func.count())
            .where(AnalysisRunComment.run_id == run_id)
            .group_by(AnalysisRunComment.sampling_bucket)
        )
        return {
            (bucket or "sin_bucket"): int(total)
            for bucket, total in self.session.execute(stmt).all()
        }

    def count_for_run(self, run_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(AnalysisRunComment)
            .where(AnalysisRunComment.run_id == run_id)
        )
        return int(self.session.execute(stmt).scalar_one())

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
