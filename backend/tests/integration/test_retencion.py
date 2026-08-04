"""Retención de datos: dos políticas y una purga que no rompe nada.

Un comentario se comparte entre ejecuciones. Borrarlo por antigüedad sin mirar
quién lo usa dejaría análisis vivos sin su muestra, así que la condición es
doble: caducado **y** no referenciado por ninguna ejecución que sobreviva.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import ALGORITHM_VERSION, settings
from app.models.entities import AnalysisRun, AnalysisRunComment, Comment, MaintenanceRun
from app.models.enums import AnalysisStatus, DataSource, SamplingStrategy
from app.repositories.analysis import AnalysisRunRepository
from app.repositories.channels import CommentRepository
from app.services.demo import DemoLoader
from app.services.retention import last_purge, purge
from sqlalchemy import func, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _canal(session: Session) -> object:
    canal = DemoLoader(session).load("luciaglowdemo")
    session.commit()
    return canal


def _run(session: Session, canal_id: object, *, edad_dias: int = 0) -> AnalysisRun:
    run = AnalysisRunRepository(session).create(
        channel_id=canal_id,
        status=AnalysisStatus.COMPLETED,
        progress=100,
        max_videos=5,
        max_comments_per_video=10,
        max_comments_per_channel=50,
        include_replies=False,
        sampling_strategy=SamplingStrategy.MIXED,
        algorithm_version=ALGORITHM_VERSION,
        source=DataSource.DEMO,
    )
    session.flush()
    if edad_dias:
        run.created_at = datetime.now(UTC) - timedelta(days=edad_dias)
    session.commit()
    return run


def _envejecer_comentarios(session: Session, dias: int, limite: int | None = None) -> list[Comment]:
    stmt = select(Comment)
    if limite is not None:
        stmt = stmt.limit(limite)
    comentarios = list(session.execute(stmt).scalars())
    viejo = datetime.now(UTC) - timedelta(days=dias)
    for comentario in comentarios:
        comentario.created_at = viejo
    session.commit()
    return comentarios


def _total(session: Session, model: type) -> int:
    return int(session.execute(select(func.count()).select_from(model)).scalar_one())


# --- Ejecuciones ------------------------------------------------------------


def test_una_ejecucion_caducada_se_elimina(session: Session) -> None:
    canal = _canal(session)
    caducada = _run(session, canal.id, edad_dias=120)

    informe = purge(session, run_retention_days=90)
    session.commit()

    assert informe.runs_deleted == 1
    assert session.get(AnalysisRun, caducada.id) is None


def test_una_ejecucion_vigente_se_conserva(session: Session) -> None:
    canal = _canal(session)
    vigente = _run(session, canal.id, edad_dias=10)

    informe = purge(session, run_retention_days=90)
    session.commit()

    assert informe.runs_deleted == 0
    assert session.get(AnalysisRun, vigente.id) is not None


def test_al_borrar_la_ejecucion_se_van_sus_asociaciones(session: Session) -> None:
    canal = _canal(session)
    run = _run(session, canal.id, edad_dias=200)
    comentarios = list(session.execute(select(Comment).limit(5)).scalars())
    CommentRepository(session).register_run_sample(run.id, [(c.id, "demo") for c in comentarios])
    session.commit()
    assert _total(session, AnalysisRunComment) == 5

    purge(session, run_retention_days=90)
    session.commit()

    assert _total(session, AnalysisRunComment) == 0


# --- Comentarios ------------------------------------------------------------


def test_un_comentario_en_uso_por_una_ejecucion_viva_se_conserva(session: Session) -> None:
    """La condición doble: caducado no basta si alguien lo usa."""
    canal = _canal(session)
    viva = _run(session, canal.id, edad_dias=1)
    comentarios = _envejecer_comentarios(session, dias=400, limite=5)
    CommentRepository(session).register_run_sample(viva.id, [(c.id, "demo") for c in comentarios])
    session.commit()

    informe = purge(session, run_retention_days=90, comment_retention_days=180)
    session.commit()

    assert informe.comments_kept_referenced >= 5
    for comentario in comentarios:
        assert session.get(Comment, comentario.id) is not None


def test_un_comentario_huerfano_y_caducado_se_elimina(session: Session) -> None:
    _canal(session)
    comentarios = _envejecer_comentarios(session, dias=400, limite=3)
    ids = [c.id for c in comentarios]

    informe = purge(session, run_retention_days=90, comment_retention_days=180)
    session.commit()

    assert informe.comments_deleted >= 3
    for comentario_id in ids:
        assert session.get(Comment, comentario_id) is None


def test_un_comentario_caducado_de_una_ejecucion_tambien_caducada_se_elimina(
    session: Session,
) -> None:
    """La ejecución se va en esta misma purga, así que ya no lo protege."""
    canal = _canal(session)
    caducada = _run(session, canal.id, edad_dias=200)
    comentarios = _envejecer_comentarios(session, dias=400, limite=4)
    CommentRepository(session).register_run_sample(
        caducada.id, [(c.id, "demo") for c in comentarios]
    )
    session.commit()
    ids = [c.id for c in comentarios]

    purge(session, run_retention_days=90, comment_retention_days=180)
    session.commit()

    for comentario_id in ids:
        assert session.get(Comment, comentario_id) is None


def test_un_comentario_reciente_no_se_toca(session: Session) -> None:
    _canal(session)
    antes = _total(session, Comment)

    informe = purge(session, run_retention_days=90, comment_retention_days=180)
    session.commit()

    assert informe.comments_deleted == 0
    assert _total(session, Comment) == antes


# --- Simulación y registro --------------------------------------------------


def test_la_simulacion_no_escribe_absolutamente_nada(session: Session) -> None:
    """Cero escrituras: ni borrados, ni su propio registro de mantenimiento."""
    canal = _canal(session)
    _run(session, canal.id, edad_dias=200)
    _envejecer_comentarios(session, dias=400, limite=6)

    antes = {
        modelo.__name__: _total(session, modelo)
        for modelo in (AnalysisRun, Comment, AnalysisRunComment, MaintenanceRun)
    }

    informe = purge(session, run_retention_days=90, comment_retention_days=180, dry_run=True)

    # La sesión no debe tener nada pendiente de escribir antes de confirmar.
    assert not session.new, "la simulación ha añadido objetos a la sesión"
    assert not session.dirty, "la simulación ha modificado objetos"
    assert not session.deleted, "la simulación ha marcado objetos para borrar"

    session.commit()

    assert informe.dry_run is True
    assert informe.runs_deleted == 1
    assert informe.comments_deleted >= 6
    despues = {
        modelo.__name__: _total(session, modelo)
        for modelo in (AnalysisRun, Comment, AnalysisRunComment, MaintenanceRun)
    }
    assert despues == antes


def test_la_simulacion_no_altera_marcas_de_tiempo(session: Session) -> None:
    canal = _canal(session)
    run = _run(session, canal.id, edad_dias=10)
    creado = run.created_at

    purge(session, run_retention_days=90, comment_retention_days=180, dry_run=True)
    session.commit()

    session.refresh(run)
    assert run.created_at == creado


def test_el_informe_desglosa_por_entidad(session: Session) -> None:
    canal = _canal(session)
    _run(session, canal.id, edad_dias=200)

    informe = purge(session, run_retention_days=90, dry_run=True)

    assert set(informe.counts_before) == {"analysis_run", "comment", "video", "channel"}
    texto = informe.as_text()
    assert "Análisis" in texto
    assert "Comentarios" in texto
    assert "no se borran" in texto


def test_la_purga_queda_registrada(session: Session) -> None:
    _canal(session)

    purge(session, run_retention_days=90)
    session.commit()

    registro = last_purge(session)
    assert registro is not None
    assert registro.dry_run is False
    assert registro.details is not None
    assert "runs_deleted" in registro.details


def test_una_simulacion_no_deja_registro_de_mantenimiento(session: Session) -> None:
    _canal(session)

    purge(session, run_retention_days=90, dry_run=True)
    session.commit()

    assert last_purge(session) is None
    # Y tampoco queda una fila marcada como simulación: la traza va al log.
    assert _total(session, MaintenanceRun) == 0


def test_una_purga_real_si_deja_registro(session: Session) -> None:
    _canal(session)

    purge(session, run_retention_days=90, dry_run=True)
    purge(session, run_retention_days=90)
    session.commit()

    assert _total(session, MaintenanceRun) == 1
    registro = last_purge(session)
    assert registro is not None and registro.dry_run is False


def test_los_canales_no_se_borran_por_la_purga(session: Session) -> None:
    """Eliminar un canal es una acción explícita del usuario, nunca un efecto."""
    canal = _canal(session)
    _envejecer_comentarios(session, dias=400)

    purge(session, run_retention_days=1, comment_retention_days=1)
    session.commit()

    from app.repositories.channels import ChannelRepository

    assert ChannelRepository(session).get(canal.id) is not None


def test_purgar_sin_datos_no_falla(session: Session) -> None:
    informe = purge(session, run_retention_days=30)
    session.commit()

    assert informe.runs_deleted == 0
    assert informe.comments_deleted == 0
    assert last_purge(session) is not None


def test_los_valores_por_defecto_vienen_de_la_configuracion(session: Session) -> None:
    informe = purge(session, dry_run=True)

    assert informe.run_retention_days == settings.data_retention_days
    assert informe.comment_retention_days == settings.comment_retention_days


def test_borrar_una_ejecucion_concreta_no_toca_los_comentarios(session: Session) -> None:
    canal = _canal(session)
    run = _run(session, canal.id)
    comentarios = list(session.execute(select(Comment).limit(3)).scalars())
    CommentRepository(session).register_run_sample(run.id, [(c.id, "demo") for c in comentarios])
    session.commit()
    antes = _total(session, Comment)

    AnalysisRunRepository(session).delete(run.id)
    session.commit()

    assert _total(session, Comment) == antes
    assert _total(session, AnalysisRunComment) == 0
    assert session.get(AnalysisRun, run.id) is None
    assert uuid.UUID(str(canal.id))
