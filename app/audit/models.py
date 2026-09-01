from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TimestampMixin


# Registro append-only de eventos administrativos e alterações críticas
class AuditLogModel(TimestampMixin, BaseModel):

    __tablename__ = "tb_cf_audit_log"
    __table_args__ = (
        Index("ix_tb_cf_audit_entity", "entidade", "entidade_id"),
        Index("ix_tb_cf_audit_action", "acao"),
        Index("ix_tb_cf_audit_user", "id_usuario"),
        {"comment": "Logs de auditoria do Sistema de Controle de Ferramentas."},
    )

    id_audit_log: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_usuario: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usuario_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acao: Mapped[str] = mapped_column(String(120), nullable=False)
    entidade: Mapped[str] = mapped_column(String(120), nullable=False)
    entidade_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    antes: Mapped[str | None] = mapped_column(Text, nullable=True)
    depois: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resultado: Mapped[str] = mapped_column(
        String(40), nullable=False, default="success"
    )
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
