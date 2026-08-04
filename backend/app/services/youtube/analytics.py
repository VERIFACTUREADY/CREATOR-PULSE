"""Cliente de la YouTube Analytics API v2 (modo propietario).

Estas métricas **no existen en modo público**: requieren la autorización del
dueño del canal. Nunca se estiman ni se rellenan con valores inventados; si una
métrica no está disponible se devuelve `None` y la interfaz lo indica.

Nota sobre impresiones y CTR: Google las expone en un grupo de métricas aparte
que no todas las cuentas tienen habilitado. Se piden en una consulta separada
para que, si fallan, el resto del informe siga llegando.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

ANALYTICS_ENDPOINT = "https://youtubeanalytics.googleapis.com/v2/reports"

#: Métricas centrales, disponibles para cualquier canal con analíticas.
CORE_METRICS: tuple[str, ...] = (
    "views",
    "estimatedMinutesWatched",
    "averageViewDuration",
    "averageViewPercentage",
    "subscribersGained",
    "subscribersLost",
    "likes",
    "comments",
    "shares",
)

#: Métricas que dependen de que la cuenta tenga datos de impresiones.
IMPRESSION_METRICS: tuple[str, ...] = (
    "impressions",
    "impressionsClickThroughRate",
)

#: Ventana por defecto del informe.
DEFAULT_WINDOW_DAYS = 28


class AnalyticsError(AppError):
    code = "analytics_error"
    status_code = 502
    message = "No se han podido obtener las analíticas privadas de tu canal."


class AnalyticsForbiddenError(AnalyticsError):
    code = "analytics_sin_permiso"
    status_code = 403
    message = (
        "La cuenta conectada no tiene permiso para ver las analíticas de este canal. "
        "Conecta la cuenta que es propietaria del canal."
    )


@dataclass
class MetricSeries:
    """Serie temporal de una métrica."""

    dimension: str
    rows: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class OwnerAnalytics:
    """Informe de propietario. Los `None` significan «no disponible»."""

    start_date: str
    end_date: str
    views: int | None = None
    estimated_minutes_watched: int | None = None
    average_view_duration_seconds: float | None = None
    average_view_percentage: float | None = None
    subscribers_gained: int | None = None
    subscribers_lost: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    impressions: int | None = None
    impressions_ctr: float | None = None
    daily: list[dict[str, Any]] = field(default_factory=list)
    traffic_sources: list[dict[str, Any]] = field(default_factory=list)
    geography: list[dict[str, Any]] = field(default_factory=list)
    top_videos: list[dict[str, Any]] = field(default_factory=list)
    unavailable_es: list[str] = field(default_factory=list)

    @property
    def net_subscribers(self) -> int | None:
        if self.subscribers_gained is None or self.subscribers_lost is None:
            return None
        return self.subscribers_gained - self.subscribers_lost

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "views": self.views,
            "estimated_minutes_watched": self.estimated_minutes_watched,
            "average_view_duration_seconds": self.average_view_duration_seconds,
            "average_view_percentage": self.average_view_percentage,
            "subscribers_gained": self.subscribers_gained,
            "subscribers_lost": self.subscribers_lost,
            "net_subscribers": self.net_subscribers,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "impressions": self.impressions,
            "impressions_ctr": self.impressions_ctr,
            "daily": self.daily,
            "traffic_sources": self.traffic_sources,
            "geography": self.geography,
            "top_videos": self.top_videos,
            "unavailable_es": self.unavailable_es,
        }


#: Nombres legibles de las fuentes de tráfico que devuelve la API.
TRAFFIC_SOURCE_LABELS_ES: dict[str, str] = {
    "ADVERTISING": "Publicidad",
    "ANNOTATION": "Anotaciones",
    "CAMPAIGN_CARD": "Tarjetas de campaña",
    "END_SCREEN": "Pantalla final",
    "EXT_URL": "Enlaces externos",
    "NO_LINK_EMBEDDED": "Reproductor incrustado",
    "NO_LINK_OTHER": "Otras fuentes",
    "NOTIFICATION": "Notificaciones",
    "PLAYLIST": "Listas de reproducción",
    "PROMOTED": "Contenido promocionado",
    "RELATED_VIDEO": "Vídeos sugeridos",
    "SHORTS": "Feed de Shorts",
    "SOUND_PAGE": "Página de sonido",
    "SUBSCRIBER": "Feed de suscriptores",
    "YT_CHANNEL": "Página del canal",
    "YT_OTHER_PAGE": "Otras páginas de YouTube",
    "YT_SEARCH": "Búsqueda de YouTube",
    "HASHTAGS": "Hashtags",
}


def traffic_source_label(code: str) -> str:
    return TRAFFIC_SOURCE_LABELS_ES.get(code, code.replace("_", " ").capitalize())


class YouTubeAnalyticsClient:
    """Consulta la YouTube Analytics API con el token del propietario."""

    def __init__(
        self,
        access_token: str,
        *,
        client: httpx.Client | None = None,
        timeout: float | None = None,
    ) -> None:
        self.access_token = access_token
        self.timeout = timeout or settings.youtube_request_timeout_seconds
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=self.timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> YouTubeAnalyticsClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- Consulta base ----------------------------------------------------

    def query(
        self,
        *,
        channel_id: str,
        start_date: str,
        end_date: str,
        metrics: tuple[str, ...] | list[str],
        dimensions: str | None = None,
        sort: str | None = None,
        max_results: int | None = None,
        filters: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "ids": f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": ",".join(metrics),
        }
        if dimensions:
            params["dimensions"] = dimensions
        if sort:
            params["sort"] = sort
        if max_results:
            params["maxResults"] = max_results
        if filters:
            params["filters"] = filters

        try:
            response = self._client.get(
                ANALYTICS_ENDPOINT,
                params=params,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise AnalyticsError(detail=f"red: {exc}") from exc

        if response.status_code == 200:
            return dict(response.json())

        if response.status_code in (401, 403):
            raise AnalyticsForbiddenError(detail=f"HTTP {response.status_code}")

        raise AnalyticsError(detail=f"HTTP {response.status_code}: {response.text[:200]}")

    # -- Utilidades -------------------------------------------------------

    @staticmethod
    def _rows_to_dicts(payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Convierte la respuesta columnar de la API en diccionarios."""
        headers = [h.get("name") for h in payload.get("columnHeaders", [])]
        return [dict(zip(headers, row, strict=False)) for row in payload.get("rows", [])]

    @staticmethod
    def _first_row(payload: dict[str, Any]) -> dict[str, Any]:
        rows = YouTubeAnalyticsClient._rows_to_dicts(payload)
        return rows[0] if rows else {}

    # -- Informe completo -------------------------------------------------

    def fetch_report(
        self,
        channel_id: str,
        *,
        days: int = DEFAULT_WINDOW_DAYS,
        today: date | None = None,
    ) -> OwnerAnalytics:
        """Construye el informe de propietario de los últimos `days` días.

        Cada bloque se pide por separado para que el fallo de uno (típicamente
        impresiones, que no todas las cuentas tienen) no tumbe el informe entero.
        """
        # YouTube Analytics tiene 2-3 días de retraso: pedir hasta hoy devuelve
        # ceros que parecerían una caída de audiencia.
        reference = today or datetime.now(UTC).date()
        end = reference - timedelta(days=3)
        start = end - timedelta(days=days - 1)
        start_date, end_date = start.isoformat(), end.isoformat()

        report = OwnerAnalytics(start_date=start_date, end_date=end_date)
        unavailable: list[str] = []

        # --- Métricas centrales ---
        totals = self._first_row(
            self.query(
                channel_id=channel_id,
                start_date=start_date,
                end_date=end_date,
                metrics=CORE_METRICS,
            )
        )
        report.views = _as_int(totals.get("views"))
        report.estimated_minutes_watched = _as_int(totals.get("estimatedMinutesWatched"))
        report.average_view_duration_seconds = _as_float(totals.get("averageViewDuration"))
        report.average_view_percentage = _as_float(totals.get("averageViewPercentage"))
        report.subscribers_gained = _as_int(totals.get("subscribersGained"))
        report.subscribers_lost = _as_int(totals.get("subscribersLost"))
        report.likes = _as_int(totals.get("likes"))
        report.comments = _as_int(totals.get("comments"))
        report.shares = _as_int(totals.get("shares"))

        # --- Impresiones y CTR (pueden no estar disponibles) ---
        try:
            impressions = self._first_row(
                self.query(
                    channel_id=channel_id,
                    start_date=start_date,
                    end_date=end_date,
                    metrics=IMPRESSION_METRICS,
                )
            )
            report.impressions = _as_int(impressions.get("impressions"))
            report.impressions_ctr = _as_float(impressions.get("impressionsClickThroughRate"))
        except AnalyticsError as exc:
            logger.info("analytics_impressions_unavailable", detail=exc.detail)
            unavailable.append("Tu cuenta no expone impresiones ni porcentaje de clics por la API.")

        # --- Evolución diaria ---
        try:
            report.daily = self._rows_to_dicts(
                self.query(
                    channel_id=channel_id,
                    start_date=start_date,
                    end_date=end_date,
                    metrics=("views", "estimatedMinutesWatched", "subscribersGained"),
                    dimensions="day",
                    sort="day",
                )
            )
        except AnalyticsError:
            unavailable.append("No se ha podido obtener la evolución diaria.")

        # --- Fuentes de tráfico ---
        try:
            rows = self._rows_to_dicts(
                self.query(
                    channel_id=channel_id,
                    start_date=start_date,
                    end_date=end_date,
                    metrics=("views", "estimatedMinutesWatched"),
                    dimensions="insightTrafficSourceType",
                    sort="-views",
                )
            )
            report.traffic_sources = [
                {
                    **row,
                    "label_es": traffic_source_label(str(row.get("insightTrafficSourceType", ""))),
                }
                for row in rows
            ]
        except AnalyticsError:
            unavailable.append("No se han podido obtener las fuentes de tráfico.")

        # --- Geografía ---
        try:
            report.geography = self._rows_to_dicts(
                self.query(
                    channel_id=channel_id,
                    start_date=start_date,
                    end_date=end_date,
                    metrics=("views", "estimatedMinutesWatched"),
                    dimensions="country",
                    sort="-views",
                    max_results=15,
                )
            )
        except AnalyticsError:
            unavailable.append("No se ha podido obtener la geografía de la audiencia.")

        # --- Vídeos con mejor retención ---
        try:
            report.top_videos = self._rows_to_dicts(
                self.query(
                    channel_id=channel_id,
                    start_date=start_date,
                    end_date=end_date,
                    metrics=(
                        "views",
                        "estimatedMinutesWatched",
                        "averageViewDuration",
                        "averageViewPercentage",
                    ),
                    dimensions="video",
                    sort="-estimatedMinutesWatched",
                    max_results=20,
                )
            )
        except AnalyticsError:
            unavailable.append("No se ha podido obtener el detalle por vídeo.")

        report.unavailable_es = unavailable
        return report


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


__all__ = [
    "ANALYTICS_ENDPOINT",
    "CORE_METRICS",
    "DEFAULT_WINDOW_DAYS",
    "IMPRESSION_METRICS",
    "TRAFFIC_SOURCE_LABELS_ES",
    "AnalyticsError",
    "AnalyticsForbiddenError",
    "MetricSeries",
    "OwnerAnalytics",
    "YouTubeAnalyticsClient",
    "traffic_source_label",
]
