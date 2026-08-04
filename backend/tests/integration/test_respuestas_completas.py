"""Descarga completa de respuestas cuando se pide «incluir respuestas».

`commentThreads.list` sólo trae unas pocas respuestas por hilo. Si la interfaz
ofrece incluirlas, la aplicación debe pedir el resto con `comments.list`; y
cuando no pueda garantizarlo, decirlo en lugar de aparentar que la conversación
está entera.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from app.core.config import settings
from app.services.youtube.client import UsageLedger, YouTubeClient
from app.services.youtube.ingest import YouTubeIngestService
from sqlalchemy.orm import Session

from tests.integration.conftest import CHANNEL_ID, channel_payload, playlist_payload, videos_payload

BASE = "https://www.googleapis.com/youtube/v3"
pytestmark = pytest.mark.integration


def _client(ledger: UsageLedger | None = None) -> YouTubeClient:
    return YouTubeClient(
        api_key="clave-de-prueba",
        sleep=lambda _s: None,
        ledger=ledger or UsageLedger(),
        max_retries=1,
    )


def _thread(
    thread_id: str, *, total_replies: int, embedded: int, video_id: str = "vid0"
) -> dict[str, Any]:
    """Un hilo con `total_replies` declaradas y `embedded` incluidas."""
    return {
        "id": thread_id,
        "snippet": {
            "totalReplyCount": total_replies,
            "topLevelComment": {
                "id": thread_id,
                "snippet": {
                    "textOriginal": "El vídeo está muy bien explicado",
                    "publishedAt": "2024-05-01T10:00:00Z",
                    "likeCount": 3,
                    "authorChannelId": {"value": "UCautor1"},
                },
            },
        },
        "replies": {
            "comments": [
                {
                    "id": f"{thread_id}-r{i}",
                    "snippet": {
                        "textOriginal": f"Respuesta embebida {i}",
                        "publishedAt": "2024-05-01T11:00:00Z",
                        "likeCount": 0,
                        "authorChannelId": {"value": f"UCautor{i}"},
                    },
                }
                for i in range(embedded)
            ]
        }
        if embedded
        else {},
    }


def _reply_items(thread_id: str, indices: list[int]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"{thread_id}-r{i}",
            "snippet": {
                "textOriginal": f"Respuesta paginada {i}",
                "publishedAt": "2024-05-01T12:00:00Z",
                "likeCount": 1,
                "authorChannelId": {"value": f"UCautor{i}"},
            },
        }
        for i in indices
    ]


def _mock_base(threads: list[dict[str, Any]]) -> None:
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json=channel_payload()))
    respx.get(f"{BASE}/playlistItems").mock(
        return_value=httpx.Response(200, json=playlist_payload(1))
    )
    respx.get(f"{BASE}/videos").mock(return_value=httpx.Response(200, json=videos_payload(1)))
    respx.get(f"{BASE}/commentThreads").mock(
        return_value=httpx.Response(200, json={"items": threads})
    )


def _ingest(
    session: Session, *, ledger: UsageLedger | None = None, max_comments_per_video: int = 100
) -> Any:
    service = YouTubeIngestService(session, client=_client(ledger))
    channel = service.resolve_and_store_channel(f"https://www.youtube.com/channel/{CHANNEL_ID}")
    result = service.ingest_channel(
        channel,
        max_videos=1,
        max_comments_per_video=max_comments_per_video,
        max_comments_per_channel=max_comments_per_video,
        include_replies=True,
    )
    session.commit()
    return result


def _texts(session: Session, result: Any) -> list[str]:
    from app.repositories.channels import CommentRepository

    ids = [cid for cid, _ in result.selected_comments]
    comentarios = CommentRepository(session).list_for_videos([v.id for v in result.videos])
    return [c.text for c in comentarios if c.id in set(ids)]


# --- Casos ------------------------------------------------------------------


@respx.mock
def test_hilo_sin_respuestas_no_pide_comments_list(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_base([_thread("t1", total_replies=0, embedded=0)])
    ruta = respx.get(f"{BASE}/comments").mock(return_value=httpx.Response(200, json={"items": []}))

    resultado = _ingest(session)

    assert not ruta.called, "no hay respuestas que pedir"
    assert resultado.replies_fetched == 0
    assert resultado.replies_incomplete is False


@respx.mock
def test_hilo_con_todas_las_respuestas_embebidas_no_pagina(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_base([_thread("t1", total_replies=2, embedded=2)])
    ruta = respx.get(f"{BASE}/comments").mock(return_value=httpx.Response(200, json={"items": []}))

    resultado = _ingest(session)

    assert not ruta.called
    assert resultado.replies_incomplete is False
    # El principal más sus dos respuestas.
    assert resultado.comments_fetched == 3


@respx.mock
def test_hilo_con_mas_respuestas_que_las_embebidas_se_pagina(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El caso que la auditoría señalaba como roto."""
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_base([_thread("t1", total_replies=7, embedded=2)])

    paginas = [
        httpx.Response(
            200, json={"items": _reply_items("t1", [2, 3, 4]), "nextPageToken": "siguiente"}
        ),
        httpx.Response(200, json={"items": _reply_items("t1", [5, 6])}),
    ]
    ruta = respx.get(f"{BASE}/comments").mock(side_effect=paginas)

    resultado = _ingest(session)

    assert ruta.call_count == 2, "debe recorrer las dos páginas"
    assert resultado.replies_fetched == 5
    assert resultado.replies_incomplete is False
    # 1 principal + 2 embebidas + 5 paginadas.
    assert resultado.comments_fetched == 8


