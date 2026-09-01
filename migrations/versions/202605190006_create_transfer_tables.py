"""create transfer tables

Revision ID: 202605190006
Revises: 202605190005
Create Date: 2026-05-19 00:00:06

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190006"
down_revision = "202605190005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_cf_transfer",
        sa.Column("id_transfer", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("tipo_transferencia", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("destino_tipo_custodia", sa.String(length=40), nullable=False),
        sa.Column("destino_usuario_id", sa.Integer(), nullable=True),
        sa.Column("destino_location_id", sa.Integer(), nullable=True),
        sa.Column(
            "destino_responsavel_snapshot", sa.String(length=255), nullable=False
        ),
        sa.Column("destino_local_snapshot", sa.String(length=255), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("solicitado_por_id", sa.Integer(), nullable=True),
        sa.Column("origem_confirmada_por_id", sa.Integer(), nullable=True),
        sa.Column("destino_confirmado_por_id", sa.Integer(), nullable=True),
        sa.Column("recusado_por_id", sa.Integer(), nullable=True),
        sa.Column("cancelado_por_id", sa.Integer(), nullable=True),
        sa.Column("solicitado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origem_confirmada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("destino_confirmado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recusado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_recusa", sa.Text(), nullable=True),
        sa.Column("motivo_cancelamento", sa.Text(), nullable=True),
        sa.Column(
            "assinatura_unica_prevista",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cancelado_por_id"], ["tb_cf_usuario.id_usuario"]),
        sa.ForeignKeyConstraint(
            ["destino_confirmado_por_id"], ["tb_cf_usuario.id_usuario"]
        ),
        sa.ForeignKeyConstraint(
            ["destino_location_id"], ["tb_cf_location.id_location"]
        ),
        sa.ForeignKeyConstraint(["destino_usuario_id"], ["tb_cf_usuario.id_usuario"]),
        sa.ForeignKeyConstraint(
            ["origem_confirmada_por_id"], ["tb_cf_usuario.id_usuario"]
        ),
        sa.ForeignKeyConstraint(["recusado_por_id"], ["tb_cf_usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["solicitado_por_id"], ["tb_cf_usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_transfer", name="pk_tb_cf_transfer"),
        comment="Processos formais de transferência de ferramentas.",
    )
    op.create_index(
        "ix_tb_cf_transfer_codigo", "tb_cf_transfer", ["codigo"], unique=True
    )
    op.create_index(
        "ix_tb_cf_transfer_dest_location", "tb_cf_transfer", ["destino_location_id"]
    )
    op.create_index(
        "ix_tb_cf_transfer_dest_user", "tb_cf_transfer", ["destino_usuario_id"]
    )
    op.create_index(
        "ix_tb_cf_transfer_solicitante", "tb_cf_transfer", ["solicitado_por_id"]
    )
    op.create_index("ix_tb_cf_transfer_status", "tb_cf_transfer", ["status"])
    op.create_index("ix_tb_cf_transfer_tipo", "tb_cf_transfer", ["tipo_transferencia"])

    op.create_table(
        "tb_cf_transfer_item",
        sa.Column("id_transfer_item", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_transfer", sa.Integer(), nullable=False),
        sa.Column("id_tool", sa.Integer(), nullable=False),
        sa.Column("id_custody_origem", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("status_ferramenta_anterior", sa.String(length=40), nullable=False),
        sa.Column("origem_tipo_custodia", sa.String(length=40), nullable=False),
        sa.Column("origem_responsavel_snapshot", sa.String(length=255), nullable=False),
        sa.Column("origem_local_snapshot", sa.String(length=255), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("concluido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_custody_origem"], ["tb_cf_tool_custody.id_custody"]
        ),
        sa.ForeignKeyConstraint(["id_tool"], ["tb_cf_tool.id_tool"]),
        sa.ForeignKeyConstraint(["id_transfer"], ["tb_cf_transfer.id_transfer"]),
        sa.PrimaryKeyConstraint("id_transfer_item", name="pk_tb_cf_transfer_item"),
        comment="Itens individuais de processos de transferência.",
    )
    op.create_index("ix_tb_cf_transfer_item_status", "tb_cf_transfer_item", ["status"])
    op.create_index("ix_tb_cf_transfer_item_tool", "tb_cf_transfer_item", ["id_tool"])
    op.create_index(
        "ix_tb_cf_transfer_item_transfer", "tb_cf_transfer_item", ["id_transfer"]
    )


def downgrade() -> None:
    op.drop_index("ix_tb_cf_transfer_item_transfer", table_name="tb_cf_transfer_item")
    op.drop_index("ix_tb_cf_transfer_item_tool", table_name="tb_cf_transfer_item")
    op.drop_index("ix_tb_cf_transfer_item_status", table_name="tb_cf_transfer_item")
    op.drop_table("tb_cf_transfer_item")
    op.drop_index("ix_tb_cf_transfer_tipo", table_name="tb_cf_transfer")
    op.drop_index("ix_tb_cf_transfer_status", table_name="tb_cf_transfer")
    op.drop_index("ix_tb_cf_transfer_solicitante", table_name="tb_cf_transfer")
    op.drop_index("ix_tb_cf_transfer_dest_user", table_name="tb_cf_transfer")
    op.drop_index("ix_tb_cf_transfer_dest_location", table_name="tb_cf_transfer")
    op.drop_index("ix_tb_cf_transfer_codigo", table_name="tb_cf_transfer")
    op.drop_table("tb_cf_transfer")
