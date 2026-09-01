"""add mobile evidence and qr support fields

Revision ID: 202605190014
Revises: 202605190013
Create Date: 2026-05-19 00:00:14

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190014"
down_revision = "202605190013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tb_cf_tool",
        sa.Column("referencia_foto_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "tb_cf_tool",
        sa.Column("referencia_foto_filename", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "tb_cf_tool",
        sa.Column("referencia_foto_content_type", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "tb_cf_tool",
        sa.Column("referencia_foto_size_bytes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tb_cf_tool",
        sa.Column(
            "referencia_foto_uploaded_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "tb_cf_tool",
        sa.Column("referencia_foto_uploaded_by_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_tb_cf_tool_ref_photo_user",
        "tb_cf_tool",
        "tb_cf_usuario",
        ["referencia_foto_uploaded_by_id"],
        ["id_usuario"],
    )

    op.create_table(
        "tb_cf_inventory_item_evidence",
        sa.Column(
            "id_inventory_item_evidence",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("id_inventory_item", sa.Integer(), nullable=False),
        sa.Column("id_inventory", sa.Integer(), nullable=False),
        sa.Column("id_tool", sa.Integer(), nullable=True),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_inventory_item"],
            ["tb_cf_inventory_item.id_inventory_item"],
            name="fk_tb_cf_inv_item_ev_item",
        ),
        sa.ForeignKeyConstraint(
            ["id_inventory"],
            ["tb_cf_inventory.id_inventory"],
            name="fk_tb_cf_inv_item_ev_inventory",
        ),
        sa.ForeignKeyConstraint(
            ["id_tool"],
            ["tb_cf_tool.id_tool"],
            name="fk_tb_cf_inv_item_ev_tool",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["tb_cf_usuario.id_usuario"],
            name="fk_tb_cf_inv_item_ev_user",
        ),
        sa.PrimaryKeyConstraint(
            "id_inventory_item_evidence",
            name="pk_tb_cf_inventory_item_evidence",
        ),
        comment="Evidências de conferência física dos itens de inventário.",
    )
    op.create_index(
        "ix_tb_cf_inventory_item_ev_item",
        "tb_cf_inventory_item_evidence",
        ["id_inventory_item"],
    )
    op.create_index(
        "ix_tb_cf_inventory_item_ev_inventory",
        "tb_cf_inventory_item_evidence",
        ["id_inventory"],
    )
    op.create_index(
        "ix_tb_cf_inventory_item_ev_tool",
        "tb_cf_inventory_item_evidence",
        ["id_tool"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tb_cf_inventory_item_ev_tool", table_name="tb_cf_inventory_item_evidence"
    )
    op.drop_index(
        "ix_tb_cf_inventory_item_ev_inventory",
        table_name="tb_cf_inventory_item_evidence",
    )
    op.drop_index(
        "ix_tb_cf_inventory_item_ev_item", table_name="tb_cf_inventory_item_evidence"
    )
    op.drop_table("tb_cf_inventory_item_evidence")
    op.drop_constraint("fk_tb_cf_tool_ref_photo_user", "tb_cf_tool", type_="foreignkey")
    op.drop_column("tb_cf_tool", "referencia_foto_uploaded_by_id")
    op.drop_column("tb_cf_tool", "referencia_foto_uploaded_at")
    op.drop_column("tb_cf_tool", "referencia_foto_size_bytes")
    op.drop_column("tb_cf_tool", "referencia_foto_content_type")
    op.drop_column("tb_cf_tool", "referencia_foto_filename")
    op.drop_column("tb_cf_tool", "referencia_foto_path")
