"""create access control tables

Revision ID: 202605190003
Revises: 202605190002
Create Date: 2026-05-19 00:00:03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190003"
down_revision = "202605190002"
branch_labels = None
depends_on = None


def _bool_default(value: bool) -> sa.TextClause:
    return sa.text("1" if value else "0")


def upgrade() -> None:
    op.create_table(
        "tb_cf_role",
        sa.Column("id_role", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=80), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=True),
        sa.Column(
            "ativo", sa.Boolean(), server_default=_bool_default(True), nullable=False
        ),
        sa.Column(
            "sistema", sa.Boolean(), server_default=_bool_default(True), nullable=False
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
        sa.PrimaryKeyConstraint("id_role", name="pk_tb_cf_role"),
        comment="Perfis de acesso do Sistema de Controle de Ferramentas.",
    )
    op.create_index("ux_tb_cf_role_codigo", "tb_cf_role", ["codigo"], unique=True)
    op.create_index("ix_tb_cf_role_ativo", "tb_cf_role", ["ativo"])

    op.create_table(
        "tb_cf_permission",
        sa.Column("id_permission", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=120), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("grupo", sa.String(length=80), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=True),
        sa.Column(
            "ativo", sa.Boolean(), server_default=_bool_default(True), nullable=False
        ),
        sa.Column(
            "sistema", sa.Boolean(), server_default=_bool_default(True), nullable=False
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
        sa.PrimaryKeyConstraint("id_permission", name="pk_tb_cf_permission"),
        comment="Permissões granulares validadas no backend.",
    )
    op.create_index(
        "ux_tb_cf_permission_codigo", "tb_cf_permission", ["codigo"], unique=True
    )
    op.create_index("ix_tb_cf_permission_grupo", "tb_cf_permission", ["grupo"])
    op.create_index("ix_tb_cf_permission_ativo", "tb_cf_permission", ["ativo"])

    op.create_table(
        "tb_cf_role_permission",
        sa.Column(
            "id_role_permission", sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column("id_role", sa.Integer(), nullable=False),
        sa.Column("id_permission", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_role"],
            ["tb_cf_role.id_role"],
            name="fk_tb_cf_role_permission_role",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["id_permission"],
            ["tb_cf_permission.id_permission"],
            name="fk_tb_cf_role_permission_permission",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_role_permission", name="pk_tb_cf_role_permission"),
        sa.UniqueConstraint(
            "id_role", "id_permission", name="uq_tb_cf_role_permission"
        ),
        comment="Vínculo N:N entre perfis e permissões.",
    )
    op.create_index(
        "ix_tb_cf_role_permission_role", "tb_cf_role_permission", ["id_role"]
    )
    op.create_index(
        "ix_tb_cf_role_permission_permission",
        "tb_cf_role_permission",
        ["id_permission"],
    )

    op.create_table(
        "tb_cf_user_role",
        sa.Column("id_user_role", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("id_role", sa.Integer(), nullable=False),
        sa.Column(
            "ativo", sa.Boolean(), server_default=_bool_default(True), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_usuario"],
            ["tb_cf_usuario.id_usuario"],
            name="fk_tb_cf_user_role_usuario",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["id_role"],
            ["tb_cf_role.id_role"],
            name="fk_tb_cf_user_role_role",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_user_role", name="pk_tb_cf_user_role"),
        sa.UniqueConstraint("id_usuario", "id_role", name="uq_tb_cf_user_role"),
        comment="Vínculo N:N entre usuários locais e perfis.",
    )
    op.create_index("ix_tb_cf_user_role_usuario", "tb_cf_user_role", ["id_usuario"])
    op.create_index("ix_tb_cf_user_role_role", "tb_cf_user_role", ["id_role"])

    op.create_table(
        "tb_cf_user_scope",
        sa.Column("id_user_scope", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_usuario", sa.Integer(), nullable=False),
        sa.Column("tipo_escopo", sa.String(length=40), nullable=False),
        sa.Column(
            "valor_escopo", sa.String(length=120), server_default="*", nullable=False
        ),
        sa.Column("descricao", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["id_usuario"],
            ["tb_cf_usuario.id_usuario"],
            name="fk_tb_cf_user_scope_usuario",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id_user_scope", name="pk_tb_cf_user_scope"),
        sa.UniqueConstraint(
            "id_usuario",
            "tipo_escopo",
            "valor_escopo",
            name="uq_tb_cf_user_scope_valor",
        ),
        comment="Escopos de acesso por usuário para limitar dados por contexto.",
    )
    op.create_index("ix_tb_cf_user_scope_usuario", "tb_cf_user_scope", ["id_usuario"])
    op.create_index(
        "ix_tb_cf_user_scope_tipo_valor",
        "tb_cf_user_scope",
        ["tipo_escopo", "valor_escopo"],
    )


def downgrade() -> None:
    op.drop_index("ix_tb_cf_user_scope_tipo_valor", table_name="tb_cf_user_scope")
    op.drop_index("ix_tb_cf_user_scope_usuario", table_name="tb_cf_user_scope")
    op.drop_table("tb_cf_user_scope")

    op.drop_index("ix_tb_cf_user_role_role", table_name="tb_cf_user_role")
    op.drop_index("ix_tb_cf_user_role_usuario", table_name="tb_cf_user_role")
    op.drop_table("tb_cf_user_role")

    op.drop_index(
        "ix_tb_cf_role_permission_permission", table_name="tb_cf_role_permission"
    )
    op.drop_index("ix_tb_cf_role_permission_role", table_name="tb_cf_role_permission")
    op.drop_table("tb_cf_role_permission")

    op.drop_index("ix_tb_cf_permission_ativo", table_name="tb_cf_permission")
    op.drop_index("ix_tb_cf_permission_grupo", table_name="tb_cf_permission")
    op.drop_index("ux_tb_cf_permission_codigo", table_name="tb_cf_permission")
    op.drop_table("tb_cf_permission")

    op.drop_index("ix_tb_cf_role_ativo", table_name="tb_cf_role")
    op.drop_index("ux_tb_cf_role_codigo", table_name="tb_cf_role")
    op.drop_table("tb_cf_role")
