"""Una muestra cerrada no se amplía por reintentar la ejecución.

La prueba de idempotencia anterior repetía exactamente el mismo mock, así que
no distinguía «no duplica pares» de «no añade comentarios nuevos». En una API
viva los comentarios cambian entre intentos, y con `ON CONFLICT DO NOTHING` un
reintento ampliaba la muestra por la puerta de atrás.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from app.core.config import ALGORITHM_VERSION, settings
from app.models.entities import AnalysisRun, AnalysisRunComment
from app.models.enums import AnalysisStatus, DataSource, SamplingStrategy
from app.repositories.analysis import AnalysisRunRepository
from app.repositories.channels import CommentRepository
from app.services.analysis.orchestrator import AnalysisOrchestrator
from app.services.demo import DemoLoader
from app.services.youtube.client import UsageLedger, YouTubeClient
from app.services.youtube.ingest import YouTubeIngestService
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from tests.integration.conftest import CHANNEL_ID, channel_payload, playlist_payload, videos_payload

BASE = "https://www.googleapis.com/youtube/v3"
pytestmark = pytest.mark.integration


def _client() -> YouTubeClient:
    return YouTubeClient(
        api_key="clave-de-prueba", sleep=lambda _s: None, ledger=UsageLedger(), max_retries=1
    )


def _threads(ids: list[str], video_id: str = "vid0") -> dict[str, Any]:
    """Hilos con identificadores controlados, para poder cambiarlos entre intentos."""
    return {
        "items": [
            {
                "id": cid,
                "snippet": {
                    "totalReplyCount": 0,
                    "topLevelComment": {
                        "id": cid,
                        "snippet": {
                            "textOriginal": f"Comentario {cid} sobre el vídeo, muy interesante",
                            "publishedAt": "2024-05-01T10:00:00Z",
                            "likeCount": 3,
                            "authorChannelId": {"value": f"UCautor{cid}"},
                        },
                    },
                },
            }
            for cid in ids
        ]
    }


def _mock(ids: list[str]) -> None:
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json=channel_payload()))
    respx.get(f"{BASE}/playlistItems").mock(
        return_value=httpx.Response(200, json=playlist_payload(1))
    )
    respx.get(f"{BASE}/videos").mock(return_value=httpx.Response(200, json=videos_payload(1)))
    respx.get(f"{BASE}/commentThreads").mock(return_value=httpx.Response(200, json=_threads(ids)))


def _run(session: Session, channel_id: Any, *, max_comments: int = 100) -> AnalysisRun:
    run = AnalysisRunRepository(session).create(
        channel_id=channel_id,
        status=AnalysisStatus.QUEUED,
        progress=0,
        max_videos=5,
        max_comments_per_video=max_comments,
        max_comments_per_channel=max_comments,
        include_replies=False,
        sampling_strategy=SamplingStrategy.RECENT,
        algorithm_version=ALGORITHM_VERSION,
        source=DataSource.YOUTUBE_API,
    )
    session.commit()
    return run


def _resolve(session: Session) -> Any:
    service = YouTubeIngestService(session, client=_client())
    channel = service.resolve_and_store_channel(f"https://www.youtube.com/channel/{CHANNEL_ID}")
    session.commit()
    return channel


def _sample_texts(session: Session, run_id: Any) -> list[str]:
    return [c.youtube_comment_id for c in CommentRepository(session).list_for_run(run_id)]


def _orders(session: Session, run_id: Any) -> list[int]:
    return sorted(
        session.execute(
            select(AnalysisRunComment.selection_order).where(AnalysisRunComment.run_id == run_id)
        ).scalars()
    )


# --- El caso que la revisión señalaba --------------------------------------


@respx.mock
def test_el_reintento_con_datos_distintos_no_cambia_la_muestra(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Primer intento A/B/C; el reintento ve A/B/D y la muestra sigue siendo A/B/C."""
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock(["A", "B", "C"])
    channel = _resolve(session)
    run = _run(session, channel.id)

    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()
    primera = _sample_texts(session, run.id)
    assert set(primera) == {"A", "B", "C"}

    # YouTube devuelve ahora otra selección: D en lugar de C.
    respx.get(f"{BASE}/commentThreads").mock(
        return_value=httpx.Response(200, json=_threads(["A", "B", "D"]))
    )
    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()

    assert _sample_texts(session, run.id) == primera
    assert "D" not in _sample_texts(session, run.id)


