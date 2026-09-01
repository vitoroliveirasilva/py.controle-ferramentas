from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.locations.models import LocationModel
from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin
from app.tools.models import ToolModel
from app.users.models import UserModel


# Processo formal de transferência de uma ou mais ferramentas
class TransferModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_transfer"
    __table_args__ = (
        Index("ix_tb_cf_transfer_status", "status"),
        Index("ix_tb_cf_transfer_codigo", "codigo", unique=True),
        Index("ix_tb_cf_transfer_tipo", "tipo_transferencia"),
        Index("ix_tb_cf_transfer_solicitante", "solicitado_por_id"),
        Index("ix_tb_cf_transfer_dest_user", "destino_usuario_id"),
        Index("ix_tb_cf_transfer_dest_location", "destino_location_id"),
        {"comment": "Processos formais de transferência de ferramentas."},
    )

    id_transfer: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    tipo_transferencia: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False)
    destino_tipo_custodia: Mapped[str] = mapped_column(String(40), nullable=False)
    destino_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    destino_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_location.id_location"), nullable=True
    )
    destino_responsavel_snapshot: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    destino_local_snapshot: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    solicitado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    origem_confirmada_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    destino_confirmado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    recusado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    cancelado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    solicitado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    origem_confirmada_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    destino_confirmado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recusado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    motivo_recusa: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    assinatura_unica_prevista: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    destino_usuario: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[destino_usuario_id]
    )
    destino_location: Mapped[LocationModel | None] = relationship("LocationModel")
    solicitado_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[solicitado_por_id]
    )
    origem_confirmada_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[origem_confirmada_por_id]
    )
    destino_confirmado_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[destino_confirmado_por_id]
    )
    recusado_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[recusado_por_id]
    )
    cancelado_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[cancelado_por_id]
    )
    itens: Mapped[list[TransferItemModel]] = relationship(
        "TransferItemModel",
        back_populates="transfer",
        cascade="save-update, merge",
        order_by="TransferItemModel.id_transfer_item",
    )


# Ferramenta participante de um processo formal de transferência
class TransferItemModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_transfer_item"
    __table_args__ = (
        Index("ix_tb_cf_transfer_item_transfer", "id_transfer"),
        Index("ix_tb_cf_transfer_item_tool", "id_tool"),
        Index("ix_tb_cf_transfer_item_status", "status"),
        {"comment": "Itens individuais de processos de transferência."},
    )

    id_transfer_item: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_transfer: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_transfer.id_transfer"), nullable=False
    )
    id_tool: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_tool.id_tool"), nullable=False
    )
    id_custody_origem: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_tool_custody.id_custody"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    status_ferramenta_anterior: Mapped[str] = mapped_column(String(40), nullable=False)
    origem_tipo_custodia: Mapped[str] = mapped_column(String(40), nullable=False)
    origem_responsavel_snapshot: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    origem_local_snapshot: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    concluido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    transfer: Mapped[TransferModel] = relationship(
        "TransferModel", back_populates="itens"
    )
    tool: Mapped[ToolModel] = relationship("ToolModel")
    custody_origem = relationship("ToolCustodyModel")
