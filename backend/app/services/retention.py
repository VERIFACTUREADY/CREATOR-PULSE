"""Política de retención de datos.

Son **dos políticas distintas**, y conviene no confundirlas:

* `DATA_RETENTION_DAYS` — resultados de análisis. Caducan antes porque son
  derivados: se pueden recalcular.
* `COMMENT_RETENTION_DAYS` — comentarios brutos y sus metadatos. Se comparten
  entre ejecuciones y volver a descargarlos cuesta cuota de la API, así que se
  conservan más tiempo. Sólo se borra un comentario cuando ha caducado **y** ya
  no lo referencia ninguna ejecución viva.

Nada de esto ocurre solo. Es un comando que hay que programar (cron, un job de
Azure Container Apps, un `systemd timer`…). La interfaz dice cuándo se ejecutó
por última vez en lugar de prometer una automatización que la aplicación no
puede garantizar por sí misma.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.entities import (
    AnalysisRun,
    AnalysisRunComment,
    Channel,
    Comment,
    MaintenanceRun,
    Video,
)

logger = get_logger(__name__)

PURGE_KIND = "purga_retencion"


@dataclass
class PurgeReport:
    """Qué se ha borrado (o se borraría) y con qué criterio."""

    dry_run: bool
    run_retention_days: int
    comment_retention_days: int
    runs_cutoff: datetime
    comments_cutoff: datetime
    runs_deleted: int = 0
    run_samples_deleted: int = 0
    comments_deleted: int = 0
    comments_kept_referenced: int = 0
    orphan_videos: int = 0
    orphan_channels: int = 0
    counts_before: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "run_retention_days": self.run_retention_days,
            "comment_retention_days": self.comment_retention_days,
            "runs_cutoff": self.runs_cutoff.isoformat(),
            "comments_cutoff": self.comments_cutoff.isoformat(),
            "runs_deleted": self.runs_deleted,
            "run_samples_deleted": self.run_samples_deleted,
            "comments_deleted": self.comments_deleted,
            "comments_kept_referenced": self.comments_kept_referenced,
            "orphan_videos": self.orphan_videos,
            "orphan_channels": self.orphan_channels,
            "counts_before": self.counts_before,
        }

    def as_text(self) -> str:
        cabecera = "Simulación (no se ha borrado nada)" if self.dry_run else "Purga aplicada"
        verbo = "se eliminarían" if self.dry_run else "eliminados"
        return "\n".join(
            [
                cabecera,
                f"  Análisis {verbo}: {self.runs_deleted} "
                f"(anteriores a {self.runs_cutoff.date().isoformat()}, "
                f"retención de {self.run_retention_days} días)",
                f"  Asociaciones de muestra {verbo}: {self.run_samples_deleted}",
                f"  Comentarios {verbo}: {self.comments_deleted} "
                f"(anteriores a {self.comments_cutoff.date().isoformat()}, "
                f"retención de {self.comment_retention_days} días)",
                f"  Comentarios caducados pero conservados por estar en uso: "
                f"{self.comments_kept_referenced}",
                f"  Vídeos sin comentarios tras la purga: {self.orphan_videos} (no se borran)",
                f"  Canales sin vídeos ni análisis: {self.orphan_channels} (no se borran)",
            ]
        )


def _count(session: Session, model: type) -> int:
    return int(session.execute(select(func.count()).select_from(model)).scalar_one())


def purge(
    session: Session,
    *,
    run_retention_days: int | None = None,
    comment_retention_days: int | None = None,
    dry_run: bool = False,
) -> PurgeReport:
    """Aplica (o simula) la política de retención.

    Con `dry_run=True` no se modifica nada: se cuenta lo que se borraría.
    """
    now = datetime.now(UTC)
    run_days = (
        run_retention_days if run_retention_days is not None else settings.data_retention_days
    )
    comment_days = (
        comment_retention_days
        if comment_retention_days is not None
        else settings.comment_retention_days
    )

    report = PurgeReport(
        dry_run=dry_run,
        run_retention_days=run_days,
        comment_retention_days=comment_days,
        runs_cutoff=now - timedelta(days=run_days),
        comments_cutoff=now - timedelta(days=comment_days),
        counts_before={
            "analysis_run": _count(session, AnalysisRun),
            "comment": _count(session, Comment),
            "video": _count(session, Video),
            "channel": _count(session, Channel),
        },
    )

    caducadas = select(AnalysisRun.id).where(AnalysisRun.created_at < report.runs_cutoff)
    ids_caducadas = list(session.execute(caducadas).scalars())
    report.runs_deleted = len(ids_caducadas)
    report.run_samples_deleted = int(
        session.execute(
            select(func.count())
            .select_from(AnalysisRunComment)
            .where(AnalysisRunComment.run_id.in_(ids_caducadas))
        ).scalar_one()
        if ids_caducadas
        else 0
    )

    # Un comentario es borrable si ha caducado y **ninguna ejecución que vaya a
    # sobrevivir** lo referencia. Las ejecuciones caducadas no cuentan: se van
    # en esta misma purga.
    referenciados_por_vivas = select(AnalysisRunComment.comment_id)
    if ids_caducadas:
        referenciados_por_vivas = referenciados_por_vivas.where(
            AnalysisRunComment.run_id.notin_(ids_caducadas)
        )
    borrables = select(Comment.id).where(
        Comment.created_at < report.comments_cutoff,
        Comment.id.notin_(referenciados_por_vivas),
    )
    ids_borrables = list(session.execute(borrables).scalars())
    report.comments_deleted = len(ids_borrables)

    report.comments_kept_referenced = int(
        session.execute(
            select(func.count())
            .select_from(Comment)
            .where(
                Comment.created_at < report.comments_cutoff,
                Comment.id.in_(referenciados_por_vivas),
            )
        ).scalar_one()
    )

    if not dry_run:
        if ids_caducadas:
            # El borrado en cascada se lleva resultados y asociaciones.
            session.execute(delete(AnalysisRun).where(AnalysisRun.id.in_(ids_caducadas)))
        if ids_borrables:
            session.execute(delete(Comment).where(Comment.id.in_(ids_borrables)))
        session.flush()

    # Los huérfanos se cuentan pero **no se borran**: eliminar un canal es una
    # acción explícita del usuario, y borrarlo por detrás sería una sorpresa.
    report.orphan_videos = int(
        session.execute(
            select(func.count())
            .select_from(Video)
            .where(~select(Comment.id).where(Comment.video_id == Video.id).exists())
        ).scalar_one()
    )
    report.orphan_channels = int(
        session.execute(
            select(func.count())
            .select_from(Channel)
            .where(
                ~select(Video.id).where(Video.channel_id == Channel.id).exists(),
                ~select(AnalysisRun.id).where(AnalysisRun.channel_id == Channel.id).exists(),
            )
        ).scalar_one()
    )

    session.add(
        MaintenanceRun(
            kind=PURGE_KIND,
            executed_at=now,
            dry_run=dry_run,
            details=report.to_dict(),
        )
    )
    session.flush()

    logger.info(
        "retention_purge",
        dry_run=dry_run,
        runs_deleted=report.runs_deleted,
        comments_deleted=report.comments_deleted,
    )
    return report


def last_purge(session: Session, *, include_dry_runs: bool = False) -> MaintenanceRun | None:
    """Última purga registrada, para poder mostrarla en la interfaz."""
    stmt = select(MaintenanceRun).where(MaintenanceRun.kind == PURGE_KIND)
    if not include_dry_runs:
        stmt = stmt.where(MaintenanceRun.dry_run.is_(False))
    stmt = stmt.order_by(MaintenanceRun.executed_at.desc()).limit(1)
    return session.execute(stmt).scalar_one_or_none()


__all__ = ["PURGE_KIND", "PurgeReport", "last_purge", "purge"]
