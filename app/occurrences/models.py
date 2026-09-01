from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin
from app.tools.models import ToolModel
from app.users.models import UserModel


# Registro formal de ocorrência operacional ou patrimonial de ferramenta
class OccurrenceModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_occurrence"
    __table_args__ = (
        Index("ux_tb_cf_occurrence_codigo", "codigo", unique=True),
        Index("ix_tb_cf_occurrence_tool", "id_tool"),
        Index("ix_tb_cf_occurrence_tipo", "tipo_ocorrencia"),
        Index("ix_tb_cf_occurrence_status", "status"),
        Index("ix_tb_cf_occurrence_registrante", "registrante_id"),
        Index("ix_tb_cf_occurrence_created", "created_at"),
        {"comment": "Ocorrências de perda, dano, baixa, manutenção e regularizações."},
    )

    id_occurrence: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    id_tool: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_tool.id_tool"), nullable=False
    )
    tipo_ocorrencia: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="aberta")
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    responsavel_atual_snapshot: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    custodia_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo_imobilizado_snapshot: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )
    impacto_patrimonial: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    fato_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registrado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    registrante_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    registrante_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decisao: Mapped[str | None] = mapped_column(String(40), nullable=True)
    decisao_motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    aprovado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    aprovado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolvido_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    resolvido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observacoes_resolucao: Mapped[str | None] = mapped_column(Text, nullable=True)

    tool: Mapped[ToolModel] = relationship("ToolModel")
    registrante: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[registrante_id]
    )
    aprovado_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[aprovado_por_id]
    )
    resolvido_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[resolvido_por_id]
    )
    anexos: Mapped[list[OccurrenceAttachmentModel]] = relationship(
        "OccurrenceAttachmentModel",
        back_populates="occurrence",
        cascade="save-update, merge",
        order_by="OccurrenceAttachmentModel.uploaded_at.desc()",
    )


# Metadados de anexo/foto vinculado a uma ocorrência
class OccurrenceAttachmentModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_occurrence_attachment"
    __table_args__ = (
        Index("ix_tb_cf_occ_attachment_occurrence", "id_occurrence"),
        {"comment": "Anexos de evidência das ocorrências."},
    )

    id_attachment: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_occurrence: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_occurrence.id_occurrence"), nullable=False
    )
    filename_original: Mapped[str] = mapped_column(String(255), nullable=False)
    filename_storage: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)

    occurrence: Mapped[OccurrenceModel] = relationship(
        "OccurrenceModel", back_populates="anexos"
    )
    uploaded_by: Mapped[UserModel | None] = relationship("UserModel")
