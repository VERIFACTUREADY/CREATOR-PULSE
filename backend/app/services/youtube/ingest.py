"""Ingesta de datos públicos de YouTube hacia la base de datos.

Resuelve el canal, recupera la playlist de subidas, importa los vídeos por lotes
y descarga comentarios siguiendo la estrategia de muestreo elegida. Todo es
idempotente: volver a ejecutarlo actualiza en lugar de duplicar.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ChannelNotFoundError, YouTubeError, YouTubeNotConfiguredError
from app.core.logging import get_logger
from app.models.entities import Channel, Video
from app.models.enums import DataSource, SamplingStrategy
from app.repositories.channels import ChannelRepository, CommentRepository, VideoRepository
from app.services.youtube.client import UsageLedger, YouTubeClient
from app.services.youtube.mappers import (
    map_channel,
    map_comment_reply,
    map_comment_thread,
    map_playlist_item_to_video_id,
    map_video,
    to_int,
)
from app.services.youtube.parser import ChannelReference, ReferenceKind, parse_channel_reference

logger = get_logger(__name__)


@dataclass
class IngestResult:
    """Resumen de lo que la ingesta ha traído."""

    channel: Channel
    videos: list[Video]
    comments_fetched: int = 0
    videos_with_comments_disabled: int = 0
    videos_with_zero_comments: int = 0
    used_cache: bool = False
    sampling_buckets: dict[str, int] = field(default_factory=dict)
    ledger: UsageLedger | None = None
    #: Muestra exacta de esta ejecución: `(comment_id, sampling_bucket)` en
    #: orden de selección. Es lo que se ancla a la `AnalysisRun`.
    selected_comments: list[tuple[uuid.UUID, str | None]] = field(default_factory=list)
    #: Respuestas obtenidas con `comments.list` además de las embebidas.
    replies_fetched: int = 0
    #: Alguna conversación quedó incompleta (por límite alcanzado o por error).
    replies_incomplete: bool = False


def count_sampling_buckets(selected: list[tuple[uuid.UUID, str | None]]) -> dict[str, int]:
    """Recuento por bucket de la muestra realmente seleccionada."""
    counts: dict[str, int] = {}
    for _, bucket in selected:
        key = bucket or "sin_bucket"
        counts[key] = counts.get(key, 0) + 1
    return counts


def resolve_channel_payload(client: YouTubeClient, reference: ChannelReference) -> dict[str, Any]:
    """Resuelve una referencia a la carga útil de canal de la API.

    Prueba los endpoints en orden creciente de coste de cuota: `channels.list`
    (1 unidad) antes que `search.list` (100 unidades).
    """
    item: dict[str, Any] | None = None

    if reference.kind is ReferenceKind.CHANNEL_ID:
        item = client.get_channel_by_id(reference.value)
    elif reference.kind is ReferenceKind.HANDLE:
        item = client.get_channel_by_handle(reference.value)
    elif reference.kind is ReferenceKind.LEGACY_USER:
        item = client.get_channel_by_username(reference.value)
    elif reference.kind is ReferenceKind.LEGACY_CUSTOM:
        # Las URLs personalizadas antiguas suelen coincidir con el handle actual.
        item = client.get_channel_by_handle(reference.value)
        if item is None:
            item = client.get_channel_by_username(reference.value)
        if item is None:
            item = client.search_channel(reference.value)

    if item is None:
        raise ChannelNotFoundError(
            f"No se ha encontrado ningún canal público para «{reference.as_display()}». "
            "Comprueba la URL o el @handle.",
            detail=f"referencia no resuelta: {reference.kind}={reference.value}",
        )
    return map_channel(item)


def _sampling_plan(strategy: SamplingStrategy, budget: int) -> list[tuple[str, str, int]]:
    """Devuelve `(bucket, order, cantidad)` para la estrategia dada.

    Muestrear sólo por relevancia sesga el análisis hacia los comentarios más
    votados, así que la estrategia mixta reparte el presupuesto entre recientes
    y relevantes.
    """
    if budget <= 0:
        return []
    if strategy is SamplingStrategy.RECENT:
        return [("recent", "time", budget)]
    if strategy is SamplingStrategy.RELEVANT:
        return [("relevant", "relevance", budget)]
    recent = max(1, budget // 2)
    relevant = max(1, budget - recent)
    return [("recent", "time", recent), ("relevant", "relevance", relevant)]


class YouTubeIngestService:
    """Orquesta la descarga y persistencia de datos públicos de un canal."""

    def __init__(
        self,
        session: Session,
        client: YouTubeClient | None = None,
        *,
        ledger: UsageLedger | None = None,
    ) -> None:
        self.session = session
        self.ledger = ledger or UsageLedger()
        self.client = client or YouTubeClient(ledger=self.ledger)
        self.channels = ChannelRepository(session)
        self.videos = VideoRepository(session)
        self.comments = CommentRepository(session)
        #: Respuestas traídas con `comments.list` además de las embebidas.
        self._replies_fetched = 0
        #: Se activa si alguna conversación se queda a medias, por límite o
        #: por error. La calidad de datos lo refleja en lugar de callarlo.
        self._replies_incomplete = False
        #: Hilos cuyas respuestas ya se han resuelto, para no pagarlas dos veces.
        self._threads_with_replies_done: set[str] = set()

    # -- Resolución --------------------------------------------------------

    def resolve_and_store_channel(self, raw_reference: str, *, force: bool = False) -> Channel:
        """Resuelve una referencia y guarda (o refresca) el canal."""
        if not settings.youtube_configured:
            raise YouTubeNotConfiguredError()
        reference = parse_channel_reference(raw_reference)

        # Si es un ID directo y ya está fresco, se evita la llamada a la API.
        if not force and reference.kind is ReferenceKind.CHANNEL_ID:
            existing = self.channels.get_by_youtube_id(reference.value)
            if existing is not None and self.channels.is_fresh(
                existing, settings.youtube_cache_ttl_hours
            ):
                self.ledger.record("channels.list", cache_status="hit")
                return existing

        payload = resolve_channel_payload(self.client, reference)
        if reference.kind is ReferenceKind.HANDLE and not payload.get("handle"):
            payload["handle"] = reference.value
        return self.channels.upsert(payload, source=DataSource.YOUTUBE_API)

    # -- Ingesta completa --------------------------------------------------

    def ingest_channel(
        self,
        channel: Channel,
        *,
        max_videos: int,
        max_comments_per_video: int,
        max_comments_per_channel: int,
        include_replies: bool = False,
        sampling_strategy: SamplingStrategy = SamplingStrategy.MIXED,
        run_id: uuid.UUID | None = None,
        on_progress: Any = None,
    ) -> IngestResult:
        """Descarga vídeos y comentarios respetando los límites indicados."""
        videos = self._ingest_videos(channel, max_videos=max_videos)
        result = IngestResult(channel=channel, videos=videos, ledger=self.ledger)

        if not videos:
            logger.info("no_videos_found", channel_id=str(channel.id))
            return result

        remaining_budget = max_comments_per_channel
        # Se reparte el presupuesto global entre los vídeos para que ningún
        # vídeo agote la muestra por sí solo.
        per_video_cap = min(
            max_comments_per_video,
            max(1, max_comments_per_channel // max(1, len(videos))) * 2,
        )

        for index, video in enumerate(videos):
            if remaining_budget <= 0:
                break
            if video.comments_disabled:
                result.videos_with_comments_disabled += 1
                continue

            budget = min(per_video_cap, remaining_budget)
            selected, buckets = self._ingest_comments_for_video(
                video,
                budget=budget,
                strategy=sampling_strategy,
                include_replies=include_replies,
            )

            # El tope global se aplica aquí, después de deduplicar y combinar
            # buckets, y no sobre lo descargado: así `max_comments_per_channel`
            # es un límite real de la muestra analizada, no una estimación.
            if len(selected) > remaining_budget:
                selected = selected[:remaining_budget]

            fetched = len(selected)
            if fetched == 0:
                result.videos_with_zero_comments += 1
            remaining_budget -= fetched
            result.comments_fetched += fetched
            result.selected_comments.extend(selected)
            for bucket, count in buckets.items():
                result.sampling_buckets[bucket] = result.sampling_buckets.get(bucket, 0) + count

            if on_progress is not None:
                on_progress(index + 1, len(videos))

        # Los buckets deben describir la muestra final, no lo que se llegó a
        # descargar antes de recortar por el tope global.
        result.sampling_buckets = count_sampling_buckets(result.selected_comments)
        result.replies_fetched = self._replies_fetched
        result.replies_incomplete = self._replies_incomplete

        if run_id is not None:
            self.comments.register_run_sample(run_id, result.selected_comments)

        return result

    def _ingest_videos(self, channel: Channel, *, max_videos: int) -> list[Video]:
        playlist_id = channel.uploads_playlist_id
        if not playlist_id:
            logger.warning("channel_without_uploads_playlist", channel_id=str(channel.id))
            return []

        # La playlist de subidas es más barata en cuota que `search.list`.
        video_ids: list[str] = []
        for item in self.client.iter_playlist_items(playlist_id, max_items=max_videos):
            status = (item.get("status") or {}).get("privacyStatus")
            if status in {"private", "privacyStatusUnspecified"}:
                continue
            video_id = map_playlist_item_to_video_id(item)
            if video_id:
                video_ids.append(video_id)

        # Deduplicación conservando el orden.
        video_ids = list(dict.fromkeys(video_ids))[:max_videos]
        if not video_ids:
            return []

        raw_videos = self.client.get_videos(video_ids)
        mapped = [map_video(item) for item in raw_videos]
        # Los vídeos borrados o privados desaparecen de `videos.list`: se ignoran.
        mapped = [v for v in mapped if v["youtube_video_id"]]
        stored = self.videos.upsert_many(channel.id, mapped, source=DataSource.YOUTUBE_API)

        order = {vid: i for i, vid in enumerate(video_ids)}
        stored.sort(key=lambda v: order.get(v.youtube_video_id, 10**6))
        return stored

    def _collect_missing_replies(
        self,
        thread: dict[str, Any],
        collected: dict[str, dict[str, Any]],
        *,
        bucket: str,
        budget: int,
    ) -> None:
        """Descarga con `comments.list` las respuestas que el hilo no trajo.

        `commentThreads.list` incluye sólo unas pocas respuestas por hilo. Si
        `totalReplyCount` dice que hay más, se piden aparte. Un fallo aquí no
        tira la ingesta: se anota que la conversación queda incompleta y se
        conserva todo lo ya obtenido, que es preferible a perderlo.
        """
        snippet = thread.get("snippet") or {}
        top = snippet.get("topLevelComment") or {}
        parent_id = str(top.get("id") or thread.get("id") or "")
        if not parent_id:
            return

        # Las estrategias mixtas recorren el mismo hilo dos veces (recientes y
        # relevantes). Sin esta marca se pagarían dos veces las mismas
        # respuestas en cuota.
        if parent_id in self._threads_with_replies_done:
            return

        total = to_int(snippet.get("totalReplyCount")) or 0
        embedded = (thread.get("replies") or {}).get("comments") or []
        if total <= len(embedded):
            self._threads_with_replies_done.add(parent_id)
            return

        room = budget - len(collected)
        if room <= 0:
            # El límite manda sobre la completitud: se anota y se para.
            self._replies_incomplete = True
            return

        self._threads_with_replies_done.add(parent_id)
        nuevas = 0
        try:
            # `comments.list` enumera el hilo **desde el principio**, así que
            # devuelve también las que ya venían embebidas. Por eso se pide
            # hasta `total` y se deja que la deduplicación haga su trabajo:
            # pedir sólo «las que faltan» traería duplicados y ninguna nueva.
            for item in self.client.iter_comment_replies(parent_id, max_replies=total):
                reply = map_comment_reply(item, parent_id)
                if reply is None:
                    continue
                key = reply["youtube_comment_id"]
                if key in collected:
                    continue
                if nuevas >= room:
                    # Cabían menos de las que hay: la conversación queda a medias.
                    self._replies_incomplete = True
                    break
                reply["sampling_bucket"] = bucket
                collected[key] = reply
                nuevas += 1
                self._replies_fetched += 1
        except YouTubeError as exc:
            # Ni se propaga ni se finge que la conversación está completa.
            logger.warning("replies_fetch_failed", parent_id=parent_id, code=exc.code)
            self._replies_incomplete = True

    def _ingest_comments_for_video(
        self,
        video: Video,
        *,
        budget: int,
        strategy: SamplingStrategy,
        include_replies: bool,
    ) -> tuple[list[tuple[uuid.UUID, str | None]], dict[str, int]]:
        collected: dict[str, dict[str, Any]] = {}
        buckets: dict[str, int] = {}

        for bucket, order, quota in _sampling_plan(strategy, budget):
            before = len(collected)
            for thread in self.client.iter_comment_threads(
                video.youtube_video_id,
                max_comments=quota,
                order=order,
                include_replies=include_replies,
            ):
                for comment in map_comment_thread(thread, include_replies=include_replies):
                    key = comment["youtube_comment_id"]
                    # Deduplicación entre estrategias solapadas.
                    if key in collected:
                        continue
                    comment["sampling_bucket"] = bucket
                    collected[key] = comment

                # Las respuestas embebidas en el hilo pueden no ser todas. Se
                # piden las que falten justo después del hilo, para que cada
                # conversación quede junta y en orden.
                if include_replies:
                    self._collect_missing_replies(thread, collected, bucket=bucket, budget=budget)
            buckets[bucket] = buckets.get(bucket, 0) + (len(collected) - before)

        if not collected:
            return [], buckets

        rows = list(collected.values())[:budget]
        stored = self.comments.upsert_many(video.id, rows, source=DataSource.YOUTUBE_API)

        # Se conserva el orden de descarga: es lo que hace reproducible la
        # muestra. Si un comentario no vuelve del upsert, no se inventa.
        selected: list[tuple[uuid.UUID, str | None]] = []
        for row in rows:
            comment_id = stored.get(str(row["youtube_comment_id"]))
            if comment_id is not None:
                selected.append((comment_id, row.get("sampling_bucket")))
        return selected, buckets

    def touch_channel(self, channel: Channel) -> None:
        channel.last_fetched_at = datetime.now(UTC)
        self.session.add(channel)
        self.session.flush()


__all__ = ["IngestResult", "YouTubeIngestService", "resolve_channel_payload"]
