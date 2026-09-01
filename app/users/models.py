from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin


class UserModel(UserMixin, TimestampMixin, SoftDeleteMixin, BaseModel):
    # Tabela de usuários locais, com campos para controle de status e informações básicas

    __tablename__ = "tb_cf_usuario"
    __table_args__ = (
        Index("ux_tb_cf_usuario_email_lower", "email_lower", unique=True),
        Index(
            "ux_tb_cf_usuario_microsoft_oid",
            "microsoft_oid",
            unique=True,
            sqlite_where=text("microsoft_oid IS NOT NULL"),
            mssql_where=text("microsoft_oid IS NOT NULL"),
        ),
        Index("ix_tb_cf_usuario_ativo_bloqueado", "ativo", "bloqueado"),
        {
            "comment": "Usuários locais autorizados pelo banco após autenticação Microsoft."
        },
    )

    id_usuario: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    microsoft_oid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    email_lower: Mapped[str] = mapped_column(String(255), nullable=False)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    bloqueado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    bloqueio_motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ultimo_login_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def get_id(self) -> str:
        return str(self.id_usuario)

    @property
    def is_active(self) -> bool:
        return bool(self.ativo and not self.bloqueado and not self.is_deleted)

    @property
    def display_name(self) -> str:
        return self.nome or self.email
