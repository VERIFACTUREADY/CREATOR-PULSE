"""Pruebas de ingesta, idempotencia y análisis completo."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from app.core.config import ALGORITHM_VERSION, settings
from app.core.errors import ChannelNotFoundError, YouTubeQuotaExceededError
from app.models.enums import AnalysisStatus, DataSource, SamplingStrategy
from app.repositories.analysis import AnalysisRunRepository, ResultsRepository
from app.repositories.channels import ChannelRepository, CommentRepository, VideoRepository
from app.services.analysis.orchestrator import AnalysisOrchestrator
from app.services.demo import DemoLoader, list_demo_channels
from app.services.youtube.client import UsageLedger, YouTubeClient
from app.services.youtube.ingest import YouTubeIngestService
from sqlalchemy.orm import Session

from tests.integration.conftest import (
    CHANNEL_ID,
    UPLOADS_ID,
    channel_payload,
    comment_threads_payload,
    error_payload,
    playlist_payload,
    videos_payload,
)

BASE = "https://www.googleapis.com/youtube/v3"
pytestmark = pytest.mark.integration


def _client() -> YouTubeClient:
    return YouTubeClient(
        api_key="clave-de-prueba", sleep=lambda _s: None, ledger=UsageLedger(), max_retries=1
    )


def _mock_full_channel(*, video_count: int = 3, comments_disabled_index: int | None = None) -> None:
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json=channel_payload()))
    respx.get(f"{BASE}/playlistItems").mock(
        return_value=httpx.Response(200, json=playlist_payload(video_count))
    )
    respx.get(f"{BASE}/videos").mock(
        return_value=httpx.Response(
            200,
            json=videos_payload(video_count, comments_disabled_index=comments_disabled_index),
        )
    )
    respx.get(f"{BASE}/commentThreads").mock(
        side_effect=lambda request: httpx.Response(
            200,
            json=comment_threads_payload(request.url.params.get("videoId", "v"), 5),
        )
    )


def _ingest(session: Session, **kwargs: Any) -> Any:
    service = YouTubeIngestService(session, client=_client())
    channel = service.resolve_and_store_channel(f"https://www.youtube.com/channel/{CHANNEL_ID}")
    result = service.ingest_channel(
        channel,
        max_videos=kwargs.get("max_videos", 10),
        max_comments_per_video=kwargs.get("max_comments_per_video", 20),
        max_comments_per_channel=kwargs.get("max_comments_per_channel", 200),
        include_replies=False,
        sampling_strategy=kwargs.get("strategy", SamplingStrategy.MIXED),
    )
    session.commit()
    return result


# --- Resolución e importación ----------------------------------------------


@respx.mock
def test_import_public_channel(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_full_channel()

    result = _ingest(session)

    assert result.channel.youtube_channel_id == CHANNEL_ID
    assert result.channel.uploads_playlist_id == UPLOADS_ID
    assert len(result.videos) == 3
    assert result.comments_fetched > 0
    assert ChannelRepository(session).get_by_youtube_id(CHANNEL_ID) is not None


@respx.mock
def test_handle_resolution(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    route = respx.get(f"{BASE}/channels").mock(
        return_value=httpx.Response(200, json=channel_payload())
    )
    service = YouTubeIngestService(session, client=_client())
    channel = service.resolve_and_store_channel("@canalprueba")
    session.commit()

    assert channel.handle == "canalprueba"
    assert route.calls.last.request.url.params["forHandle"] == "@canalprueba"


@respx.mock
def test_channel_not_found_raises_spanish_error(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json={"items": []}))

    with pytest.raises(ChannelNotFoundError) as excinfo:
        YouTubeIngestService(session, client=_client()).resolve_and_store_channel("@inexistente")
    assert "no se ha encontrado" in excinfo.value.message.lower()


@respx.mock
def test_quota_exceeded_propagates(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    respx.get(f"{BASE}/channels").mock(
        return_value=httpx.Response(403, json=error_payload("quotaExceeded"))
    )
    with pytest.raises(YouTubeQuotaExceededError):
        YouTubeIngestService(session, client=_client()).resolve_and_store_channel("@canalprueba")


@respx.mock
def test_comments_disabled_video_does_not_break_ingest(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_full_channel(video_count=3, comments_disabled_index=1)

    result = _ingest(session)

    assert result.videos_with_comments_disabled == 1
    assert len(result.videos) == 3
    assert result.comments_fetched > 0


@respx.mock
def test_empty_channel_completes_without_error(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json=channel_payload()))
    respx.get(f"{BASE}/playlistItems").mock(return_value=httpx.Response(200, json={"items": []}))

    result = _ingest(session)
    assert result.videos == []
    assert result.comments_fetched == 0


@respx.mock
def test_partial_api_failure_on_comments_is_survivable(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si un vídeo falla por comentarios cerrados, el resto se importa igual."""
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json=channel_payload()))
    respx.get(f"{BASE}/playlistItems").mock(
        return_value=httpx.Response(200, json=playlist_payload(3))
    )
    respx.get(f"{BASE}/videos").mock(return_value=httpx.Response(200, json=videos_payload(3)))

    calls = {"n": 0}

    def _comments(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(403, json=error_payload("commentsDisabled"))
        return httpx.Response(
            200, json=comment_threads_payload(request.url.params.get("videoId", "v"), 5)
        )

    respx.get(f"{BASE}/commentThreads").mock(side_effect=_comments)

    result = _ingest(session)
    assert result.comments_fetched > 0


# --- Idempotencia -----------------------------------------------------------


@respx.mock
def test_refresh_does_not_duplicate_records(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_full_channel()

    first = _ingest(session)
    videos_after_first = VideoRepository(session).count_for_channel(first.channel.id)
    comments_after_first = CommentRepository(session).count_for_videos([v.id for v in first.videos])

    second = _ingest(session)
    videos_after_second = VideoRepository(session).count_for_channel(second.channel.id)
    comments_after_second = CommentRepository(session).count_for_videos(
        [v.id for v in second.videos]
    )

    assert videos_after_first == videos_after_second == 3
    assert comments_after_first == comments_after_second
    assert first.channel.id == second.channel.id


@respx.mock
def test_channel_cache_avoids_refetch_within_freshness_window(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    route = respx.get(f"{BASE}/channels").mock(
        return_value=httpx.Response(200, json=channel_payload())
    )
    reference = f"https://www.youtube.com/channel/{CHANNEL_ID}"

    service = YouTubeIngestService(session, client=_client())
    service.resolve_and_store_channel(reference)
    session.commit()
    assert route.call_count == 1

    service2 = YouTubeIngestService(session, client=_client())
    service2.resolve_and_store_channel(reference)
    session.commit()
    # La segunda resolución se sirve desde la base de datos.
    assert route.call_count == 1
    assert service2.ledger.records[0].cache_status == "hit"
    assert service2.ledger.records[0].estimated_quota_units == 0


@respx.mock
def test_forced_refresh_bypasses_cache(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    route = respx.get(f"{BASE}/channels").mock(
        return_value=httpx.Response(200, json=channel_payload())
    )
    reference = f"https://www.youtube.com/channel/{CHANNEL_ID}"

    service = YouTubeIngestService(session, client=_client())
    service.resolve_and_store_channel(reference)
    service.resolve_and_store_channel(reference, force=True)
    session.commit()
    assert route.call_count == 2


@respx.mock
def test_comment_deduplication_across_sampling_strategies(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La estrategia mixta pide dos veces; los solapes no se duplican."""
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json=channel_payload()))
    respx.get(f"{BASE}/playlistItems").mock(
        return_value=httpx.Response(200, json=playlist_payload(1))
    )
    respx.get(f"{BASE}/videos").mock(return_value=httpx.Response(200, json=videos_payload(1)))
    # Las dos pasadas devuelven exactamente los mismos comentarios.
    respx.get(f"{BASE}/commentThreads").mock(
        return_value=httpx.Response(200, json=comment_threads_payload("vid00000000", 5))
    )

    result = _ingest(session, strategy=SamplingStrategy.MIXED)
    stored = CommentRepository(session).count_for_videos([v.id for v in result.videos])
    assert stored == 5


# --- Análisis completo ------------------------------------------------------


@respx.mock
def test_full_analysis_run_completes(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_full_channel(video_count=3)

    service = YouTubeIngestService(session, client=_client())
    channel = service.resolve_and_store_channel(f"https://www.youtube.com/channel/{CHANNEL_ID}")
    session.commit()

    runs = AnalysisRunRepository(session)
    run = runs.create(
        channel_id=channel.id,
        status=AnalysisStatus.QUEUED,
        progress=0,
        max_videos=10,
        max_comments_per_video=20,
        max_comments_per_channel=200,
        include_replies=False,
        sampling_strategy=SamplingStrategy.MIXED,
        algorithm_version=ALGORITHM_VERSION,
        source=DataSource.YOUTUBE_API,
    )
    session.commit()

    result = AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)

    assert result.status == AnalysisStatus.COMPLETED, result.error_detail
    assert result.progress == 100
    assert result.videos_fetched == 3
    assert result.comments_analysed > 0
    assert result.data_quality is not None
    assert result.summary is not None
    assert result.completed_at is not None


def test_analysis_of_missing_run_raises(session: Session) -> None:
    import uuid

    from app.core.errors import AppError

    with pytest.raises(AppError):
        AnalysisOrchestrator(session).execute(uuid.uuid4())


# --- Modo demostración ------------------------------------------------------


def test_demo_channels_are_available() -> None:
    channels = list_demo_channels()
    assert len(channels) >= 3
    handles = {c.handle for c in channels}
    assert "luciaglowdemo" in handles


def test_demo_load_is_idempotent(session: Session) -> None:
    loader = DemoLoader(session)
    first = loader.load("luciaglowdemo")
    session.commit()
    videos_first = VideoRepository(session).count_for_channel(first.id)

    second = loader.load("luciaglowdemo")
    session.commit()
    videos_second = VideoRepository(session).count_for_channel(second.id)

    assert first.id == second.id
    assert videos_first == videos_second


def test_demo_data_is_labelled_as_demo(session: Session) -> None:
    channel = DemoLoader(session).load("luciaglowdemo")
    session.commit()
    assert channel.source == DataSource.DEMO
    assert channel.is_demo


def test_demo_analysis_produces_full_dashboard(session: Session) -> None:
    """El pipeline determinista analiza las fixtures, no las precalcula."""
    channel = DemoLoader(session).load("luciaglowdemo")
    run = AnalysisRunRepository(session).create(
        channel_id=channel.id,
        status=AnalysisStatus.QUEUED,
        progress=0,
        max_videos=20,
        max_comments_per_video=250,
        max_comments_per_channel=3000,
        include_replies=False,
        sampling_strategy=SamplingStrategy.MIXED,
        algorithm_version=ALGORITHM_VERSION,
        source=DataSource.DEMO,
    )
    session.commit()

    result = AnalysisOrchestrator(session).execute(run.id)
    assert result.status == AnalysisStatus.COMPLETED, result.error_detail

    results = ResultsRepository(session)
    topics = results.topics(run.id)
    recommendations = results.recommendations(run.id)
    ideas = results.content_ideas(run.id)

    assert topics, "el análisis debe detectar temas"
    assert recommendations, "el análisis debe generar recomendaciones"
    assert ideas, "el análisis debe generar ideas de contenido"
    assert result.data_quality["is_demo"] is True

    # Toda recomendación lleva evidencia y nivel de confianza.
    for rec in recommendations:
        assert rec.confidence_level in {"baja", "media", "alta"}
        assert rec.evidence
        assert rec.caveat_es

    # Toda idea declara su riesgo de sobreinterpretación.
    for idea in ideas:
        assert idea.overinterpretation_risk_es


def test_demo_analysis_detects_expected_signals(session: Session) -> None:
    """Las fixtures contienen elogios, críticas y peticiones detectables."""
    channel = DemoLoader(session).load("luciaglowdemo")
    run = AnalysisRunRepository(session).create(
        channel_id=channel.id,
        status=AnalysisStatus.QUEUED,
        progress=0,
        max_videos=20,
        max_comments_per_video=250,
        max_comments_per_channel=3000,
        include_replies=False,
        sampling_strategy=SamplingStrategy.MIXED,
        algorithm_version=ALGORITHM_VERSION,
        source=DataSource.DEMO,
    )
    session.commit()

    result = AnalysisOrchestrator(session).execute(run.id)
    summary = result.summary or {}

    assert summary["comments_analysed"] > 100
    assert summary["requests"] > 0
    assert summary["questions"] > 0
    assert summary["sentiment"]["positive"] > 0
    assert summary["sentiment"]["negative"] > 0
    assert summary["top_strength"] is not None
    assert summary["top_request"] is not None
    # Las fixtures incluyen un vídeo con comentarios desactivados.
    assert result.data_quality["videos_with_comments_disabled"] >= 1
    # Y un vídeo viral que concentra visualizaciones.
    assert result.data_quality["viral_view_concentration"] > 0.3


def test_reanalysis_replaces_previous_results(session: Session) -> None:
    channel = DemoLoader(session).load("codigoclarodemo")
    runs = AnalysisRunRepository(session)

    def _new_run() -> Any:
        run = runs.create(
            channel_id=channel.id,
            status=AnalysisStatus.QUEUED,
            progress=0,
            max_videos=20,
            max_comments_per_video=250,
            max_comments_per_channel=3000,
            include_replies=False,
            sampling_strategy=SamplingStrategy.MIXED,
            algorithm_version=ALGORITHM_VERSION,
            source=DataSource.DEMO,
        )
        session.commit()
        return run

    first = _new_run()
    AnalysisOrchestrator(session).execute(first.id)
    topics_first = len(ResultsRepository(session).topics(first.id))

    # Reejecutar sobre la misma ejecución no acumula resultados.
    AnalysisOrchestrator(session).execute(first.id)
    topics_again = len(ResultsRepository(session).topics(first.id))
    assert topics_first == topics_again
