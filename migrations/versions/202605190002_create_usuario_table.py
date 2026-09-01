"""create usuario table

Revision ID: 202605190002
Revises: 202605190001
Create Date: 2026-05-19 00:00:02

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190002"
down_revision = "202605190001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_cf_usuario",
        sa.Column("id_usuario", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("microsoft_oid", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("email_lower", sa.String(length=255), nullable=False),
        sa.Column("nome", sa.String(length=180), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "bloqueado", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("bloqueio_motivo", sa.String(length=255), nullable=True),
        sa.Column("ultimo_login_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id_usuario", name="pk_tb_cf_usuario"),
        comment="Usuários locais autorizados pelo banco após autenticação Microsoft.",
    )
    op.create_index(
        "ux_tb_cf_usuario_email_lower", "tb_cf_usuario", ["email_lower"], unique=True
    )
    op.create_index(
        "ix_tb_cf_usuario_ativo_bloqueado",
        "tb_cf_usuario",
        ["ativo", "bloqueado"],
    )

    bind = op.get_bind()
    dialect_name = bind.dialect.name if bind is not None else ""

    if dialect_name == "mssql":
        op.create_index(
            "ux_tb_cf_usuario_microsoft_oid",
            "tb_cf_usuario",
            ["microsoft_oid"],
            unique=True,
            mssql_where=sa.text("microsoft_oid IS NOT NULL"),
        )
    elif dialect_name == "sqlite":
        op.create_index(
            "ux_tb_cf_usuario_microsoft_oid",
            "tb_cf_usuario",
            ["microsoft_oid"],
            unique=True,
            sqlite_where=sa.text("microsoft_oid IS NOT NULL"),
        )
    else:
        op.create_index(
            "ux_tb_cf_usuario_microsoft_oid",
            "tb_cf_usuario",
            ["microsoft_oid"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("ux_tb_cf_usuario_microsoft_oid", table_name="tb_cf_usuario")
    op.drop_index("ix_tb_cf_usuario_ativo_bloqueado", table_name="tb_cf_usuario")
    op.drop_index("ux_tb_cf_usuario_email_lower", table_name="tb_cf_usuario")
    op.drop_table("tb_cf_usuario")
