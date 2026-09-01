from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin
from app.users.models import UserModel


# Notificação interna gerada por pendências operacionais do sistema
class NotificationModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_notification"
    __table_args__ = (
        Index("ux_tb_cf_notification_codigo", "codigo", unique=True),
        Index(
            "ux_tb_cf_notification_dedupe",
            "dedupe_key",
            unique=True,
            sqlite_where=text("dedupe_key IS NOT NULL"),
            mssql_where=text("dedupe_key IS NOT NULL"),
        ),
        Index("ix_tb_cf_notification_status", "status"),
        Index("ix_tb_cf_notification_tipo", "tipo_notificacao"),
        Index("ix_tb_cf_notification_priority", "prioridade"),
        Index("ix_tb_cf_notification_user", "id_usuario_destino"),
        Index("ix_tb_cf_notification_entity", "entidade", "entidade_id"),
        Index("ix_tb_cf_notification_channel", "canal"),
        {"comment": "Notificações internas de pendências operacionais."},
    )

    id_notification: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    tipo_notificacao: Mapped[str] = mapped_column(String(60), nullable=False)
    titulo: Mapped[str] = mapped_column(String(180), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    prioridade: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    canal: Mapped[str] = mapped_column(String(30), nullable=False)
    entidade: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entidade_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    id_usuario_destino: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    destinatario_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    origem: Mapped[str | None] = mapped_column(String(80), nullable=True)
    lida_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    enviada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultima_tentativa_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tentativas_envio: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    erro_envio: Mapped[str | None] = mapped_column(Text, nullable=True)

    usuario_destino: Mapped[UserModel | None] = relationship("UserModel")
    entregas: Mapped[list[NotificationDeliveryModel]] = relationship(
        "NotificationDeliveryModel",
        back_populates="notification",
        cascade="save-update, merge",
        order_by="NotificationDeliveryModel.attempted_at.desc()",
    )


# Histórico de tentativas de envio de notificação por canal
class NotificationDeliveryModel(TimestampMixin, BaseModel):

    __tablename__ = "tb_cf_notification_delivery"
    __table_args__ = (
        Index("ix_tb_cf_notification_delivery_notification", "id_notification"),
        Index("ix_tb_cf_notification_delivery_status", "status"),
        Index("ix_tb_cf_notification_delivery_channel", "canal"),
        Index("ix_tb_cf_notification_delivery_attempted", "attempted_at"),
        {"comment": "Histórico de entrega/envio das notificações."},
    )

    id_delivery: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_notification: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_notification.id_notification"), nullable=False
    )
    canal: Mapped[str] = mapped_column(String(30), nullable=False)
    destino: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    resposta: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    notification: Mapped[NotificationModel] = relationship(
        "NotificationModel", back_populates="entregas"
    )
