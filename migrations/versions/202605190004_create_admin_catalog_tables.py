"""create admin catalog tables

Revision ID: 202605190004
Revises: 202605190003
Create Date: 2026-05-19 00:00:04

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190004"
down_revision = "202605190003"
branch_labels = None
depends_on = None


def _bool_default(value: bool) -> sa.TextClause:
    return sa.text("1" if value else "0")


def upgrade() -> None:
    op.create_table(
        "tb_cf_audit_log",
        sa.Column("id_audit_log", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=True),
        sa.Column("usuario_email", sa.String(length=255), nullable=True),
        sa.Column("acao", sa.String(length=120), nullable=False),
        sa.Column("entidade", sa.String(length=120), nullable=False),
        sa.Column("entidade_id", sa.String(length=80), nullable=True),
        sa.Column("antes", sa.Text(), nullable=True),
        sa.Column("depois", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("ip", sa.String(length=80), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("correlation_id", sa.String(length=80), nullable=True),
        sa.Column(
            "resultado", sa.String(length=40), nullable=False, server_default="success"
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id_audit_log", name="pk_tb_cf_audit_log"),
        comment="Logs de auditoria do Sistema de Controle de Ferramentas.",
    )
    op.create_index(
        "ix_tb_cf_audit_entity", "tb_cf_audit_log", ["entidade", "entidade_id"]
    )
    op.create_index("ix_tb_cf_audit_action", "tb_cf_audit_log", ["acao"])
    op.create_index("ix_tb_cf_audit_user", "tb_cf_audit_log", ["id_usuario"])

    op.create_table(
        "tb_cf_tool_category",
        sa.Column("id_categoria", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column(
            "ativo", sa.Boolean(), server_default=_bool_default(True), nullable=False
        ),
        sa.Column(
            "controle_individual_padrao",
            sa.Boolean(),
            server_default=_bool_default(True),
            nullable=False,
        ),
        sa.Column(
            "requer_numero_serie",
            sa.Boolean(),
            server_default=_bool_default(False),
            nullable=False,
        ),
        sa.Column(
            "requer_calibracao",
            sa.Boolean(),
            server_default=_bool_default(False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=_bool_default(False),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id_categoria", name="pk_tb_cf_tool_category"),
        comment="Categorias de ferramentas usadas nos cadastros administrativos.",
    )
    op.create_index(
        "ux_tb_cf_tool_category_codigo", "tb_cf_tool_category", ["codigo"], unique=True
    )
    op.create_index("ix_tb_cf_tool_category_nome", "tb_cf_tool_category", ["nome"])
    op.create_index("ix_tb_cf_tool_category_ativo", "tb_cf_tool_category", ["ativo"])

    op.create_table(
        "tb_cf_location",
        sa.Column("id_location", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=60), nullable=False),
        sa.Column("nome", sa.String(length=160), nullable=False),
        sa.Column("tipo_local", sa.String(length=40), nullable=False),
        sa.Column("filial", sa.String(length=120), nullable=True),
        sa.Column("departamento", sa.String(length=120), nullable=True),
        sa.Column("responsavel_nome", sa.String(length=160), nullable=True),
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column(
            "ativo", sa.Boolean(), server_default=_bool_default(True), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=_bool_default(False),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id_location", name="pk_tb_cf_location"),
        comment="Locais administrativos e operacionais para inventário e custódia.",
    )
    op.create_index(
        "ux_tb_cf_location_codigo", "tb_cf_location", ["codigo"], unique=True
    )
    op.create_index("ix_tb_cf_location_tipo", "tb_cf_location", ["tipo_local"])
    op.create_index("ix_tb_cf_location_filial", "tb_cf_location", ["filial"])
    op.create_index("ix_tb_cf_location_ativo", "tb_cf_location", ["ativo"])

    op.create_table(
        "tb_cf_tool",
        sa.Column("id_tool", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo_interno", sa.String(length=80), nullable=False),
        sa.Column("nome", sa.String(length=180), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("id_categoria", sa.Integer(), nullable=False),
        sa.Column(
            "status", sa.String(length=40), nullable=False, server_default="disponivel"
        ),
        sa.Column(
            "criticidade", sa.String(length=30), nullable=False, server_default="media"
        ),
        sa.Column("ativo_imobilizado", sa.String(length=80), nullable=True),
        sa.Column("numero_serie", sa.String(length=120), nullable=True),
        sa.Column("marca", sa.String(length=120), nullable=True),
        sa.Column("modelo", sa.String(length=120), nullable=True),
        sa.Column(
            "controle_individual",
            sa.Boolean(),
            server_default=_bool_default(True),
            nullable=False,
        ),
        sa.Column(
            "requer_calibracao",
            sa.Boolean(),
            server_default=_bool_default(False),
            nullable=False,
        ),
        sa.Column(
            "ativo", sa.Boolean(), server_default=_bool_default(True), nullable=False
        ),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default=_bool_default(False),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_categoria"],
            ["tb_cf_tool_category.id_categoria"],
            name="fk_tb_cf_tool_category",
        ),
        sa.PrimaryKeyConstraint("id_tool", name="pk_tb_cf_tool"),
        comment="Cadastro administrativo de ferramentas.",
    )
    op.create_index(
        "ux_tb_cf_tool_codigo_interno", "tb_cf_tool", ["codigo_interno"], unique=True
    )
    op.create_index(
        "ux_tb_cf_tool_ativo_imobilizado",
        "tb_cf_tool",
        ["ativo_imobilizado"],
        unique=True,
        mssql_where=sa.text("ativo_imobilizado IS NOT NULL"),
    )
    op.create_index(
        "ux_tb_cf_tool_numero_serie",
        "tb_cf_tool",
        ["numero_serie"],
        unique=True,
        mssql_where=sa.text("numero_serie IS NOT NULL"),
    )
    op.create_index("ix_tb_cf_tool_nome", "tb_cf_tool", ["nome"])
    op.create_index("ix_tb_cf_tool_status", "tb_cf_tool", ["status"])
    op.create_index("ix_tb_cf_tool_categoria", "tb_cf_tool", ["id_categoria"])


def downgrade() -> None:
    op.drop_index("ix_tb_cf_tool_categoria", table_name="tb_cf_tool")
    op.drop_index("ix_tb_cf_tool_status", table_name="tb_cf_tool")
    op.drop_index("ix_tb_cf_tool_nome", table_name="tb_cf_tool")
    op.drop_index("ux_tb_cf_tool_numero_serie", table_name="tb_cf_tool")
    op.drop_index("ux_tb_cf_tool_ativo_imobilizado", table_name="tb_cf_tool")
    op.drop_index("ux_tb_cf_tool_codigo_interno", table_name="tb_cf_tool")
    op.drop_table("tb_cf_tool")

    op.drop_index("ix_tb_cf_location_ativo", table_name="tb_cf_location")
    op.drop_index("ix_tb_cf_location_filial", table_name="tb_cf_location")
    op.drop_index("ix_tb_cf_location_tipo", table_name="tb_cf_location")
    op.drop_index("ux_tb_cf_location_codigo", table_name="tb_cf_location")
    op.drop_table("tb_cf_location")

    op.drop_index("ix_tb_cf_tool_category_ativo", table_name="tb_cf_tool_category")
    op.drop_index("ix_tb_cf_tool_category_nome", table_name="tb_cf_tool_category")
    op.drop_index("ux_tb_cf_tool_category_codigo", table_name="tb_cf_tool_category")
    op.drop_table("tb_cf_tool_category")

    op.drop_index("ix_tb_cf_audit_user", table_name="tb_cf_audit_log")
    op.drop_index("ix_tb_cf_audit_action", table_name="tb_cf_audit_log")
    op.drop_index("ix_tb_cf_audit_entity", table_name="tb_cf_audit_log")
    op.drop_table("tb_cf_audit_log")
