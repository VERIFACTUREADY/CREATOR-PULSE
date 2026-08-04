"""La muestra de comentarios pertenece a la ejecución, no al vídeo.

Antes de esta tabla asociativa, una segunda ejecución leía todos los
comentarios almacenados para sus vídeos —incluidos los que había descargado la
primera—, así que los límites solicitados no significaban nada y el análisis no
era reproducible. Estas pruebas fijan ese contrato.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from app.core.config import ALGORITHM_VERSION, settings
from app.models.entities import AnalysisRunComment, Comment
from app.models.enums import AnalysisStatus, DataSource, SamplingStrategy
from app.repositories.analysis import AnalysisRunRepository
from app.repositories.channels import CommentRepository
from app.services.analysis.orchestrator import AnalysisOrchestrator
from app.services.demo import DemoLoader
from app.services.youtube.client import UsageLedger, YouTubeClient
from app.services.youtube.ingest import YouTubeIngestService
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.integration.conftest import (
    CHANNEL_ID,
    channel_payload,
    comment_threads_payload,
    playlist_payload,
    videos_payload,
)

BASE = "https://www.googleapis.com/youtube/v3"
pytestmark = pytest.mark.integration


def _client() -> YouTubeClient:
    return YouTubeClient(
        api_key="clave-de-prueba", sleep=lambda _s: None, ledger=UsageLedger(), max_retries=1
    )


def _mock_channel(*, video_count: int = 3, comments_per_video: int = 40) -> None:
    respx.get(f"{BASE}/channels").mock(return_value=httpx.Response(200, json=channel_payload()))
    respx.get(f"{BASE}/playlistItems").mock(
        return_value=httpx.Response(200, json=playlist_payload(video_count))
    )
    respx.get(f"{BASE}/videos").mock(
        return_value=httpx.Response(200, json=videos_payload(video_count))
    )
    respx.get(f"{BASE}/commentThreads").mock(
        side_effect=lambda request: httpx.Response(
            200,
            json=comment_threads_payload(
                request.url.params.get("videoId", "v"), comments_per_video
            ),
        )
    )


def _make_run(
    session: Session,
    channel_id: object,
    *,
    max_comments_per_channel: int,
    max_comments_per_video: int = 100,
    strategy: str = SamplingStrategy.MIXED,
    source: str = DataSource.YOUTUBE_API,
) -> object:
    run = AnalysisRunRepository(session).create(
        channel_id=channel_id,
        status=AnalysisStatus.QUEUED,
        progress=0,
        max_videos=10,
        max_comments_per_video=max_comments_per_video,
        max_comments_per_channel=max_comments_per_channel,
        include_replies=False,
        sampling_strategy=strategy,
        algorithm_version=ALGORITHM_VERSION,
        source=source,
    )
    session.commit()
    return run


def _sample_size(session: Session, run_id: object) -> int:
    return int(
        session.execute(
            select(func.count())
            .select_from(AnalysisRunComment)
            .where(AnalysisRunComment.run_id == run_id)
        ).scalar_one()
    )


def _resolve_channel(session: Session) -> object:
    service = YouTubeIngestService(session, client=_client())
    channel = service.resolve_and_store_channel(f"https://www.youtube.com/channel/{CHANNEL_ID}")
    session.commit()
    return channel


# --- Límites por ejecución --------------------------------------------------


@respx.mock
def test_segunda_ejecucion_con_limite_menor_no_hereda_comentarios(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El caso que motivó todo el bloque: 100 y luego 20 debe dar como mucho 20."""
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_channel(video_count=3, comments_per_video=60)
    channel = _resolve_channel(session)

    primera = _make_run(session, channel.id, max_comments_per_channel=100)
    AnalysisOrchestrator(session, youtube_client=_client()).execute(primera.id)
    session.commit()

    segunda = _make_run(session, channel.id, max_comments_per_channel=20)
    resultado = AnalysisOrchestrator(session, youtube_client=_client()).execute(segunda.id)
    session.commit()

    assert resultado.status == AnalysisStatus.COMPLETED, resultado.error_detail
    assert _sample_size(session, segunda.id) <= 20
    # `comments_fetched` describe esta ejecución, no el histórico acumulado.
    assert resultado.comments_fetched <= 20

    # La primera conserva la suya: son muestras independientes.
    assert _sample_size(session, primera.id) > 20


