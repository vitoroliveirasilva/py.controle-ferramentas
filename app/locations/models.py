from __future__ import annotations

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin


# Local operacional onde uma ferramenta pode estar sob responsabilidade
class LocationModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_location"
    __table_args__ = (
        Index("ux_tb_cf_location_codigo", "codigo", unique=True),
        Index("ix_tb_cf_location_tipo", "tipo_local"),
        Index("ix_tb_cf_location_filial", "filial"),
        Index("ix_tb_cf_location_ativo", "ativo"),
        {
            "comment": "Locais administrativos e operacionais para inventário e custódia."
        },
    )

    id_location: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    tipo_local: Mapped[str] = mapped_column(String(40), nullable=False)
    filial: Mapped[str | None] = mapped_column(String(120), nullable=True)
    departamento: Mapped[str | None] = mapped_column(String(120), nullable=True)
    responsavel_nome: Mapped[str | None] = mapped_column(String(160), nullable=True)
    endereco: Mapped[str | None] = mapped_column(Text, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
