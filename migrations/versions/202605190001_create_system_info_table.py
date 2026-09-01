"""create system info table

Revision ID: 202605190001
Revises:
Create Date: 2026-05-19 00:00:01

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_cf_system_info",
        sa.Column("id_system_info", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chave", sa.String(length=120), nullable=False),
        sa.Column("valor", sa.Text(), nullable=True),
        sa.Column("descricao", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id_system_info", name="pk_tb_cf_system_info"),
        sa.UniqueConstraint("chave", name="uq_tb_cf_system_info_chave"),
        comment="Tabela técnica inicial do Sistema de Controle de Ferramentas.",
    )
    op.create_index("ix_tb_cf_system_info_chave", "tb_cf_system_info", ["chave"])


def downgrade() -> None:
    op.drop_index("ix_tb_cf_system_info_chave", table_name="tb_cf_system_info")
    op.drop_table("tb_cf_system_info")
