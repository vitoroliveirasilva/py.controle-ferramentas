"""create occurrence tables

Revision ID: 202605190009
Revises: 202605190008
Create Date: 2026-05-19 00:00:09

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190009"
down_revision = "202605190008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_cf_occurrence",
        sa.Column("id_occurrence", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("id_tool", sa.Integer(), nullable=False),
        sa.Column("tipo_ocorrencia", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("responsavel_atual_snapshot", sa.String(length=255), nullable=True),
        sa.Column("custodia_snapshot", sa.Text(), nullable=True),
        sa.Column("ativo_imobilizado_snapshot", sa.String(length=80), nullable=True),
        sa.Column(
            "impacto_patrimonial",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("fato_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registrado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrante_id", sa.Integer(), nullable=True),
        sa.Column("registrante_email", sa.String(length=255), nullable=True),
        sa.Column("decisao", sa.String(length=40), nullable=True),
        sa.Column("decisao_motivo", sa.Text(), nullable=True),
        sa.Column("aprovado_por_id", sa.Integer(), nullable=True),
        sa.Column("aprovado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolvido_por_id", sa.Integer(), nullable=True),
        sa.Column("resolvido_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacoes_resolucao", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["aprovado_por_id"], ["tb_cf_usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["id_tool"], ["tb_cf_tool.id_tool"]),
        sa.ForeignKeyConstraint(["registrante_id"], ["tb_cf_usuario.id_usuario"]),
        sa.ForeignKeyConstraint(["resolvido_por_id"], ["tb_cf_usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_occurrence"),
        comment="Ocorrências de perda, dano, baixa, manutenção e regularizações.",
    )
    op.create_index(
        "ux_tb_cf_occurrence_codigo", "tb_cf_occurrence", ["codigo"], unique=True
    )
    op.create_index("ix_tb_cf_occurrence_tool", "tb_cf_occurrence", ["id_tool"])
    op.create_index("ix_tb_cf_occurrence_tipo", "tb_cf_occurrence", ["tipo_ocorrencia"])
    op.create_index("ix_tb_cf_occurrence_status", "tb_cf_occurrence", ["status"])
    op.create_index(
        "ix_tb_cf_occurrence_registrante", "tb_cf_occurrence", ["registrante_id"]
    )
    op.create_index("ix_tb_cf_occurrence_created", "tb_cf_occurrence", ["created_at"])

    op.create_table(
        "tb_cf_occurrence_attachment",
        sa.Column("id_attachment", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_occurrence", sa.Integer(), nullable=False),
        sa.Column("filename_original", sa.String(length=255), nullable=False),
        sa.Column("filename_storage", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column(
            "tamanho_bytes", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["id_occurrence"], ["tb_cf_occurrence.id_occurrence"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["tb_cf_usuario.id_usuario"]),
        sa.PrimaryKeyConstraint("id_attachment"),
        comment="Anexos de evidência das ocorrências.",
    )
    op.create_index(
        "ix_tb_cf_occ_attachment_occurrence",
        "tb_cf_occurrence_attachment",
        ["id_occurrence"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tb_cf_occ_attachment_occurrence", table_name="tb_cf_occurrence_attachment"
    )
    op.drop_table("tb_cf_occurrence_attachment")
    op.drop_index("ix_tb_cf_occurrence_created", table_name="tb_cf_occurrence")
    op.drop_index("ix_tb_cf_occurrence_registrante", table_name="tb_cf_occurrence")
    op.drop_index("ix_tb_cf_occurrence_status", table_name="tb_cf_occurrence")
    op.drop_index("ix_tb_cf_occurrence_tipo", table_name="tb_cf_occurrence")
    op.drop_index("ix_tb_cf_occurrence_tool", table_name="tb_cf_occurrence")
    op.drop_index("ux_tb_cf_occurrence_codigo", table_name="tb_cf_occurrence")
    op.drop_table("tb_cf_occurrence")
