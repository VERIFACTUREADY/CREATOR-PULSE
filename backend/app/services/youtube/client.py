"""Cliente HTTP de la YouTube Data API v3.

Sólo usa endpoints oficiales. No hace scraping de HTML ni automatiza el
navegador. Incluye reintentos con retroceso exponencial, tiempos de espera y
traducción de los errores de Google a errores de dominio en español.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import (
    YouTubeError,
    YouTubeInvalidKeyError,
    YouTubeNotConfiguredError,
    YouTubeQuotaExceededError,
)
from app.core.logging import get_logger
from app.services.youtube.quota import estimate_cost

logger = get_logger(__name__)

#: Razones de error de Google que indican cuota agotada.
_QUOTA_REASONS = frozenset({"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"})
#: Razones que indican una clave inválida o la API deshabilitada.
_KEY_REASONS = frozenset(
    {"keyInvalid", "accessNotConfigured", "forbidden", "ipRefererBlocked", "badRequest"}
)
#: Razones que indican que el recurso no admite comentarios.
COMMENTS_DISABLED_REASONS = frozenset({"commentsDisabled", "videoNotFound"})

_RETRYABLE_STATUS = frozenset({500, 502, 503, 504})


@dataclass
class UsageRecord:
    """Una llamada registrada en el libro mayor de uso."""

    endpoint: str
    request_count: int = 1
    estimated_quota_units: int = 0
    cache_status: str = "miss"
    success: bool = True
    error_code: str | None = None


@dataclass
class UsageLedger:
    """Acumula el consumo de API de una ejecución."""

    records: list[UsageRecord] = field(default_factory=list)

    def record(
        self,
        endpoint: str,
        *,
        success: bool = True,
        cache_status: str = "miss",
        error_code: str | None = None,
    ) -> None:
        units = estimate_cost(endpoint) if cache_status == "miss" else 0
        self.records.append(
            UsageRecord(
                endpoint=endpoint,
                estimated_quota_units=units,
                cache_status=cache_status,
                success=success,
                error_code=error_code,
            )
        )

    @property
    def total_requests(self) -> int:
        return sum(r.request_count for r in self.records)

    @property
    def total_quota_units(self) -> int:
        return sum(r.estimated_quota_units for r in self.records)

    def summary(self) -> dict[str, Any]:
        by_endpoint: dict[str, dict[str, int]] = {}
        for rec in self.records:
            bucket = by_endpoint.setdefault(
                rec.endpoint, {"requests": 0, "quota_units": 0, "errors": 0, "cached": 0}
            )
            bucket["requests"] += rec.request_count
            bucket["quota_units"] += rec.estimated_quota_units
            if not rec.success:
                bucket["errors"] += 1
            if rec.cache_status == "hit":
                bucket["cached"] += 1
        return {
            "total_requests": self.total_requests,
            "total_estimated_quota_units": self.total_quota_units,
            "by_endpoint": by_endpoint,
        }


def _extract_error(payload: dict[str, Any]) -> tuple[str, str]:
    """Devuelve `(reason, message)` del cuerpo de error de Google."""
    error = payload.get("error") or {}
    errors = error.get("errors") or []
    reason = ""
    if errors and isinstance(errors, list) and isinstance(errors[0], dict):
        reason = str(errors[0].get("reason", ""))
    if not reason:
        reason = str(error.get("status", ""))
    return reason, str(error.get("message", ""))


class YouTubeClient:
    """Cliente síncrono de la YouTube Data API v3.

    Se usa desde el worker (no dentro de la petición web), por lo que un cliente
    síncrono es suficiente y simplifica el manejo de reintentos.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        client: httpx.Client | None = None,
        ledger: UsageLedger | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.youtube_api_key
        self.base_url = (base_url or settings.youtube_api_base_url).rstrip("/")
        self.timeout = timeout or settings.youtube_request_timeout_seconds
        self.max_retries = max_retries if max_retries is not None else settings.youtube_max_retries
        self.ledger = ledger or UsageLedger()
        self._sleep = sleep
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=self.timeout)

    def __enter__(self) -> YouTubeClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # -- Petición base ----------------------------------------------------

    def _request(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta `GET {base}/{endpoint}` con reintentos y backoff exponencial."""
        if not self.api_key:
            raise YouTubeNotConfiguredError()

        url = f"{self.base_url}/{endpoint.split('.')[0]}"
        query = {k: v for k, v in params.items() if v is not None}
        query["key"] = self.api_key

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.get(url, params=query, timeout=self.timeout)
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning("youtube_timeout", endpoint=endpoint, attempt=attempt)
                if attempt >= self.max_retries:
                    self.ledger.record(endpoint, success=False, error_code="timeout")
                    raise YouTubeError(
                        "La API de YouTube ha tardado demasiado en responder. "
                        "Inténtalo de nuevo en unos minutos.",
                        detail=str(exc),
                        code="youtube_timeout",
                    ) from exc
                self._backoff(attempt)
                continue
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("youtube_network_error", endpoint=endpoint, attempt=attempt)
                if attempt >= self.max_retries:
                    self.ledger.record(endpoint, success=False, error_code="network")
                    raise YouTubeError(
                        "No se ha podido conectar con la API de YouTube.",
                        detail=str(exc),
                        code="youtube_red",
                    ) from exc
                self._backoff(attempt)
                continue

            if response.status_code == 200:
                self.ledger.record(endpoint, success=True)
                return dict(response.json())

            payload = self._safe_json(response)
            reason, message = _extract_error(payload)

            if response.status_code in _RETRYABLE_STATUS and attempt < self.max_retries:
                logger.warning(
                    "youtube_retryable_status",
                    endpoint=endpoint,
                    status=response.status_code,
                    attempt=attempt,
                )
                self._backoff(attempt)
                continue

            self.ledger.record(endpoint, success=False, error_code=reason or "http_error")
            raise self._translate_error(response.status_code, reason, message, endpoint)

        # Defensivo: el bucle siempre devuelve o lanza.
        raise YouTubeError(detail=str(last_error))  # pragma: no cover

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any]:
        try:
            data = response.json()
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}

    def _backoff(self, attempt: int) -> None:
        """Retroceso exponencial con jitter: 1s, 2s, 4s, 8s (máx. 30s)."""
        delay = min(2.0**attempt, 30.0) + random.uniform(0, 0.5)  # noqa: S311
        self._sleep(delay)

    @staticmethod
    def _translate_error(status: int, reason: str, message: str, endpoint: str) -> YouTubeError:
        detail = f"{endpoint} -> HTTP {status} ({reason}): {message}"
        if reason in _QUOTA_REASONS:
            return YouTubeQuotaExceededError(detail=detail)
        if status == 403 and reason in _KEY_REASONS:
            return YouTubeInvalidKeyError(detail=detail)
        if status == 400 and reason in _KEY_REASONS:
            return YouTubeInvalidKeyError(detail=detail)
        if status == 404:
            return YouTubeError(
                "El recurso solicitado no existe o ya no es público.",
                detail=detail,
                code="youtube_no_encontrado",
                status_code=404,
            )
        return YouTubeError(detail=detail)

    # -- Endpoints --------------------------------------------------------

    def get_channel_by_id(self, channel_id: str) -> dict[str, Any] | None:
        data = self._request(
            "channels.list",
            {"part": "snippet,statistics,contentDetails,brandingSettings", "id": channel_id},
        )
        items = data.get("items") or []
        return dict(items[0]) if items else None

    def get_channel_by_handle(self, handle: str) -> dict[str, Any] | None:
        data = self._request(
            "channels.list",
            {
                "part": "snippet,statistics,contentDetails,brandingSettings",
                "forHandle": f"@{handle.lstrip('@')}",
            },
        )
        items = data.get("items") or []
        return dict(items[0]) if items else None

    def get_channel_by_username(self, username: str) -> dict[str, Any] | None:
        data = self._request(
            "channels.list",
            {
                "part": "snippet,statistics,contentDetails,brandingSettings",
                "forUsername": username,
            },
        )
        items = data.get("items") or []
        return dict(items[0]) if items else None

    def search_channel(self, query: str) -> dict[str, Any] | None:
        """Búsqueda de canal. Cuesta 100 unidades: sólo como último recurso.

        Se usa únicamente para resolver URLs personalizadas heredadas (`/c/…`)
        que la API no puede resolver de otra forma. Nunca para listar vídeos.
        """
        data = self._request(
            "search.list", {"part": "snippet", "type": "channel", "q": query, "maxResults": 1}
        )
        items = data.get("items") or []
        if not items:
            return None
        channel_id = (items[0].get("id") or {}).get("channelId") or items[0].get("snippet", {}).get(
            "channelId"
        )
        if not channel_id:
            return None
        return self.get_channel_by_id(str(channel_id))

    def iter_playlist_items(
        self, playlist_id: str, *, max_items: int, page_size: int = 50
    ) -> Iterator[dict[str, Any]]:
        """Itera los elementos de una playlist con paginación acotada."""
        yielded = 0
        page_token: str | None = None
        seen_tokens: set[str] = set()

        while yielded < max_items:
            remaining = max_items - yielded
            data = self._request(
                "playlistItems.list",
                {
                    "part": "snippet,contentDetails,status",
                    "playlistId": playlist_id,
                    "maxResults": min(page_size, max(1, remaining)),
                    "pageToken": page_token,
                },
            )
            items = data.get("items") or []
            if not items:
                return
            for item in items:
                yield dict(item)
                yielded += 1
                if yielded >= max_items:
                    return
            page_token = data.get("nextPageToken")
            # La paginación nunca es ilimitada: se corta ante un token repetido.
            if not page_token or page_token in seen_tokens:
                return
            seen_tokens.add(page_token)

    def get_videos(self, video_ids: list[str], *, batch_size: int = 50) -> list[dict[str, Any]]:
        """Obtiene los vídeos en lotes de como máximo 50 IDs."""
        results: list[dict[str, Any]] = []
        unique_ids = list(dict.fromkeys(v for v in video_ids if v))
        for start in range(0, len(unique_ids), batch_size):
            batch = unique_ids[start : start + batch_size]
            data = self._request(
                "videos.list",
                {
                    "part": "snippet,statistics,contentDetails,status,liveStreamingDetails",
                    "id": ",".join(batch),
                    "maxResults": len(batch),
                },
            )
            results.extend(dict(item) for item in (data.get("items") or []))
        return results

    def iter_comment_threads(
        self,
        video_id: str,
        *,
        max_comments: int,
        order: str = "time",
        page_size: int = 100,
        include_replies: bool = False,
    ) -> Iterator[dict[str, Any]]:
        """Itera hilos de comentarios de un vídeo.

        Si el vídeo tiene los comentarios desactivados o no existe, no lanza:
        simplemente no produce ningún elemento (el llamador lo marca).
        """
        yielded = 0
        page_token: str | None = None
        seen_tokens: set[str] = set()

        while yielded < max_comments:
            remaining = max_comments - yielded
            params: dict[str, Any] = {
                "part": "snippet,replies" if include_replies else "snippet",
                "videoId": video_id,
                "maxResults": min(page_size, max(1, remaining)),
                "order": order,
                "textFormat": "plainText",
                "pageToken": page_token,
            }
            try:
                data = self._request("commentThreads.list", params)
            except YouTubeError as exc:
                detail = (exc.detail or "").lower()
                if "commentsdisabled" in detail or "videonotfound" in detail:
                    logger.info("comments_unavailable", video_id=video_id, reason=exc.code)
                    return
                raise

            items = data.get("items") or []
            if not items:
                return
            for item in items:
                yield dict(item)
                yielded += 1
                if yielded >= max_comments:
                    return
            page_token = data.get("nextPageToken")
            if not page_token or page_token in seen_tokens:
                return
            seen_tokens.add(page_token)


__all__ = [
    "COMMENTS_DISABLED_REASONS",
    "UsageLedger",
    "UsageRecord",
    "YouTubeClient",
]
