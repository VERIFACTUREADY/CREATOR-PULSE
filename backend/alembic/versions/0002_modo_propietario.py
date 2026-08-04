"""Modo propietario: campos adicionales del token OAuth.

Añade el tipo de token, la marca del último refresco y el indicador de
revocación.

Las dos columnas obligatorias se crean con `server_default` para que la
migración funcione aunque la tabla ya tenga filas, y el valor por defecto se
retira después: a partir de ahí es la aplicación quien fija el valor.

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "oauth_token",
        sa.Column("token_type", sa.String(length=32), nullable=False, server_default="Bearer"),
    )
    op.add_column(
        "oauth_token",
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "oauth_token",
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # El valor por defecto sólo hacía falta para rellenar las filas existentes.
    op.alter_column("oauth_token", "token_type", server_default=None)
    op.alter_column("oauth_token", "revoked", server_default=None)


def downgrade() -> None:
    op.drop_column("oauth_token", "revoked")
    op.drop_column("oauth_token", "last_refreshed_at")
    op.drop_column("oauth_token", "token_type")
