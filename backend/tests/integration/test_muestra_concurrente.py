"""Dos workers sobre la misma ejecución no pueden corromper la muestra.

`register_run_sample` comprobaba `sample_finalized_at` sin bloquear la fila.
Con dos procesos simultáneos —RQ lo hace improbable, no imposible— ambos podían
verla a `NULL`, borrar la muestra del otro e insertar la suya. El resultado era
una muestra a medias o un `IntegrityError` por órdenes repetidos.

Estas pruebas usan **dos sesiones reales de PostgreSQL**: sin transacciones de
verdad, el bloqueo no se puede comprobar.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any

import pytest
from app.core.config import ALGORITHM_VERSION
from app.models.entities import AnalysisRun, AnalysisRunComment, Comment
from app.models.enums import AnalysisStatus, DataSource, SamplingStrategy
from app.repositories.analysis import AnalysisRunRepository
from app.repositories.channels import CommentRepository
from app.services.demo import DemoLoader
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

pytestmark = pytest.mark.integration


def _crear_run(session: Session, canal_id: Any, *, max_comments: int = 40) -> AnalysisRun:
    run = AnalysisRunRepository(session).create(
        channel_id=canal_id,
        status=AnalysisStatus.QUEUED,
        progress=0,
        max_videos=5,
        max_comments_per_video=max_comments,
        max_comments_per_channel=max_comments,
        include_replies=False,
        sampling_strategy=SamplingStrategy.MIXED,
        algorithm_version=ALGORITHM_VERSION,
        source=DataSource.DEMO,
    )
    session.commit()
    return run


def _total_asociaciones(session: Session, run_id: uuid.UUID) -> int:
    return int(
        session.execute(
            select(func.count())
            .select_from(AnalysisRunComment)
            .where(AnalysisRunComment.run_id == run_id)
        ).scalar_one()
    )


def test_dos_sesiones_simultaneas_no_corrompen_la_muestra(session: Session, engine: Any) -> None:
    """El segundo worker espera en el bloqueo y reutiliza lo que cerró el primero."""
    canal = DemoLoader(session).load("luciaglowdemo")
    session.commit()
    run = _crear_run(session, canal.id)

    comentarios = list(session.execute(select(Comment).limit(20)).scalars())
    primera_mitad = [(c.id, "recent") for c in comentarios[:10]]
    segunda_mitad = [(c.id, "relevant") for c in comentarios[10:]]
    session.commit()

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    resultados: list[Any] = []
    errores: list[BaseException] = []
    barrera = threading.Barrier(2, timeout=30)

    def registrar(seleccion: list[tuple[uuid.UUID, str]]) -> None:
        db = factory()
        try:
            # Ambos hilos llegan a la vez al cierre de la muestra.
            barrera.wait()
            resultado = CommentRepository(db).register_run_sample(run.id, seleccion)
            db.commit()
            resultados.append(resultado)
        except BaseException as exc:
            errores.append(exc)
            db.rollback()
        finally:
            db.close()

    hilos = [
        threading.Thread(target=registrar, args=(primera_mitad,)),
        threading.Thread(target=registrar, args=(segunda_mitad,)),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=40)

    assert errores == [], f"ninguno debería fallar: {errores}"
    assert len(resultados) == 2

    # Uno cierra la muestra y el otro la reutiliza. Nunca los dos escriben.
    reutilizados = [r for r in resultados if r.reused]
    escritores = [r for r in resultados if not r.reused]
    assert len(escritores) == 1, "sólo un worker puede cerrar la muestra"
    assert len(reutilizados) == 1, "el segundo debe reutilizar la del primero"

    session.expire_all()
    total = _total_asociaciones(session, run.id)
    assert total == 10, "la muestra es exactamente la que cerró el primero"
    assert escritores[0].inserted == 10
    assert reutilizados[0].inserted == 0
    assert reutilizados[0].size == 10


def test_los_ordenes_siguen_siendo_unicos_tras_la_carrera(session: Session, engine: Any) -> None:
    canal = DemoLoader(session).load("luciaglowdemo")
    session.commit()
    run = _crear_run(session, canal.id)
    comentarios = list(session.execute(select(Comment).limit(12)).scalars())
    session.commit()

    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    barrera = threading.Barrier(2, timeout=30)
    errores: list[BaseException] = []

    def registrar(desde: int) -> None:
        db = factory()
        try:
            barrera.wait()
            CommentRepository(db).register_run_sample(
                run.id, [(c.id, "demo") for c in comentarios[desde : desde + 6]]
            )
            db.commit()
        except BaseException as exc:
            errores.append(exc)
            db.rollback()
        finally:
            db.close()

    hilos = [
        threading.Thread(target=registrar, args=(0,)),
        threading.Thread(target=registrar, args=(6,)),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=40)

    assert errores == [], f"no debe haber IntegrityError por órdenes repetidos: {errores}"

    session.expire_all()
    ordenes = sorted(
        session.execute(
            select(AnalysisRunComment.selection_order).where(AnalysisRunComment.run_id == run.id)
        ).scalars()
    )
    assert ordenes == list(range(len(ordenes)))
    assert len(ordenes) == len(set(ordenes))
