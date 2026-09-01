"""create inventory divergence tables

Revision ID: 202605190008
Revises: 202605190007
Create Date: 2026-05-19 00:00:08

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190008"
down_revision = "202605190007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_cf_inventory_divergence",
        sa.Column(
            "id_inventory_divergence", sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column("id_inventory", sa.Integer(), nullable=False),
        sa.Column("id_inventory_item", sa.Integer(), nullable=True),
        sa.Column("id_tool", sa.Integer(), nullable=True),
        sa.Column("tipo_divergencia", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("severidade", sa.String(length=20), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("acao_regularizacao", sa.String(length=80), nullable=True),
        sa.Column("resolucao", sa.Text(), nullable=True),
        sa.Column("aberta_por_id", sa.Integer(), nullable=True),
        sa.Column("aberta_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("regularizada_por_id", sa.Integer(), nullable=True),
        sa.Column("regularizada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["aberta_por_id"], ["tb_cf_usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["id_inventory"], ["tb_cf_inventory.id_inventory"]),
        sa.ForeignKeyConstraint(
            ["id_inventory_item"], ["tb_cf_inventory_item.id_inventory_item"]
        ),
        sa.ForeignKeyConstraint(["id_tool"], ["tb_cf_tool.id_tool"]),
        sa.ForeignKeyConstraint(["regularizada_por_id"], ["tb_cf_usuario.id_usuario"]),
        sa.PrimaryKeyConstraint(
            "id_inventory_divergence", name="pk_tb_cf_inventory_divergence"
        ),
        comment="Divergências de inventário que exigem ação de regularização.",
    )
    op.create_index(
        "ix_tb_cf_inventory_div_inventory",
        "tb_cf_inventory_divergence",
        ["id_inventory"],
    )
    op.create_index(
        "ix_tb_cf_inventory_div_item",
        "tb_cf_inventory_divergence",
        ["id_inventory_item"],
    )
    op.create_index(
        "ix_tb_cf_inventory_div_tool",
        "tb_cf_inventory_divergence",
        ["id_tool"],
    )
    op.create_index(
        "ix_tb_cf_inventory_div_status",
        "tb_cf_inventory_divergence",
        ["status"],
    )
    op.create_index(
        "ix_tb_cf_inventory_div_type",
        "tb_cf_inventory_divergence",
        ["tipo_divergencia"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tb_cf_inventory_div_type", table_name="tb_cf_inventory_divergence"
    )
    op.drop_index(
        "ix_tb_cf_inventory_div_status", table_name="tb_cf_inventory_divergence"
    )
    op.drop_index(
        "ix_tb_cf_inventory_div_tool", table_name="tb_cf_inventory_divergence"
    )
    op.drop_index(
        "ix_tb_cf_inventory_div_item", table_name="tb_cf_inventory_divergence"
    )
    op.drop_index(
        "ix_tb_cf_inventory_div_inventory", table_name="tb_cf_inventory_divergence"
    )
    op.drop_table("tb_cf_inventory_divergence")
