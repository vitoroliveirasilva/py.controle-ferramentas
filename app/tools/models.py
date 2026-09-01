from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.categories.models import ToolCategoryModel
from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin


# Cadastro mestre de ferramenta controlada pelo sistema
class ToolModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_tool"
    __table_args__ = (
        Index("ux_tb_cf_tool_codigo_interno", "codigo_interno", unique=True),
        Index(
            "ux_tb_cf_tool_ativo_imobilizado",
            "ativo_imobilizado",
            unique=True,
            sqlite_where=text("ativo_imobilizado IS NOT NULL"),
            mssql_where=text("ativo_imobilizado IS NOT NULL"),
        ),
        Index(
            "ux_tb_cf_tool_numero_serie",
            "numero_serie",
            unique=True,
            sqlite_where=text("numero_serie IS NOT NULL"),
            mssql_where=text("numero_serie IS NOT NULL"),
        ),
        Index("ix_tb_cf_tool_nome", "nome"),
        Index("ix_tb_cf_tool_status", "status"),
        Index("ix_tb_cf_tool_categoria", "id_categoria"),
        {"comment": "Cadastro administrativo de ferramentas."},
    )

    id_tool: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo_interno: Mapped[str] = mapped_column(String(80), nullable=False)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_categoria: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_tool_category.id_categoria"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="disponivel"
    )
    criticidade: Mapped[str] = mapped_column(
        String(30), nullable=False, default="media"
    )
    ativo_imobilizado: Mapped[str | None] = mapped_column(String(80), nullable=True)
    numero_serie: Mapped[str | None] = mapped_column(String(120), nullable=True)
    marca: Mapped[str | None] = mapped_column(String(120), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    controle_individual: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    requer_calibracao: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    referencia_foto_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referencia_foto_filename: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    referencia_foto_content_type: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    referencia_foto_size_bytes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    referencia_foto_uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    referencia_foto_uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )

    categoria: Mapped[ToolCategoryModel] = relationship(
        "ToolCategoryModel", back_populates="ferramentas"
    )


# Relacionamentos definidos após a classe para evitar acoplamento circular em imports de tipo
ToolModel.custodias = relationship(
    "ToolCustodyModel",
    back_populates="tool",
    order_by="ToolCustodyModel.inicio_em.desc()",
    cascade="save-update, merge",
)
ToolModel.timeline_events = relationship(
    "ToolTimelineEventModel",
    back_populates="tool",
    order_by="ToolTimelineEventModel.occurred_at.desc()",
    cascade="save-update, merge",
)
