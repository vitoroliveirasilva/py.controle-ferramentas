"""create internal signature tables

Revision ID: 202605190010
Revises: 202605190009
Create Date: 2026-05-19 00:00:10

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190010"
down_revision = "202605190009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tb_cf_inventory") as batch_op:
        batch_op.add_column(
            sa.Column("finalizado_em", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("finalizado_por_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("motivo_finalizacao", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_tb_cf_inventory_finalizado_por",
            "tb_cf_usuario",
            ["finalizado_por_id"],
            ["id_usuario"],
        )

    op.create_table(
        "tb_cf_internal_signature",
        sa.Column("id_signature", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("acao", sa.String(length=100), nullable=False),
        sa.Column("entidade", sa.String(length=80), nullable=False),
        sa.Column("entidade_id", sa.String(length=80), nullable=False),
        sa.Column("resultado", sa.String(length=40), nullable=False),
        sa.Column("metodo", sa.String(length=60), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("contexto_json", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=80), nullable=True),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("usuario_email", sa.String(length=255), nullable=False),
        sa.Column("usuario_nome", sa.String(length=180), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(length=80), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("id_inventory", sa.Integer(), nullable=True),
        sa.Column("id_transfer", sa.Integer(), nullable=True),
        sa.Column("id_occurrence", sa.Integer(), nullable=True),
        sa.Column("id_inventory_divergence", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["id_inventory"], ["tb_cf_inventory.id_inventory"]),
        sa.ForeignKeyConstraint(
            ["id_inventory_divergence"],
            ["tb_cf_inventory_divergence.id_inventory_divergence"],
        ),
        sa.ForeignKeyConstraint(["id_occurrence"], ["tb_cf_occurrence.id_occurrence"]),
        sa.ForeignKeyConstraint(["id_transfer"], ["tb_cf_transfer.id_transfer"]),
        sa.ForeignKeyConstraint(["id_usuario"], ["tb_cf_usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_signature"),
        comment="Assinaturas internas/evidências de ações críticas.",
    )
    op.create_index(
        "ux_tb_cf_internal_signature_codigo",
        "tb_cf_internal_signature",
        ["codigo"],
        unique=True,
    )
    op.create_index(
        "ix_tb_cf_internal_signature_entity",
        "tb_cf_internal_signature",
        ["entidade", "entidade_id"],
    )
    op.create_index(
        "ix_tb_cf_internal_signature_action", "tb_cf_internal_signature", ["acao"]
    )
    op.create_index(
        "ix_tb_cf_internal_signature_result",
        "tb_cf_internal_signature",
        ["resultado"],
    )
    op.create_index(
        "ix_tb_cf_internal_signature_user",
        "tb_cf_internal_signature",
        ["id_usuario"],
    )
    op.create_index(
        "ix_tb_cf_internal_signature_inventory",
        "tb_cf_internal_signature",
        ["id_inventory"],
    )
    op.create_index(
        "ix_tb_cf_internal_signature_transfer",
        "tb_cf_internal_signature",
        ["id_transfer"],
    )
    op.create_index(
        "ix_tb_cf_internal_signature_occurrence",
        "tb_cf_internal_signature",
        ["id_occurrence"],
    )
    op.create_index(
        "ix_tb_cf_internal_signature_signed_at",
        "tb_cf_internal_signature",
        ["signed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tb_cf_internal_signature_signed_at", table_name="tb_cf_internal_signature"
    )
    op.drop_index(
        "ix_tb_cf_internal_signature_occurrence", table_name="tb_cf_internal_signature"
    )
    op.drop_index(
        "ix_tb_cf_internal_signature_transfer", table_name="tb_cf_internal_signature"
    )
    op.drop_index(
        "ix_tb_cf_internal_signature_inventory", table_name="tb_cf_internal_signature"
    )
    op.drop_index(
        "ix_tb_cf_internal_signature_user", table_name="tb_cf_internal_signature"
    )
    op.drop_index(
        "ix_tb_cf_internal_signature_result", table_name="tb_cf_internal_signature"
    )
    op.drop_index(
        "ix_tb_cf_internal_signature_action", table_name="tb_cf_internal_signature"
    )
    op.drop_index(
        "ix_tb_cf_internal_signature_entity", table_name="tb_cf_internal_signature"
    )
    op.drop_index(
        "ux_tb_cf_internal_signature_codigo", table_name="tb_cf_internal_signature"
    )
    op.drop_table("tb_cf_internal_signature")

    with op.batch_alter_table("tb_cf_inventory") as batch_op:
        batch_op.drop_constraint(
            "fk_tb_cf_inventory_finalizado_por", type_="foreignkey"
        )
        batch_op.drop_column("motivo_finalizacao")
        batch_op.drop_column("finalizado_por_id")
        batch_op.drop_column("finalizado_em")
