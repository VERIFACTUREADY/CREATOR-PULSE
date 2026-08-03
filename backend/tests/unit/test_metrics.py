"""Pruebas de tendencias, métricas de rendimiento y calidad de datos."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from app.models.enums import TrendDirection
from app.services.analysis.clustering import cluster_embeddings
from app.services.analysis.embeddings import HashingEmbeddingBackend, resize_vector
from app.services.analysis.performance import (
    VideoPerformance,
    VideoStats,
    age_days,
    compute_baseline,
    compute_performance,
    per_1000,
    safe_ratio,
    topic_performance_association,
    viral_concentration,
)
from app.services.analysis.quality import DataQuality, finalise_quality, language_distribution
from app.services.analysis.trends import (
    build_time_windows,
    compute_trend,
    coverage,
    date_coverage_summary,
    dominant_source_share,
    mentions_per_1000,
)

NOW = datetime(2024, 6, 1, tzinfo=UTC)


# --- División segura --------------------------------------------------------


def test_safe_ratio_handles_zero_denominator() -> None:
    assert safe_ratio(10, 0) is None
    assert safe_ratio(10, None) is None
    assert safe_ratio(None, 10) is None
    assert safe_ratio(10, 5) == 2.0


def test_per_1000_handles_zero_views() -> None:
    assert per_1000(50, 0) is None
    assert per_1000(50, 10_000) == 5.0


def test_per_1000_with_missing_counts() -> None:
    assert per_1000(None, 1000) is None


# --- Métricas de vídeo ------------------------------------------------------


def _stats(index: int, views: int, likes: int, comments: int, days: int) -> VideoStats:
    return VideoStats(
        video_id=f"v{index}",
        views=views,
        likes=likes,
        comments=comments,
        published_at=NOW - timedelta(days=days),
        title=f"Vídeo {index}",
    )


def test_baseline_uses_median_not_mean() -> None:
    """Un vídeo viral no debe arrastrar la referencia del canal."""
    videos = [_stats(i, 10_000, 400, 50, 30) for i in range(5)]
    videos.append(_stats(99, 5_000_000, 200_000, 20_000, 30))
    baseline = compute_baseline(videos)
    assert baseline.median_views == 10_000


def test_baseline_with_no_videos() -> None:
    baseline = compute_baseline([])
    assert baseline.video_count == 0
    assert baseline.notes


def test_baseline_warns_with_few_videos() -> None:
    assert compute_baseline([_stats(0, 100, 10, 5, 10)]).notes


def test_performance_bands() -> None:
    videos = [_stats(i, 10_000, 400, 50, 60) for i in range(5)]
    baseline = compute_baseline(videos)

    over = compute_performance(_stats(9, 30_000, 400, 50, 60), baseline, now=NOW)
    under = compute_performance(_stats(8, 2_000, 400, 50, 60), baseline, now=NOW)
    normal = compute_performance(_stats(7, 10_000, 400, 50, 60), baseline, now=NOW)

    assert over.performance_band == "por_encima"
    assert under.performance_band == "por_debajo"
    assert normal.performance_band == "normal"


def test_recent_video_gets_age_caveat_and_no_band() -> None:
    """Un vídeo de horas no se compara directamente con uno de un año."""
    baseline = compute_baseline([_stats(i, 10_000, 400, 50, 300) for i in range(5)])
    fresh = compute_performance(_stats(9, 200, 5, 1, 0), baseline, now=NOW)
    assert fresh.age_caveat
    assert fresh.performance_band == "reciente"


def test_performance_with_zero_views_does_not_crash() -> None:
    baseline = compute_baseline([_stats(0, 0, 0, 0, 10)])
    result = compute_performance(_stats(0, 0, 0, 0, 10), baseline, now=NOW)
    assert result.likes_per_1000_views is None
    assert result.views_relative_to_median is None


def test_performance_with_missing_stats() -> None:
    baseline = compute_baseline([_stats(i, 10_000, 400, 50, 30) for i in range(3)])
    hidden = VideoStats(video_id="x", views=None, likes=None, comments=None, published_at=None)
    result = compute_performance(hidden, baseline, now=NOW)
    assert result.likes_per_1000_views is None
    assert result.age_days is None


def test_age_adjusted_velocity_avoids_division_by_zero() -> None:
    baseline = compute_baseline([_stats(0, 1000, 10, 5, 1)])
    result = compute_performance(_stats(0, 1000, 10, 5, 0), baseline, now=NOW)
    assert result.age_adjusted_view_velocity is not None
    assert result.age_adjusted_view_velocity > 0


def test_age_days_of_none() -> None:
    assert age_days(None) is None


def test_viral_concentration() -> None:
    assert viral_concentration([100, 100, 100, 100]) == 0.25
    assert viral_concentration([10, 10, 980]) > 0.9
    assert viral_concentration([]) == 0.0
    assert viral_concentration([None, None]) == 0.0


# --- Asociación tema/rendimiento -------------------------------------------


def _perf(video_id: str, relative: float) -> VideoPerformance:
    return VideoPerformance(
        video_id=video_id,
        views_relative_to_median=relative,
        engagement_actions_per_1000_views=relative * 10,
        age_caveat=False,
    )


def test_association_requires_enough_videos_on_both_sides() -> None:
    performances = {"a": _perf("a", 1.5), "b": _perf("b", 0.5)}
    result = topic_performance_association({"a"}, performances)
    assert result["available"] is False
    assert "reason_es" in result


def test_association_reports_positive_direction() -> None:
    performances = {
        "a": _perf("a", 1.6),
        "b": _perf("b", 1.5),
        "c": _perf("c", 0.6),
        "d": _perf("d", 0.5),
    }
    result = topic_performance_association({"a", "b"}, performances)
    assert result["available"] is True
    assert result["direction"] == "positiva"
    # Nunca se afirma causalidad.
    assert "no una relación de causa" in result["caveat_es"]


def test_association_excludes_recent_videos() -> None:
    fresh = _perf("a", 5.0)
    fresh.age_caveat = True
    performances = {"a": fresh, "b": _perf("b", 1.0), "c": _perf("c", 1.0)}
    result = topic_performance_association({"a"}, performances)
    assert result["available"] is False


# --- Tendencias -------------------------------------------------------------


def _dates(count: int, start_days_ago: int, step: float = 1.0) -> list[datetime | None]:
    return [NOW - timedelta(days=start_days_ago - i * step) for i in range(count)]


def test_windows_need_minimum_sample() -> None:
    assert not build_time_windows(_dates(5, 30)).usable


def test_windows_need_time_span() -> None:
    """Si toda la muestra cabe en un día no hay dos periodos que comparar."""
    same_day = [NOW - timedelta(hours=i % 12) for i in range(40)]
    assert not build_time_windows(same_day).usable


def test_windows_are_usable_with_enough_spread() -> None:
    assert build_time_windows(_dates(40, 60, step=1.5)).usable


def test_trend_unknown_without_history() -> None:
    result = compute_trend(_dates(3, 5), build_time_windows(_dates(5, 10)))
    assert result.direction == TrendDirection.UNKNOWN
    assert result.note_es


def test_trend_detects_rising_share() -> None:
    all_dates = _dates(60, 90, step=1.5)
    windows = build_time_windows(all_dates)
    # El tema aparece sobre todo en la mitad reciente.
    topic_dates = all_dates[45:] + all_dates[:3]
    result = compute_trend(topic_dates, windows)
    assert result.direction == TrendDirection.RISING


def test_trend_detects_falling_share() -> None:
    all_dates = _dates(60, 90, step=1.5)
    windows = build_time_windows(all_dates)
    topic_dates = all_dates[:20] + all_dates[-2:]
    result = compute_trend(topic_dates, windows)
    assert result.direction == TrendDirection.FALLING


def test_windows_split_into_comparable_halves() -> None:
    """Las ventanas se parten por la mediana, no por un número fijo de días.

    Así los dos periodos tienen un volumen comparable aunque el canal publique
    a ritmo irregular, que es la base de la normalización de tendencias.
    """
    irregular = [NOW - timedelta(days=90 - i) for i in range(20)]
    irregular += [NOW - timedelta(days=20 - i * 0.5) for i in range(40)]
    windows = build_time_windows(irregular)
    assert abs(windows.recent_total - windows.previous_total) <= 1


def test_trend_is_normalised_against_total_volume() -> None:
    """Si el volumen total crece pero la cuota del tema se mantiene, es estable.

    Sin normalizar por el total de cada periodo, cualquier tema parecería
    crecer simplemente porque el canal recibe más comentarios.
    """
    all_dates = _dates(60, 90, step=1.5)
    windows = build_time_windows(all_dates)
    split = windows.split_point
    assert split is not None

    previous = [d for d in all_dates if d is not None and d < split]
    recent = [d for d in all_dates if d is not None and d >= split]
    # El tema representa el 25% de cada periodo, aunque el número absoluto de
    # menciones recientes sea mayor.
    topic = previous[: len(previous) // 4] + recent[: len(recent) // 4]

    result = compute_trend(topic, windows)
    assert result.direction == TrendDirection.STABLE
    assert result.recent_share == pytest.approx(result.previous_share, abs=0.03)


def test_trend_new_topic_has_capped_confidence() -> None:
    all_dates = _dates(60, 90, step=1.5)
    windows = build_time_windows(all_dates)
    result = compute_trend(all_dates[50:], windows)
    assert result.direction == TrendDirection.RISING
    assert result.confidence <= 0.6


def test_mentions_per_1000_handles_zero_total() -> None:
    assert mentions_per_1000(5, 0) == 0.0
    assert mentions_per_1000(5, 500) == 10.0


def test_coverage_bounds() -> None:
    assert coverage(4, 8) == 0.5
    assert coverage(0, 0) == 0.0
    assert coverage(10, 5) == 1.0


def test_dominant_source_share() -> None:
    assert dominant_source_share({"a": 8, "b": 2}) == 0.8
    assert dominant_source_share({}) == 0.0


def test_date_coverage_summary_counts_missing() -> None:
    summary = date_coverage_summary([NOW, None, NOW - timedelta(days=10)])
    assert summary["missing_dates"] == 1
    assert summary["span_days"] == 10.0


# --- Clustering -------------------------------------------------------------


def test_clustering_falls_back_on_tiny_samples() -> None:
    vectors = np.random.default_rng(0).random((4, 16)).astype(np.float32)
    assignment = cluster_embeddings(vectors)
    assert assignment.strategy == "keyword"
    assert assignment.n_clusters == 0
    assert assignment.noise_count == 4


def test_clustering_on_empty_input() -> None:
    assignment = cluster_embeddings(np.zeros((0, 8), dtype=np.float32))
    assert assignment.labels == []
    assert assignment.strategy == "none"


def test_clustering_separates_distinct_groups() -> None:
    backend = HashingEmbeddingBackend(dimension=256)
    audio = ["no se escucha el audio, sube el micrófono"] * 15
    humor = ["me río muchísimo con tu humor, eres muy gracioso"] * 15
    vectors = backend.encode(audio + humor)
    assignment = cluster_embeddings(vectors, min_cluster_size=3, min_comments=10)
    assert assignment.n_clusters >= 1
    assert len(assignment.labels) == 30


def test_clustering_labels_are_renumbered_from_zero() -> None:
    backend = HashingEmbeddingBackend(dimension=128)
    texts = [f"comentario sobre el audio número {i}" for i in range(20)]
    texts += [f"me encanta tu humor y tus chistes {i}" for i in range(20)]
    assignment = cluster_embeddings(backend.encode(texts), min_cluster_size=3, min_comments=10)
    positive = {label for label in assignment.labels if label >= 0}
    assert positive == set(range(len(positive)))


def test_embeddings_are_deterministic() -> None:
    backend = HashingEmbeddingBackend(dimension=64)
    first = backend.encode(["hola mundo", "otro texto"])
    second = backend.encode(["hola mundo", "otro texto"])
    assert np.allclose(first, second)


def test_embeddings_on_empty_list() -> None:
    assert HashingEmbeddingBackend(dimension=32).encode([]).shape == (0, 32)


def test_resize_vector_pads_and_truncates() -> None:
    assert len(resize_vector(np.array([1.0, 2.0]), 5)) == 5
    assert len(resize_vector(np.array([1.0] * 10), 3)) == 3


# --- Calidad de datos -------------------------------------------------------


def test_quality_warns_about_small_sample() -> None:
    quality = finalise_quality(
        DataQuality(videos_sampled=2, comments_sampled=10, comments_analysed=10)
    )
    assert quality.level == "baja"
    assert any("comentarios" in w for w in quality.warnings_es)
    assert any("vídeos" in w for w in quality.warnings_es)


def test_quality_flags_dominant_video_bias() -> None:
    quality = finalise_quality(
        DataQuality(
            videos_sampled=10,
            comments_sampled=400,
            comments_analysed=400,
            dominant_video_share=0.8,
        )
    )
    assert any("solo vídeo" in b for b in quality.biases_es)


def test_quality_flags_demo_data() -> None:
    quality = finalise_quality(DataQuality(is_demo=True))
    assert any("demostración" in b for b in quality.biases_es)


def test_quality_flags_sampling_strategy_bias() -> None:
    assert any(
        "más votados" in b
        for b in finalise_quality(DataQuality(sampling_strategy="relevant")).biases_es
    )


def test_quality_high_score_with_good_sample() -> None:
    quality = finalise_quality(
        DataQuality(
            videos_sampled=15,
            comments_sampled=600,
            comments_analysed=580,
            dominant_video_share=0.15,
            clustering_strategy="hdbscan",
            topics_found=8,
        )
    )
    assert quality.level == "alta"
    assert quality.score >= 0.7


def test_quality_score_is_bounded() -> None:
    quality = finalise_quality(
        DataQuality(videos_sampled=999, comments_sampled=99_999, comments_analysed=99_999)
    )
    assert 0.0 <= quality.score <= 1.0


def test_language_distribution() -> None:
    assert language_distribution(["es", "es", "en", ""]) == {"es": 2, "en": 1, "und": 1}