@respx.mock
def test_una_respuesta_repetida_no_se_duplica(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`comments.list` puede devolver también las que ya venían embebidas."""
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_base([_thread("t1", total_replies=4, embedded=2)])
    # Devuelve r0 y r1 (ya embebidas) más r2 y r3.
    respx.get(f"{BASE}/comments").mock(
        return_value=httpx.Response(200, json={"items": _reply_items("t1", [0, 1, 2, 3])})
    )

    resultado = _ingest(session)

    ids = [cid for cid, _ in resultado.selected_comments]
    assert len(ids) == len(set(ids))
    # 1 principal + 4 respuestas distintas, sin repetir r0 ni r1.
    assert resultado.comments_fetched == 5


@respx.mock
def test_el_limite_corta_la_descarga_y_lo_declara(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_base([_thread("t1", total_replies=50, embedded=1)])
    respx.get(f"{BASE}/comments").mock(
        return_value=httpx.Response(200, json={"items": _reply_items("t1", list(range(1, 40)))})
    )

    resultado = _ingest(session, max_comments_per_video=5)

    assert resultado.comments_fetched <= 5
    # La conversación queda a medias y eso se dice, no se oculta.
    assert resultado.replies_incomplete is True


@respx.mock
def test_un_error_al_pedir_respuestas_no_pierde_lo_ya_obtenido(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_base([_thread("t1", total_replies=9, embedded=2)])
    respx.get(f"{BASE}/comments").mock(return_value=httpx.Response(500, json={"error": {}}))

    resultado = _ingest(session)

    # El principal y las dos embebidas siguen ahí.
    assert resultado.comments_fetched == 3
    assert resultado.replies_incomplete is True


@respx.mock
def test_la_cuota_de_comments_list_se_contabiliza(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_base([_thread("t1", total_replies=4, embedded=1)])
    respx.get(f"{BASE}/comments").mock(
        return_value=httpx.Response(200, json={"items": _reply_items("t1", [1, 2, 3])})
    )

    ledger = UsageLedger()
    _ingest(session, ledger=ledger)

    endpoints = [record.endpoint for record in ledger.records]
    assert "comments.list" in endpoints


@respx.mock
def test_las_respuestas_se_marcan_como_no_principales(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.repositories.channels import CommentRepository

    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_base([_thread("t1", total_replies=3, embedded=0)])
    respx.get(f"{BASE}/comments").mock(
        return_value=httpx.Response(200, json={"items": _reply_items("t1", [0, 1, 2])})
    )

    resultado = _ingest(session)

    comentarios = CommentRepository(session).list_for_videos([v.id for v in resultado.videos])
    principales = [c for c in comentarios if c.is_top_level]
    respuestas = [c for c in comentarios if not c.is_top_level]

    assert len(principales) == 1
    assert len(respuestas) == 3
    assert all(r.parent_comment_id == "t1" for r in respuestas)
