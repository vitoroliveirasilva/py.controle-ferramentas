from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.locations.models import LocationModel
from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin
from app.tools.models import ToolModel
from app.users.models import UserModel


# Período de responsabilidade/custódia de uma ferramenta
class ToolCustodyModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_tool_custody"
    __table_args__ = (
        Index("ix_tb_cf_custody_tool", "id_tool"),
        Index("ix_tb_cf_custody_current", "id_tool", "atual"),
        Index("ix_tb_cf_custody_type", "tipo_custodia"),
        Index("ix_tb_cf_custody_user", "id_responsavel_usuario"),
        Index("ix_tb_cf_custody_location", "id_location"),
        Index(
            "ux_tb_cf_custody_current_tool",
            "id_tool",
            unique=True,
            sqlite_where=text("atual = 1 AND is_deleted = 0"),
            mssql_where=text("atual = 1 AND is_deleted = 0"),
        ),
        {"comment": "Histórico temporal de custódia das ferramentas."},
    )

    id_custody: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_tool: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_tool.id_tool"), nullable=False
    )
    tipo_custodia: Mapped[str] = mapped_column(String(40), nullable=False)
    id_responsavel_usuario: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    id_location: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_location.id_location"), nullable=True
    )
    responsavel_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    local_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inicio_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fim_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    atual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    motivo_inicio: Mapped[str] = mapped_column(Text, nullable=False)
    motivo_fim: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    encerrado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )

    tool: Mapped[ToolModel] = relationship("ToolModel", back_populates="custodias")
    responsavel_usuario: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[id_responsavel_usuario]
    )
    location: Mapped[LocationModel | None] = relationship("LocationModel")
    criado_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[criado_por_id]
    )
    encerrado_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[encerrado_por_id]
    )


# Evento de linha do tempo relacionado à custódia, para histórico e auditoria
class ToolTimelineEventModel(TimestampMixin, BaseModel):

    __tablename__ = "tb_cf_tool_timeline_event"
    __table_args__ = (
        Index("ix_tb_cf_timeline_tool_occurred", "id_tool", "occurred_at"),
        Index("ix_tb_cf_timeline_event_type", "event_type"),
        {"comment": "Linha do tempo operacional das ferramentas."},
    )

    id_event: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_tool: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_tool.id_tool"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    titulo: Mapped[str] = mapped_column(String(180), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    correlation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)

    tool: Mapped[ToolModel] = relationship(
        "ToolModel", back_populates="timeline_events"
    )
    actor: Mapped[UserModel | None] = relationship("UserModel")
