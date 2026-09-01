from __future__ import annotations

from sqlalchemy import Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin


# Tabela técnica para validar migrações e setup do banco, sem relação com o domínio de ferramentas
class SystemInfoModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_system_info"
    __table_args__ = (
        UniqueConstraint("chave", name="uq_tb_cf_system_info_chave"),
        Index("ix_tb_cf_system_info_chave", "chave"),
        {"comment": "Tabela técnica inicial do Sistema de Controle de Ferramentas."},
    )

    id_system_info: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    chave: Mapped[str] = mapped_column(String(120), nullable=False)
    valor: Mapped[str | None] = mapped_column(Text, nullable=True)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
