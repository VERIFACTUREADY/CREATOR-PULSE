"""Muestra inmutable por ejecución.

Añade `analysis_run.sample_finalized_at`, que marca el momento en que la
muestra queda cerrada, y una restricción única sobre `(run_id,
selection_order)`.

Sin lo primero, un reintento con datos distintos añadía comentarios nuevos a
una muestra ya usada: `ON CONFLICT DO NOTHING` evitaba duplicar pares, pero no
evitaba ampliarla. Sin lo segundo, dos registros parciales podían compartir
posición y la muestra dejaba de ser reproducible.

Las ejecuciones ya existentes que tengan muestra registrada se marcan como
cerradas: su selección es la que analizaron, y debe quedar congelada.

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_run",
        sa.Column("sample_finalized_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Antes de imponer la unicidad hay que dejar el orden consistente: una
    # instalación anterior pudo registrar la muestra en dos pasadas y repetir
    # posiciones. Se renumera por ejecución respetando el orden actual.
    op.execute(
        """
        WITH renumerado AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY run_id
                    ORDER BY selection_order, selected_at, id
                ) - 1 AS nueva_posicion
            FROM analysis_run_comment
        )
        UPDATE analysis_run_comment AS arc
        SET selection_order = renumerado.nueva_posicion
        FROM renumerado
        WHERE arc.id = renumerado.id
          AND arc.selection_order <> renumerado.nueva_posicion
        """
    )

    op.create_unique_constraint(
        "uq_analysis_run_comment_order",
        "analysis_run_comment",
        ["run_id", "selection_order"],
    )

    # Una ejecución que ya tiene muestra la tiene cerrada: es lo que analizó.
    op.execute(
        """
        UPDATE analysis_run
        SET sample_finalized_at = COALESCE(completed_at, created_at)
        WHERE EXISTS (
            SELECT 1 FROM analysis_run_comment
            WHERE analysis_run_comment.run_id = analysis_run.id
        )
        """
    )


def downgrade() -> None:
    op.drop_constraint("uq_analysis_run_comment_order", "analysis_run_comment", type_="unique")
    op.drop_column("analysis_run", "sample_finalized_at")