@respx.mock
def test_el_reintento_no_crea_ordenes_duplicados(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock(["A", "B", "C"])
    channel = _resolve(session)
    run = _run(session, channel.id)

    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()

    respx.get(f"{BASE}/commentThreads").mock(
        return_value=httpx.Response(200, json=_threads(["A", "B", "D", "E"]))
    )
    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()

    ordenes = _orders(session, run.id)
    assert ordenes == list(range(len(ordenes))), "el orden debe ser único y sin huecos"


@respx.mock
def test_un_fallo_antes_de_registrar_permite_crear_la_muestra_despues(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si el primer intento no llegó a cerrar la muestra, el reintento sí puede."""
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock(["A", "B", "C"])
    channel = _resolve(session)
    run = _run(session, channel.id)

    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()

    # Se simula un intento que murió a mitad de registrar: quedan filas
    # parciales y la muestra nunca se cerró.
    session.execute(
        delete(AnalysisRunComment).where(
            AnalysisRunComment.run_id == run.id,
            AnalysisRunComment.selection_order > 0,
        )
    )
    run.sample_finalized_at = None
    session.commit()
    assert len(_sample_texts(session, run.id)) == 1

    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()

    muestra = _sample_texts(session, run.id)
    assert set(muestra) == {"A", "B", "C"}, "la muestra se rehace entera"
    assert _orders(session, run.id) == [0, 1, 2], "sin huecos ni posiciones repetidas"
    recargado = session.get(AnalysisRun, run.id)
    assert recargado is not None and recargado.sample_finalized_at is not None


@respx.mock
def test_un_reintento_posterior_al_registro_no_vuelve_a_pedir_comentarios(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No gastar cuota de más es parte del requisito."""
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock(["A", "B", "C"])
    channel = _resolve(session)
    run = _run(session, channel.id)

    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()

    ruta = respx.get(f"{BASE}/commentThreads")
    llamadas_antes = ruta.call_count

    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()

    assert ruta.call_count == llamadas_antes, "no debe volver a descargar comentarios"


@respx.mock
def test_la_muestra_nunca_supera_el_limite_del_canal(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock([f"C{i}" for i in range(30)])
    channel = _resolve(session)
    run = _run(session, channel.id, max_comments=7)

    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()

    total = int(
        session.execute(
            select(func.count())
            .select_from(AnalysisRunComment)
            .where(AnalysisRunComment.run_id == run.id)
        ).scalar_one()
    )
    assert total <= 7


def test_la_comprobacion_defensiva_recorta_una_seleccion_excesiva(session: Session) -> None:
    """Aunque aguas arriba fallara todo, la muestra respeta el límite."""
    canal = DemoLoader(session).load("luciaglowdemo")
    session.commit()
    run = _run(session, canal.id, max_comments=5)

    comentarios = CommentRepository(session).list_for_videos(
        [v.id for v in AnalysisOrchestrator(session).videos.list_recent_for_channel(canal.id, 5)]
    )
    assert len(comentarios) > 5

    registro = CommentRepository(session).register_run_sample(
        run.id, [(c.id, "demo") for c in comentarios], max_comments=5
    )
    session.commit()

    assert registro.size == 5
    assert registro.inserted == 5


def test_el_modo_demo_conserva_la_muestra_en_reintentos(session: Session) -> None:
    canal = DemoLoader(session).load("luciaglowdemo")
    session.commit()
    run = _run(session, canal.id, max_comments=25)

    AnalysisOrchestrator(session).execute(run.id)
    session.commit()
    primera = _sample_texts(session, run.id)
    assert primera

    AnalysisOrchestrator(session).execute(run.id)
    session.commit()

    assert _sample_texts(session, run.id) == primera


def test_registrar_una_muestra_ya_cerrada_lo_declara(session: Session) -> None:
    canal = DemoLoader(session).load("luciaglowdemo")
    session.commit()
    run = _run(session, canal.id, max_comments=10)
    comentarios = CommentRepository(session).list_for_videos(
        [v.id for v in AnalysisOrchestrator(session).videos.list_recent_for_channel(canal.id, 5)]
    )[:4]

    primero = CommentRepository(session).register_run_sample(
        run.id, [(c.id, "demo") for c in comentarios]
    )
    session.commit()
    assert primero.reused is False
    assert primero.inserted == 4

    # Un segundo registro con otra selección no toca nada.
    otros = CommentRepository(session).list_for_videos(
        [v.id for v in AnalysisOrchestrator(session).videos.list_recent_for_channel(canal.id, 5)]
    )[10:14]
    segundo = CommentRepository(session).register_run_sample(
        run.id, [(c.id, "demo") for c in otros]
    )
    session.commit()

    assert segundo.reused is True
    assert segundo.inserted == 0
    assert segundo.size == 4