@respx.mock
def test_cambio_de_estrategia_mantiene_muestras_independientes(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_channel(video_count=2, comments_per_video=30)
    channel = _resolve_channel(session)

    reciente = _make_run(
        session, channel.id, max_comments_per_channel=30, strategy=SamplingStrategy.RECENT
    )
    AnalysisOrchestrator(session, youtube_client=_client()).execute(reciente.id)
    session.commit()

    relevante = _make_run(
        session, channel.id, max_comments_per_channel=30, strategy=SamplingStrategy.RELEVANT
    )
    AnalysisOrchestrator(session, youtube_client=_client()).execute(relevante.id)
    session.commit()

    buckets_recientes = {
        row.sampling_bucket
        for row in session.execute(
            select(AnalysisRunComment).where(AnalysisRunComment.run_id == reciente.id)
        ).scalars()
    }
    buckets_relevantes = {
        row.sampling_bucket
        for row in session.execute(
            select(AnalysisRunComment).where(AnalysisRunComment.run_id == relevante.id)
        ).scalars()
    }

    assert buckets_recientes == {"recent"}
    assert buckets_relevantes == {"relevant"}
    assert _sample_size(session, reciente.id) <= 30
    assert _sample_size(session, relevante.id) <= 30


@respx.mock
def test_un_comentario_solo_se_asocia_una_vez_por_ejecucion(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La estrategia mixta pide dos buckets que pueden solaparse."""
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_channel(video_count=2, comments_per_video=10)
    channel = _resolve_channel(session)

    run = _make_run(session, channel.id, max_comments_per_channel=100)
    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()

    filas = list(
        session.execute(
            select(AnalysisRunComment.comment_id).where(AnalysisRunComment.run_id == run.id)
        ).scalars()
    )
    assert len(filas) == len(set(filas))

    # Y el orden de selección no tiene huecos ni repeticiones.
    ordenes = sorted(
        session.execute(
            select(AnalysisRunComment.selection_order).where(AnalysisRunComment.run_id == run.id)
        ).scalars()
    )
    assert ordenes == list(range(len(ordenes)))


@respx.mock
def test_reintentar_el_mismo_trabajo_no_duplica_asociaciones(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "clave-de-prueba")
    _mock_channel(video_count=2, comments_per_video=10)
    channel = _resolve_channel(session)

    run = _make_run(session, channel.id, max_comments_per_channel=50)
    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()
    tras_el_primero = _sample_size(session, run.id)

    # El worker puede reintentar el mismo job: debe ser idempotente.
    AnalysisOrchestrator(session, youtube_client=_client()).execute(run.id)
    session.commit()

    assert _sample_size(session, run.id) == tras_el_primero


# --- Demo y borrado ---------------------------------------------------------


def test_el_modo_demo_crea_su_propia_muestra(session: Session) -> None:
    canal = DemoLoader(session).load("luciaglowdemo")
    session.commit()

    run = _make_run(
        session,
        canal.id,
        max_comments_per_channel=40,
        max_comments_per_video=5,
        source=DataSource.DEMO,
    )
    resultado = AnalysisOrchestrator(session).execute(run.id)
    session.commit()

    assert resultado.status == AnalysisStatus.COMPLETED, resultado.error_detail
    muestra = _sample_size(session, run.id)
    assert 0 < muestra <= 40
    # El límite por vídeo también se respeta en demo.
    assert resultado.comments_fetched == muestra


def test_borrar_una_ejecucion_no_borra_comentarios_de_otra(session: Session) -> None:
    canal = DemoLoader(session).load("luciaglowdemo")
    session.commit()

    primera = _make_run(session, canal.id, max_comments_per_channel=30, source=DataSource.DEMO)
    AnalysisOrchestrator(session).execute(primera.id)
    segunda = _make_run(session, canal.id, max_comments_per_channel=30, source=DataSource.DEMO)
    AnalysisOrchestrator(session).execute(segunda.id)
    session.commit()

    comentarios_compartidos = set(CommentRepository(session).list_for_run(primera.id)) & set(
        CommentRepository(session).list_for_run(segunda.id)
    )
    assert comentarios_compartidos, "las dos ejecuciones deberían compartir comentarios"

    total_antes = int(session.execute(select(func.count()).select_from(Comment)).scalar_one())

    runs = AnalysisRunRepository(session)
    runs.delete(primera.id)
    session.commit()

    assert _sample_size(session, primera.id) == 0
    assert _sample_size(session, segunda.id) > 0
    # Los comentarios siguen ahí: los comparte otra ejecución viva.
    assert int(session.execute(select(func.count()).select_from(Comment)).scalar_one()) == (
        total_antes
    )
    assert CommentRepository(session).list_for_run(segunda.id)
