from __future__ import annotations

from sqlalchemy import Boolean, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin


# Categoria administrativa de ferramentas
class ToolCategoryModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_tool_category"
    __table_args__ = (
        Index("ux_tb_cf_tool_category_codigo", "codigo", unique=True),
        Index("ix_tb_cf_tool_category_nome", "nome"),
        Index("ix_tb_cf_tool_category_ativo", "ativo"),
        {"comment": "Categorias de ferramentas usadas nos cadastros administrativos."},
    )

    id_categoria: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    controle_individual_padrao: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    requer_numero_serie: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    requer_calibracao: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    ferramentas = relationship("ToolModel", back_populates="categoria")
