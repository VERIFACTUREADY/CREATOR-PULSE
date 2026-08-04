"""Pruebas de los comandos de administración."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.cli import build_parser, main
from app.core.config import ALGORITHM_VERSION, settings
from app.models.entities import AnalysisRun, Channel
from app.models.enums import AnalysisStatus, DataSource, SamplingStrategy
from app.repositories.analysis import AnalysisRunRepository
from app.services.demo import DemoLoader
from sqlalchemy import func, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


@pytest.fixture
def cli_session(session: Session, monkeypatch: pytest.MonkeyPatch) -> Session:
    """Hace que la CLI use la sesión de la prueba en lugar de crear la suya."""
    from contextlib import contextmanager

    @contextmanager
    def _scope():  # type: ignore[no-untyped-def]
        yield session
        session.flush()

    monkeypatch.setattr("app.cli.session_scope", _scope)
    return session


def _run(session: Session, *, days_old: int) -> AnalysisRun:
    channel = DemoLoader(session).load("luciaglowdemo")
    run = AnalysisRunRepository(session).create(
        channel_id=channel.id,
        status=AnalysisStatus.COMPLETED,
        progress=100,
        max_videos=5,
        max_comments_per_video=50,
        max_comments_per_channel=200,
        include_replies=False,
        sampling_strategy=SamplingStrategy.MIXED,
        algorithm_version=ALGORITHM_VERSION,
        source=DataSource.DEMO,
    )
    run.created_at = datetime.now(UTC) - timedelta(days=days_old)
    session.add(run)
    session.flush()
    return run


def _count_runs(session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(AnalysisRun)).scalar_one())


# --- Parser -----------------------------------------------------------------


def test_parser_requires_a_command() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_parser_accepts_all_commands() -> None:
    parser = build_parser()
    assert parser.parse_args(["purgar"]).comando == "purgar"
    assert parser.parse_args(["estado"]).comando == "estado"
    assert parser.parse_args(["cargar-demo"]).comando == "cargar-demo"


# --- purgar -----------------------------------------------------------------


def test_purge_removes_only_expired_runs(
    cli_session: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    """La retención borra lo antiguo y respeta lo reciente."""
    _run(cli_session, days_old=120)
    reciente = _run(cli_session, days_old=1)
    cli_session.commit()

    assert main(["purgar", "--dias", "90"]) == 0

    assert _count_runs(cli_session) == 1
    assert cli_session.get(AnalysisRun, reciente.id) is not None
    salida = capsys.readouterr().out
    assert "Purga aplicada" in salida
    assert "Análisis eliminados: 1" in salida


def test_purge_dry_run_deletes_nothing(
    cli_session: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    _run(cli_session, days_old=200)
    cli_session.commit()

    assert main(["purgar", "--dias", "90", "--simular"]) == 0

    assert _count_runs(cli_session) == 1
    salida = capsys.readouterr().out
    assert "Simulación" in salida
    assert "No se ha borrado nada" in salida


def test_purge_keeps_channels(cli_session: Session) -> None:
    """La retención afecta a los análisis, no a los canales guardados."""
    _run(cli_session, days_old=200)
    cli_session.commit()

    main(["purgar", "--dias", "1"])

    canales = int(cli_session.execute(select(func.count()).select_from(Channel)).scalar_one())
    assert canales == 1
    assert _count_runs(cli_session) == 0


def test_purge_uses_configured_retention_by_default(
    cli_session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "data_retention_days", 30)
    _run(cli_session, days_old=45)
    cli_session.commit()

    main(["purgar"])

    assert _count_runs(cli_session) == 0
    assert "retención de 30 días" in capsys.readouterr().out


# --- estado -----------------------------------------------------------------


def test_status_reports_counts(cli_session: Session, capsys: pytest.CaptureFixture[str]) -> None:
    _run(cli_session, days_old=1)
    cli_session.commit()

    assert main(["estado"]) == 0

    salida = capsys.readouterr().out
    assert "Base de datos : correcta" in salida
    assert "Canales" in salida
    assert "Completados  : 1" in salida


def test_status_never_prints_secrets(
    cli_session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "youtube_api_key", "AIza-clave-secreta-de-prueba")
    main(["estado"])
    salida = capsys.readouterr().out
    assert "AIza" not in salida
    assert "configurada" in salida


# --- cargar-demo ------------------------------------------------------------


def test_load_demo_channel(cli_session: Session, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["cargar-demo", "--handle", "luciaglowdemo"]) == 0
    assert "Lucía Glow" in capsys.readouterr().out

    canales = int(cli_session.execute(select(func.count()).select_from(Channel)).scalar_one())
    assert canales == 1


def test_load_demo_rejects_unknown_handle(
    cli_session: Session, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["cargar-demo", "--handle", "noexiste"]) == 1
    assert "No existe el canal" in capsys.readouterr().err


def test_load_demo_respects_disabled_flag(
    cli_session: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(settings, "enable_demo_mode", False)
    assert main(["cargar-demo"]) == 1
    assert "desactivado" in capsys.readouterr().err
