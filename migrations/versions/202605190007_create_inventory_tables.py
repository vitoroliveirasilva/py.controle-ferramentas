"""create inventory tables

Revision ID: 202605190007
Revises: 202605190006
Create Date: 2026-05-19 00:00:07

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190007"
down_revision = "202605190006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_cf_inventory",
        sa.Column("id_inventory", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("titulo", sa.String(length=180), nullable=False),
        sa.Column("tipo_inventario", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("escopo_tipo", sa.String(length=20), nullable=False),
        sa.Column("escopo_usuario_id", sa.Integer(), nullable=True),
        sa.Column("escopo_location_id", sa.Integer(), nullable=True),
        sa.Column("escopo_responsavel_snapshot", sa.String(length=255), nullable=True),
        sa.Column("escopo_local_snapshot", sa.String(length=255), nullable=True),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelado_por_id", sa.Integer(), nullable=True),
        sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cancelado_por_id"], ["tb_cf_usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["criado_por_id"], ["tb_cf_usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["escopo_location_id"], ["tb_cf_location.id_location"]),
        sa.ForeignKeyConstraint(["escopo_usuario_id"], ["tb_cf_usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_inventory", name="pk_tb_cf_inventory"),
        comment="Inventários de ferramentas por técnico ou local.",
    )
    op.create_index(
        "ix_tb_cf_inventory_codigo", "tb_cf_inventory", ["codigo"], unique=True
    )
    op.create_index("ix_tb_cf_inventory_status", "tb_cf_inventory", ["status"])
    op.create_index("ix_tb_cf_inventory_tipo", "tb_cf_inventory", ["tipo_inventario"])
    op.create_index(
        "ix_tb_cf_inventory_scope_user", "tb_cf_inventory", ["escopo_usuario_id"]
    )
    op.create_index(
        "ix_tb_cf_inventory_scope_location", "tb_cf_inventory", ["escopo_location_id"]
    )

    op.create_table(
        "tb_cf_inventory_item",
        sa.Column(
            "id_inventory_item", sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column("id_inventory", sa.Integer(), nullable=False),
        sa.Column("id_tool", sa.Integer(), nullable=False),
        sa.Column("id_custody_snapshot", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("codigo_interno_snapshot", sa.String(length=80), nullable=False),
        sa.Column("ferramenta_nome_snapshot", sa.String(length=180), nullable=False),
        sa.Column("categoria_snapshot", sa.String(length=180), nullable=True),
        sa.Column("status_ferramenta_esperado", sa.String(length=40), nullable=False),
        sa.Column("tipo_custodia_esperada", sa.String(length=40), nullable=False),
        sa.Column("responsavel_snapshot", sa.String(length=255), nullable=True),
        sa.Column("local_snapshot", sa.String(length=255), nullable=True),
        sa.Column("ativo_imobilizado_snapshot", sa.String(length=80), nullable=True),
        sa.Column("numero_serie_snapshot", sa.String(length=120), nullable=True),
        sa.Column("conferido_por_id", sa.Integer(), nullable=True),
        sa.Column("conferido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conferido_por_id"], ["tb_cf_usuario.id_usuario"]),
        sa.ForeignKeyConstraint(
            ["id_custody_snapshot"], ["tb_cf_tool_custody.id_custody"]
        ),
        sa.ForeignKeyConstraint(["id_inventory"], ["tb_cf_inventory.id_inventory"]),
        sa.ForeignKeyConstraint(["id_tool"], ["tb_cf_tool.id_tool"]),
        sa.PrimaryKeyConstraint("id_inventory_item", name="pk_tb_cf_inventory_item"),
        comment="Itens de conferência física de inventário.",
    )
    op.create_index(
        "ix_tb_cf_inventory_item_inventory", "tb_cf_inventory_item", ["id_inventory"]
    )
    op.create_index("ix_tb_cf_inventory_item_tool", "tb_cf_inventory_item", ["id_tool"])
    op.create_index(
        "ix_tb_cf_inventory_item_status", "tb_cf_inventory_item", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_tb_cf_inventory_item_status", table_name="tb_cf_inventory_item")
    op.drop_index("ix_tb_cf_inventory_item_tool", table_name="tb_cf_inventory_item")
    op.drop_index(
        "ix_tb_cf_inventory_item_inventory", table_name="tb_cf_inventory_item"
    )
    op.drop_table("tb_cf_inventory_item")
    op.drop_index("ix_tb_cf_inventory_scope_location", table_name="tb_cf_inventory")
    op.drop_index("ix_tb_cf_inventory_scope_user", table_name="tb_cf_inventory")
    op.drop_index("ix_tb_cf_inventory_tipo", table_name="tb_cf_inventory")
    op.drop_index("ix_tb_cf_inventory_status", table_name="tb_cf_inventory")
    op.drop_index("ix_tb_cf_inventory_codigo", table_name="tb_cf_inventory")
    op.drop_table("tb_cf_inventory")
