"""Pruebas del cliente de YouTube con la API mockeada."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from app.core.errors import (
    YouTubeError,
    YouTubeInvalidKeyError,
    YouTubeNotConfiguredError,
    YouTubeQuotaExceededError,
)
from app.services.youtube.client import UsageLedger, YouTubeClient
from app.services.youtube.mappers import (
    map_channel,
    map_comment_thread,
    map_video,
    parse_duration,
    parse_iso_datetime,
)
from app.services.youtube.quota import estimate_analysis_cost, estimate_cost

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


def _client(**kwargs: Any) -> YouTubeClient:
    """Cliente con `sleep` neutralizado para que los reintentos no esperen."""
    kwargs.setdefault("api_key", "clave-de-prueba")
    kwargs.setdefault("sleep", lambda _seconds: None)
    return YouTubeClient(**kwargs)


# --- Configuración ----------------------------------------------------------


def test_missing_api_key_raises_domain_error() -> None:
    with pytest.raises(YouTubeNotConfiguredError) as excinfo:
        _client(api_key="").get_channel_by_id(CHANNEL_ID)
    assert "YOUTUBE_API_KEY" in excinfo.value.message


# --- Resolución de canal ----------------------------------------------------


@respx.mock
def test_get_channel_by_id() -> None:
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json=channel_payload()))
    item = _client().get_channel_by_id(CHANNEL_ID)
    assert item is not None
    assert map_channel(item)["youtube_channel_id"] == CHANNEL_ID


@respx.mock
def test_get_channel_by_handle_sends_for_handle() -> None:
    route = respx.get(f"{BASE}/channels").mock(
        return_value=httpx.Response(200, json=channel_payload())
    )
    _client().get_channel_by_handle("canalprueba")
    assert route.calls.last.request.url.params["forHandle"] == "@canalprueba"


@respx.mock
def test_channel_not_found_returns_none() -> None:
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json={"items": []}))
    assert _client().get_channel_by_id(CHANNEL_ID) is None


@respx.mock
def test_api_key_never_leaks_into_the_ledger() -> None:
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json=channel_payload()))
    client = _client()
    client.get_channel_by_id(CHANNEL_ID)
    assert "clave-de-prueba" not in str(client.ledger.summary())


# --- Errores ----------------------------------------------------------------


@respx.mock
def test_quota_exceeded_is_translated() -> None:
    respx.get(f"{BASE}/channels").mock(
        return_value=httpx.Response(403, json=error_payload("quotaExceeded"))
    )
    with pytest.raises(YouTubeQuotaExceededError) as excinfo:
        _client().get_channel_by_id(CHANNEL_ID)
    assert "cuota" in excinfo.value.message.lower()


@respx.mock
def test_invalid_key_is_translated() -> None:
    respx.get(f"{BASE}/channels").mock(
        return_value=httpx.Response(403, json=error_payload("keyInvalid"))
    )
    with pytest.raises(YouTubeInvalidKeyError):
        _client().get_channel_by_id(CHANNEL_ID)


@respx.mock
def test_api_not_enabled_is_translated() -> None:
    respx.get(f"{BASE}/channels").mock(
        return_value=httpx.Response(403, json=error_payload("accessNotConfigured"))
    )
    with pytest.raises(YouTubeInvalidKeyError) as excinfo:
        _client().get_channel_by_id(CHANNEL_ID)
    assert "YouTube Data API" in excinfo.value.message


@respx.mock
def test_server_error_is_retried_then_succeeds() -> None:
    route = respx.get(f"{BASE}/channels").mock(
        side_effect=[
            httpx.Response(503, json=error_payload("backendError")),
            httpx.Response(500, json=error_payload("backendError")),
            httpx.Response(200, json=channel_payload()),
        ]
    )
    assert _client(max_retries=3).get_channel_by_id(CHANNEL_ID) is not None
    assert route.call_count == 3


@respx.mock
def test_server_error_gives_up_after_max_retries() -> None:
    respx.get(f"{BASE}/channels").mock(
        return_value=httpx.Response(503, json=error_payload("backendError"))
    )
    with pytest.raises(YouTubeError):
        _client(max_retries=2).get_channel_by_id(CHANNEL_ID)


@respx.mock
def test_timeout_is_retried_and_translated() -> None:
    respx.get(f"{BASE}/channels").mock(side_effect=httpx.ReadTimeout("agotado"))
    with pytest.raises(YouTubeError) as excinfo:
        _client(max_retries=1).get_channel_by_id(CHANNEL_ID)
    assert excinfo.value.code == "youtube_timeout"


@respx.mock
def test_failed_calls_are_recorded_in_ledger() -> None:
    respx.get(f"{BASE}/channels").mock(
        return_value=httpx.Response(403, json=error_payload("quotaExceeded"))
    )
    client = _client()
    with pytest.raises(YouTubeQuotaExceededError):
        client.get_channel_by_id(CHANNEL_ID)
    assert client.ledger.summary()["by_endpoint"]["channels.list"]["errors"] == 1


# --- Paginación y lotes -----------------------------------------------------


@respx.mock
def test_playlist_pagination_follows_next_token() -> None:
    respx.get(f"{BASE}/playlistItems").mock(
        side_effect=[
            httpx.Response(200, json=playlist_payload(2, next_token="page2")),
            httpx.Response(200, json=playlist_payload(2)),
        ]
    )
    items = list(_client().iter_playlist_items(UPLOADS_ID, max_items=4, page_size=2))
    assert len(items) == 4


@respx.mock
def test_playlist_pagination_respects_max_items() -> None:
    respx.get(f"{BASE}/playlistItems").mock(
        return_value=httpx.Response(200, json=playlist_payload(50, next_token="siempre"))
    )
    items = list(_client().iter_playlist_items(UPLOADS_ID, max_items=5))
    assert len(items) == 5


@respx.mock
def test_playlist_pagination_stops_on_repeated_token() -> None:
    """Un token repetido no debe provocar un bucle infinito."""
    respx.get(f"{BASE}/playlistItems").mock(
        return_value=httpx.Response(200, json=playlist_payload(2, next_token="mismo"))
    )
    items = list(_client().iter_playlist_items(UPLOADS_ID, max_items=100, page_size=2))
    assert len(items) == 4


@respx.mock
def test_playlist_stops_on_empty_page() -> None:
    respx.get(f"{BASE}/playlistItems").mock(return_value=httpx.Response(200, json={"items": []}))
    assert list(_client().iter_playlist_items(UPLOADS_ID, max_items=10)) == []


@respx.mock
def test_videos_are_fetched_in_batches_of_fifty() -> None:
    route = respx.get(f"{BASE}/videos").mock(
        return_value=httpx.Response(200, json=videos_payload(1))
    )
    ids = [f"video{i:06d}" for i in range(120)]
    _client().get_videos(ids)
    assert route.call_count == 3
    first_batch = route.calls[0].request.url.params["id"].split(",")
    assert len(first_batch) == 50


@respx.mock
def test_videos_deduplicates_ids() -> None:
    route = respx.get(f"{BASE}/videos").mock(
        return_value=httpx.Response(200, json=videos_payload(1))
    )
    _client().get_videos(["abc", "abc", "abc"])
    assert route.calls[0].request.url.params["id"] == "abc"


def test_videos_with_empty_list_makes_no_request() -> None:
    assert _client().get_videos([]) == []


# --- Comentarios ------------------------------------------------------------


@respx.mock
def test_comment_threads_paginate() -> None:
    respx.get(f"{BASE}/commentThreads").mock(
        side_effect=[
            httpx.Response(200, json=comment_threads_payload("v1", 3, next_token="p2")),
            httpx.Response(200, json=comment_threads_payload("v1", 3, start=3)),
        ]
    )
    threads = list(_client().iter_comment_threads("v1", max_comments=6, page_size=3))
    assert len(threads) == 6


@respx.mock
def test_comments_disabled_yields_nothing_without_raising() -> None:
    """Un vídeo con comentarios cerrados no debe romper el trabajo."""
    respx.get(f"{BASE}/commentThreads").mock(
        return_value=httpx.Response(403, json=error_payload("commentsDisabled"))
    )
    assert list(_client().iter_comment_threads("v1", max_comments=10)) == []


@respx.mock
def test_video_not_found_yields_nothing() -> None:
    respx.get(f"{BASE}/commentThreads").mock(
        return_value=httpx.Response(404, json=error_payload("videoNotFound"))
    )
    assert list(_client().iter_comment_threads("v1", max_comments=10)) == []


@respx.mock
def test_comment_quota_error_still_propagates() -> None:
    """La cuota agotada sí debe detener el trabajo: no es un caso ignorable."""
    respx.get(f"{BASE}/commentThreads").mock(
        return_value=httpx.Response(403, json=error_payload("quotaExceeded"))
    )
    with pytest.raises(YouTubeQuotaExceededError):
        list(_client().iter_comment_threads("v1", max_comments=10))


@respx.mock
def test_zero_comments_video() -> None:
    respx.get(f"{BASE}/commentThreads").mock(return_value=httpx.Response(200, json={"items": []}))
    assert list(_client().iter_comment_threads("v1", max_comments=10)) == []


# --- Mapeadores -------------------------------------------------------------


def test_map_channel_with_hidden_subscribers() -> None:
    payload = channel_payload()
    payload["items"][0]["statistics"] = {"hiddenSubscriberCount": True, "videoCount": "10"}
    mapped = map_channel(payload["items"][0])
    assert mapped["subscriber_count"] is None
    assert mapped["subscriber_count_hidden"] is True


def test_map_channel_without_thumbnails() -> None:
    payload = channel_payload()
    payload["items"][0]["snippet"]["thumbnails"] = {}
    assert map_channel(payload["items"][0])["thumbnail_url"] is None


def test_map_video_detects_disabled_comments() -> None:
    item = videos_payload(1, comments_disabled_index=0)["items"][0]
    mapped = map_video(item)
    assert mapped["comments_disabled"] is True
    assert mapped["comment_count"] is None


def test_map_video_never_exposes_dislikes() -> None:
    item = videos_payload(1)["items"][0]
    item["statistics"]["dislikeCount"] = "500"
    assert "dislike" not in " ".join(map_video(item).keys()).lower()


def test_map_video_clamps_negative_counters() -> None:
    item = videos_payload(1)["items"][0]
    item["statistics"]["viewCount"] = "-100"
    assert map_video(item)["view_count"] == 0


@pytest.mark.parametrize(
    ("iso", "seconds"),
    [("PT10M30S", 630), ("PT1H2M3S", 3723), ("P1DT2H", 93_600), ("PT45S", 45), ("basura", None)],
)
def test_parse_duration(iso: str, seconds: int | None) -> None:
    assert parse_duration(iso) == seconds


def test_parse_iso_datetime_handles_z_suffix_and_garbage() -> None:
    assert parse_iso_datetime("2024-05-01T10:00:00Z") is not None
    assert parse_iso_datetime("no es una fecha") is None
    assert parse_iso_datetime(None) is None


def test_map_comment_thread_hashes_author_identity() -> None:
    thread = comment_threads_payload("v1", 1)["items"][0]
    mapped = map_comment_thread(thread, include_replies=False)
    assert len(mapped) == 1
    # Nunca se guarda el identificador original del autor.
    assert mapped[0]["author_hash"].startswith("a_")
    assert "UCauthor" not in mapped[0]["author_hash"]


def test_map_comment_thread_with_replies() -> None:
    thread = comment_threads_payload("v1", 1)["items"][0]
    thread["replies"] = {
        "comments": [
            {
                "id": "reply-1",
                "snippet": {
                    "textOriginal": "Yo también lo pienso",
                    "publishedAt": "2024-05-02T10:00:00Z",
                    "likeCount": 1,
                },
            }
        ]
    }
    mapped = map_comment_thread(thread, include_replies=True)
    assert len(mapped) == 2
    assert mapped[1]["is_top_level"] is False
    assert mapped[1]["parent_comment_id"] == mapped[0]["youtube_comment_id"]


# --- Cuota ------------------------------------------------------------------


def test_quota_costs_match_published_values() -> None:
    assert estimate_cost("channels.list") == 1
    assert estimate_cost("search.list") == 100
    assert estimate_cost("commentThreads.list", 5) == 5


def test_estimate_analysis_cost_grows_with_limits() -> None:
    small = estimate_analysis_cost(5, 50)
    large = estimate_analysis_cost(50, 500)
    assert large > small
    assert estimate_analysis_cost(0, 0) >= 1


def test_estimate_analysis_cost_accounts_for_replies() -> None:
    assert estimate_analysis_cost(10, 100, include_replies=True) > estimate_analysis_cost(10, 100)


def test_ledger_summary_aggregates_by_endpoint() -> None:
    ledger = UsageLedger()
    ledger.record("channels.list")
    ledger.record("videos.list")
    ledger.record("videos.list", cache_status="hit")
    summary = ledger.summary()
    assert summary["total_requests"] == 3
    # Una llamada servida desde caché no consume cuota.
    assert summary["by_endpoint"]["videos.list"]["quota_units"] == 1
    assert summary["by_endpoint"]["videos.list"]["cached"] == 1
