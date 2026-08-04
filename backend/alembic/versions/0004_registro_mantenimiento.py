"""Registro de tareas de mantenimiento.

Permite mostrar en la interfaz cuándo se purgó por última vez, en lugar de
afirmar que los datos «se purgan automáticamente»: la purga es un comando que
alguien tiene que programar, y la aplicación no puede prometerlo por sí sola.

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "maintenance_run",
        sa.Column("id", PgUUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("details", JSONB(), nullable=True),
    )
    op.create_index(
        "ix_maintenance_run_kind_executed",
        "maintenance_run",
        ["kind", "executed_at"],
    )
    # El valor por defecto sólo servía para no romper filas existentes; a
    # partir de aquí lo fija la aplicación.
    op.alter_column("maintenance_run", "dry_run", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_maintenance_run_kind_executed", table_name="maintenance_run")
    op.drop_table("maintenance_run")
