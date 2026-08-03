"""Etapa 7 del pipeline: análisis temporal y de tendencias.

Las tendencias se calculan sobre **cuotas** (share) y no sobre recuentos
absolutos: si el canal recibe más comentarios en total, todos los temas subirían
en términos absolutos y la comparación no diría nada. Comparar la proporción que
representa cada tema en dos ventanas evita ese sesgo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.models.enums import TrendDirection

#: Cambio relativo mínimo de cuota para considerar que hay tendencia.
TREND_THRESHOLD = 0.20
#: Comentarios mínimos en cada ventana para que la tendencia sea interpretable.
MIN_COMMENTS_PER_WINDOW = 8


@dataclass(slots=True)
class TimeWindows:
    """Ventanas temporales adaptativas calculadas a partir de los datos."""

    split_point: datetime | None
    start: datetime | None
    end: datetime | None
    recent_total: int
    previous_total: int
    span_days: float

    @property
    def usable(self) -> bool:
        return (
            self.split_point is not None
            and self.recent_total >= MIN_COMMENTS_PER_WINDOW
            and self.previous_total >= MIN_COMMENTS_PER_WINDOW
        )


@dataclass(slots=True)
class TrendResult:
    recent_share: float | None
    previous_share: float | None
    change: float | None
    direction: str
    confidence: float
    note_es: str | None = None


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def build_time_windows(dates: list[datetime | None]) -> TimeWindows:
    """Divide la muestra en dos mitades temporales de tamaño comparable.

    Se usa la mediana de las fechas en lugar de un número fijo de días para que
    la ventana se adapte tanto a canales que publican a diario como a los que
    publican una vez al mes.
    """
    valid = sorted(_as_utc(d) for d in dates if d is not None)
    if len(valid) < MIN_COMMENTS_PER_WINDOW * 2:
        return TimeWindows(
            split_point=None,
            start=valid[0] if valid else None,
            end=valid[-1] if valid else None,
            recent_total=0,
            previous_total=0,
            span_days=0.0,
        )

    split = valid[len(valid) // 2]
    span = (valid[-1] - valid[0]).total_seconds() / 86400.0

    # Si toda la muestra cabe en menos de un día, la comparación no aporta.
    if span < 1.0:
        return TimeWindows(
            split_point=None,
            start=valid[0],
            end=valid[-1],
            recent_total=0,
            previous_total=0,
            span_days=span,
        )

    recent_total = sum(1 for d in valid if d >= split)
    previous_total = len(valid) - recent_total
    return TimeWindows(
        split_point=split,
        start=valid[0],
        end=valid[-1],
        recent_total=recent_total,
        previous_total=previous_total,
        span_days=span,
    )


def compute_trend(
    topic_dates: list[datetime | None],
    windows: TimeWindows,
) -> TrendResult:
    """Compara la cuota del tema en la ventana reciente y en la anterior."""
    if not windows.usable or windows.split_point is None:
        return TrendResult(
            recent_share=None,
            previous_share=None,
            change=None,
            direction=TrendDirection.UNKNOWN,
            confidence=0.0,
            note_es="No hay suficiente histórico de comentarios para calcular una tendencia.",
        )

    split = windows.split_point
    valid = [_as_utc(d) for d in topic_dates if d is not None]
    recent_hits = sum(1 for d in valid if d >= split)
    previous_hits = len(valid) - recent_hits

    recent_share = recent_hits / windows.recent_total if windows.recent_total else 0.0
    previous_share = previous_hits / windows.previous_total if windows.previous_total else 0.0

    if previous_share == 0.0 and recent_share == 0.0:
        return TrendResult(
            recent_share=0.0,
            previous_share=0.0,
            change=0.0,
            direction=TrendDirection.STABLE,
            confidence=0.2,
        )

    if previous_share == 0.0:
        # Tema nuevo: sube, pero con confianza limitada por falta de referencia.
        change = 1.0
        direction = TrendDirection.RISING
        confidence = min(0.6, 0.2 + recent_hits / 40.0)
        return TrendResult(
            recent_share=round(recent_share, 4),
            previous_share=0.0,
            change=change,
            direction=direction,
            confidence=round(confidence, 3),
            note_es="Tema nuevo: no aparecía en el periodo anterior.",
        )

    change = (recent_share - previous_share) / previous_share

    if change > TREND_THRESHOLD:
        direction = TrendDirection.RISING
    elif change < -TREND_THRESHOLD:
        direction = TrendDirection.FALLING
    else:
        direction = TrendDirection.STABLE

    # La confianza depende del volumen absoluto en ambas ventanas.
    volume_factor = min(1.0, (recent_hits + previous_hits) / 60.0)
    magnitude_factor = min(1.0, abs(change) / 1.0)
    confidence = 0.25 + 0.5 * volume_factor + 0.25 * magnitude_factor
    if recent_hits < 3 or previous_hits < 3:
        confidence *= 0.6

    return TrendResult(
        recent_share=round(recent_share, 4),
        previous_share=round(previous_share, 4),
        change=round(change, 4),
        direction=direction,
        confidence=round(min(0.95, confidence), 3),
    )


def mentions_per_1000(mentions: int, total_comments: int) -> float:
    """Menciones por cada 1.000 comentarios analizados."""
    if total_comments <= 0:
        return 0.0
    return round((mentions / total_comments) * 1000.0, 2)


def coverage(unique_videos: int, total_videos: int) -> float:
    """Proporción de vídeos analizados en los que aparece el tema."""
    if total_videos <= 0:
        return 0.0
    return round(min(1.0, unique_videos / total_videos), 4)


def dominant_source_share(counts_by_video: dict[str, int]) -> float:
    """Cuota del vídeo que más comentarios aporta a un tema.

    Un valor alto indica que el tema puede venir de un único vídeo viral y no
    de un patrón sostenido del canal.
    """
    total = sum(counts_by_video.values())
    if total <= 0:
        return 0.0
    return round(max(counts_by_video.values()) / total, 4)


def date_coverage_summary(dates: list[datetime | None]) -> dict[str, object]:
    """Resumen de la cobertura temporal de la muestra."""
    valid = sorted(_as_utc(d) for d in dates if d is not None)
    if not valid:
        return {"first": None, "last": None, "span_days": 0.0, "missing_dates": len(dates)}
    span = (valid[-1] - valid[0]).total_seconds() / 86400.0
    return {
        "first": valid[0].isoformat(),
        "last": valid[-1].isoformat(),
        "span_days": round(span, 2),
        "missing_dates": len(dates) - len(valid),
    }


def recent_window_days(windows: TimeWindows) -> float:
    if windows.split_point is None or windows.end is None:
        return 0.0
    return round((windows.end - windows.split_point).total_seconds() / 86400.0, 2)


def is_recent(date: datetime | None, *, days: int = 30) -> bool:
    if date is None:
        return False
    return datetime.now(UTC) - _as_utc(date) <= timedelta(days=days)


__all__ = [
    "MIN_COMMENTS_PER_WINDOW",
    "TREND_THRESHOLD",
    "TimeWindows",
    "TrendResult",
    "build_time_windows",
    "compute_trend",
    "coverage",
    "date_coverage_summary",
    "dominant_source_share",
    "is_recent",
    "mentions_per_1000",
    "recent_window_days",
]
