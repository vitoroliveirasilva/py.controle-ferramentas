from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TimestampMixin
from app.users.models import UserModel


# Evidência de confirmação interna para ações críticas do sistema
class InternalSignatureModel(TimestampMixin, BaseModel):

    __tablename__ = "tb_cf_internal_signature"
    __table_args__ = (
        Index("ux_tb_cf_internal_signature_codigo", "codigo", unique=True),
        Index("ix_tb_cf_internal_signature_entity", "entidade", "entidade_id"),
        Index("ix_tb_cf_internal_signature_action", "acao"),
        Index("ix_tb_cf_internal_signature_result", "resultado"),
        Index("ix_tb_cf_internal_signature_user", "id_usuario"),
        Index("ix_tb_cf_internal_signature_inventory", "id_inventory"),
        Index("ix_tb_cf_internal_signature_transfer", "id_transfer"),
        Index("ix_tb_cf_internal_signature_occurrence", "id_occurrence"),
        Index("ix_tb_cf_internal_signature_signed_at", "signed_at"),
        {"comment": "Assinaturas internas/evidências de ações críticas."},
    )

    id_signature: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    acao: Mapped[str] = mapped_column(String(100), nullable=False)
    entidade: Mapped[str] = mapped_column(String(80), nullable=False)
    entidade_id: Mapped[str] = mapped_column(String(80), nullable=False)
    resultado: Mapped[str] = mapped_column(String(40), nullable=False)
    metodo: Mapped[str] = mapped_column(String(60), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    contexto_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    id_usuario: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=False
    )
    usuario_email: Mapped[str] = mapped_column(String(255), nullable=False)
    usuario_nome: Mapped[str] = mapped_column(String(180), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    id_inventory: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_inventory.id_inventory"), nullable=True
    )
    id_transfer: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_transfer.id_transfer"), nullable=True
    )
    id_occurrence: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_occurrence.id_occurrence"), nullable=True
    )
    id_inventory_divergence: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_inventory_divergence.id_inventory_divergence"), nullable=True
    )

    usuario: Mapped[UserModel] = relationship("UserModel")
