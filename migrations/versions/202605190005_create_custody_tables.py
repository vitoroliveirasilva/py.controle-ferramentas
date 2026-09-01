"""create custody tables

Revision ID: 202605190005
Revises: 202605190004
Create Date: 2026-05-19 00:00:05

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190005"
down_revision = "202605190004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_cf_tool_custody",
        sa.Column("id_custody", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_tool", sa.Integer(), nullable=False),
        sa.Column("tipo_custodia", sa.String(length=40), nullable=False),
        sa.Column("id_responsavel_usuario", sa.Integer(), nullable=True),
        sa.Column("id_location", sa.Integer(), nullable=True),
        sa.Column("responsavel_snapshot", sa.String(length=255), nullable=False),
        sa.Column("local_snapshot", sa.String(length=255), nullable=True),
        sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fim_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("atual", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("motivo_inicio", sa.Text(), nullable=False),
        sa.Column("motivo_fim", sa.Text(), nullable=True),
        sa.Column("criado_por_id", sa.Integer(), nullable=True),
        sa.Column("encerrado_por_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["criado_por_id"],
            ["tb_cf_usuario.id_usuario"],
            name="fk_tb_cf_custody_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["encerrado_por_id"],
            ["tb_cf_usuario.id_usuario"],
            name="fk_tb_cf_custody_closed_by",
        ),
        sa.ForeignKeyConstraint(
            ["id_location"],
            ["tb_cf_location.id_location"],
            name="fk_tb_cf_custody_location",
        ),
        sa.ForeignKeyConstraint(
            ["id_responsavel_usuario"],
            ["tb_cf_usuario.id_usuario"],
            name="fk_tb_cf_custody_responsavel_usuario",
        ),
        sa.ForeignKeyConstraint(
            ["id_tool"], ["tb_cf_tool.id_tool"], name="fk_tb_cf_custody_tool"
        ),
        sa.PrimaryKeyConstraint("id_custody", name="pk_tb_cf_tool_custody"),
        comment="Histórico temporal de custódia das ferramentas.",
    )
    op.create_index("ix_tb_cf_custody_tool", "tb_cf_tool_custody", ["id_tool"])
    op.create_index(
        "ix_tb_cf_custody_current", "tb_cf_tool_custody", ["id_tool", "atual"]
    )
    op.create_index("ix_tb_cf_custody_type", "tb_cf_tool_custody", ["tipo_custodia"])
    op.create_index(
        "ix_tb_cf_custody_user", "tb_cf_tool_custody", ["id_responsavel_usuario"]
    )
    op.create_index("ix_tb_cf_custody_location", "tb_cf_tool_custody", ["id_location"])
    op.create_index(
        "ux_tb_cf_custody_current_tool",
        "tb_cf_tool_custody",
        ["id_tool"],
        unique=True,
        mssql_where=sa.text("atual = 1 AND is_deleted = 0"),
        sqlite_where=sa.text("atual = 1 AND is_deleted = 0"),
    )

    op.create_table(
        "tb_cf_tool_timeline_event",
        sa.Column("id_event", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_tool", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("titulo", sa.String(length=180), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("before_payload", sa.Text(), nullable=True),
        sa.Column("after_payload", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["tb_cf_usuario.id_usuario"],
            name="fk_tb_cf_timeline_actor",
        ),
        sa.ForeignKeyConstraint(
            ["id_tool"], ["tb_cf_tool.id_tool"], name="fk_tb_cf_timeline_tool"
        ),
        sa.PrimaryKeyConstraint("id_event", name="pk_tb_cf_tool_timeline_event"),
        comment="Linha do tempo operacional das ferramentas.",
    )
    op.create_index(
        "ix_tb_cf_timeline_tool_occurred",
        "tb_cf_tool_timeline_event",
        ["id_tool", "occurred_at"],
    )
    op.create_index(
        "ix_tb_cf_timeline_event_type", "tb_cf_tool_timeline_event", ["event_type"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tb_cf_timeline_event_type", table_name="tb_cf_tool_timeline_event"
    )
    op.drop_index(
        "ix_tb_cf_timeline_tool_occurred", table_name="tb_cf_tool_timeline_event"
    )
    op.drop_table("tb_cf_tool_timeline_event")

    op.drop_index("ux_tb_cf_custody_current_tool", table_name="tb_cf_tool_custody")
    op.drop_index("ix_tb_cf_custody_location", table_name="tb_cf_tool_custody")
    op.drop_index("ix_tb_cf_custody_user", table_name="tb_cf_tool_custody")
    op.drop_index("ix_tb_cf_custody_type", table_name="tb_cf_tool_custody")
    op.drop_index("ix_tb_cf_custody_current", table_name="tb_cf_tool_custody")
    op.drop_index("ix_tb_cf_custody_tool", table_name="tb_cf_tool_custody")
    op.drop_table("tb_cf_tool_custody")
