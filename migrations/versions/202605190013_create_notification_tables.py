"""create notification tables

Revision ID: 202605190013
Revises: 202605190010
Create Date: 2026-05-19 00:00:13

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "202605190013"
down_revision = "202605190010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tb_cf_notification",
        sa.Column("id_notification", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(length=50), nullable=False),
        sa.Column("tipo_notificacao", sa.String(length=60), nullable=False),
        sa.Column("titulo", sa.String(length=180), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("prioridade", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("canal", sa.String(length=30), nullable=False),
        sa.Column("entidade", sa.String(length=80), nullable=True),
        sa.Column("entidade_id", sa.String(length=80), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("id_usuario_destino", sa.Integer(), nullable=True),
        sa.Column("destinatario_email", sa.String(length=255), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("origem", sa.String(length=80), nullable=True),
        sa.Column("lida_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enviada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultima_tentativa_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "tentativas_envio",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("erro_envio", sa.Text(), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_usuario_destino"],
            ["tb_cf_usuario.id_usuario"],
            name="fk_notification_user",
        ),
        sa.PrimaryKeyConstraint("id_notification", name="pk_tb_cf_notification"),
        comment="Notificações internas de pendências operacionais.",
    )
    op.create_index(
        "ux_tb_cf_notification_codigo", "tb_cf_notification", ["codigo"], unique=True
    )
    op.create_index(
        "ux_tb_cf_notification_dedupe",
        "tb_cf_notification",
        ["dedupe_key"],
        unique=True,
        sqlite_where=sa.text("dedupe_key IS NOT NULL"),
        mssql_where=sa.text("dedupe_key IS NOT NULL"),
    )
    op.create_index("ix_tb_cf_notification_status", "tb_cf_notification", ["status"])
    op.create_index(
        "ix_tb_cf_notification_tipo", "tb_cf_notification", ["tipo_notificacao"]
    )
    op.create_index(
        "ix_tb_cf_notification_priority", "tb_cf_notification", ["prioridade"]
    )
    op.create_index(
        "ix_tb_cf_notification_user", "tb_cf_notification", ["id_usuario_destino"]
    )
    op.create_index(
        "ix_tb_cf_notification_entity",
        "tb_cf_notification",
        ["entidade", "entidade_id"],
    )
    op.create_index("ix_tb_cf_notification_channel", "tb_cf_notification", ["canal"])

    op.create_table(
        "tb_cf_notification_delivery",
        sa.Column("id_delivery", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_notification", sa.Integer(), nullable=False),
        sa.Column("canal", sa.String(length=30), nullable=False),
        sa.Column("destino", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("resposta", sa.Text(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["id_notification"],
            ["tb_cf_notification.id_notification"],
            name="fk_notification_delivery_notification",
        ),
        sa.PrimaryKeyConstraint("id_delivery", name="pk_tb_cf_notification_delivery"),
        comment="Histórico de entrega/envio das notificações.",
    )
    op.create_index(
        "ix_tb_cf_notification_delivery_notification",
        "tb_cf_notification_delivery",
        ["id_notification"],
    )
    op.create_index(
        "ix_tb_cf_notification_delivery_status",
        "tb_cf_notification_delivery",
        ["status"],
    )
    op.create_index(
        "ix_tb_cf_notification_delivery_channel",
        "tb_cf_notification_delivery",
        ["canal"],
    )
    op.create_index(
        "ix_tb_cf_notification_delivery_attempted",
        "tb_cf_notification_delivery",
        ["attempted_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tb_cf_notification_delivery_attempted",
        table_name="tb_cf_notification_delivery",
    )
    op.drop_index(
        "ix_tb_cf_notification_delivery_channel",
        table_name="tb_cf_notification_delivery",
    )
    op.drop_index(
        "ix_tb_cf_notification_delivery_status",
        table_name="tb_cf_notification_delivery",
    )
    op.drop_index(
        "ix_tb_cf_notification_delivery_notification",
        table_name="tb_cf_notification_delivery",
    )
    op.drop_table("tb_cf_notification_delivery")

    op.drop_index("ix_tb_cf_notification_channel", table_name="tb_cf_notification")
    op.drop_index("ix_tb_cf_notification_entity", table_name="tb_cf_notification")
    op.drop_index("ix_tb_cf_notification_user", table_name="tb_cf_notification")
    op.drop_index("ix_tb_cf_notification_priority", table_name="tb_cf_notification")
    op.drop_index("ix_tb_cf_notification_tipo", table_name="tb_cf_notification")
    op.drop_index("ix_tb_cf_notification_status", table_name="tb_cf_notification")
    op.drop_index("ux_tb_cf_notification_dedupe", table_name="tb_cf_notification")
    op.drop_index("ux_tb_cf_notification_codigo", table_name="tb_cf_notification")
    op.drop_table("tb_cf_notification")
