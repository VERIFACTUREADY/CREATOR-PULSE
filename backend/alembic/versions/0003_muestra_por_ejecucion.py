"""Muestra de comentarios anclada a cada ejecución.

Antes, una ejecución analizaba todos los comentarios almacenados para sus
vídeos, incluidos los descargados por ejecuciones anteriores. Esta tabla
registra qué subconjunto miró cada `AnalysisRun`, con su bucket de muestreo y
su orden de selección.

Las ejecuciones anteriores a esta migración se quedan sin muestra registrada, y
eso es deliberado: no se puede reconstruir a posteriori qué comentarios vio
realmente cada una, y rellenarlo con todo lo disponible reintroduciría el mismo
error que se está corrigiendo. La calidad de datos marca ese caso.

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PgUUID

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_run_comment",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", PgUUID(as_uuid=True), nullable=False),
        sa.Column("comment_id", PgUUID(as_uuid=True), nullable=False),
        sa.Column("sampling_bucket", sa.String(length=32), nullable=True),
        sa.Column("selection_order", sa.Integer(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["analysis_run.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["comment.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "comment_id", name="uq_analysis_run_comment"),
    )
    op.create_index(
        "ix_analysis_run_comment_run_order",
        "analysis_run_comment",
        ["run_id", "selection_order"],
    )
    # Borrar un comentario caducado exige saber qué ejecuciones lo referencian.
    op.create_index(
        "ix_analysis_run_comment_comment",
        "analysis_run_comment",
        ["comment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_run_comment_comment", table_name="analysis_run_comment")
    op.drop_index("ix_analysis_run_comment_run_order", table_name="analysis_run_comment")
    op.drop_table("analysis_run_comment")
