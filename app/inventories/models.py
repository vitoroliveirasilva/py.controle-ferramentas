from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.locations.models import LocationModel
from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin
from app.tools.models import ToolModel
from app.users.models import UserModel


# Processo de inventário operacional de ferramentas
class InventoryModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_inventory"
    __table_args__ = (
        Index("ix_tb_cf_inventory_codigo", "codigo", unique=True),
        Index("ix_tb_cf_inventory_status", "status"),
        Index("ix_tb_cf_inventory_tipo", "tipo_inventario"),
        Index("ix_tb_cf_inventory_scope_user", "escopo_usuario_id"),
        Index("ix_tb_cf_inventory_scope_location", "escopo_location_id"),
        {"comment": "Inventários de ferramentas por técnico ou local."},
    )

    id_inventory: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    titulo: Mapped[str] = mapped_column(String(180), nullable=False)
    tipo_inventario: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    escopo_tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    escopo_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    escopo_location_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_location.id_location"), nullable=True
    )
    escopo_responsavel_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    escopo_local_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalizado_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    motivo_finalizacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    escopo_usuario: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[escopo_usuario_id]
    )
    escopo_location: Mapped[LocationModel | None] = relationship("LocationModel")
    criado_por: Mapped[UserModel | None] = relationship("UserModel", foreign_keys=[criado_por_id])
    cancelado_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[cancelado_por_id]
    )
    finalizado_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[finalizado_por_id]
    )
    itens: Mapped[list[InventoryItemModel]] = relationship(
        "InventoryItemModel",
        back_populates="inventory",
        cascade="save-update, merge",
        order_by="InventoryItemModel.id_inventory_item",
    )
    divergencias: Mapped[list[InventoryDivergenceModel]] = relationship(
        "InventoryDivergenceModel",
        back_populates="inventory",
        cascade="save-update, merge",
        order_by="InventoryDivergenceModel.id_inventory_divergence",
    )


# Item esperado/conferido dentro de um inventário
class InventoryItemModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_inventory_item"
    __table_args__ = (
        Index("ix_tb_cf_inventory_item_inventory", "id_inventory"),
        Index("ix_tb_cf_inventory_item_tool", "id_tool"),
        Index("ix_tb_cf_inventory_item_status", "status"),
        {"comment": "Itens de conferência física de inventário."},
    )

    id_inventory_item: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_inventory: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_inventory.id_inventory"), nullable=False
    )
    id_tool: Mapped[int] = mapped_column(ForeignKey("tb_cf_tool.id_tool"), nullable=False)
    id_custody_snapshot: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_tool_custody.id_custody"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    codigo_interno_snapshot: Mapped[str] = mapped_column(String(80), nullable=False)
    ferramenta_nome_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)
    categoria_snapshot: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status_ferramenta_esperado: Mapped[str] = mapped_column(String(40), nullable=False)
    tipo_custodia_esperada: Mapped[str] = mapped_column(String(40), nullable=False)
    responsavel_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    local_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ativo_imobilizado_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True)
    numero_serie_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    conferido_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    conferido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    inventory: Mapped[InventoryModel] = relationship("InventoryModel", back_populates="itens")
    tool: Mapped[ToolModel] = relationship("ToolModel")
    conferido_por: Mapped[UserModel | None] = relationship("UserModel")
    evidencias: Mapped[list[InventoryItemEvidenceModel]] = relationship(
        "InventoryItemEvidenceModel",
        back_populates="item",
        cascade="save-update, merge",
        order_by="InventoryItemEvidenceModel.created_at.desc()",
    )
    divergencias: Mapped[list[InventoryDivergenceModel]] = relationship(
        "InventoryDivergenceModel",
        back_populates="item",
        cascade="save-update, merge",
        order_by="InventoryDivergenceModel.id_inventory_divergence",
    )


# Foto/anexo de evidência vinculado a um item de inventário
class InventoryItemEvidenceModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_inventory_item_evidence"
    __table_args__ = (
        Index("ix_tb_cf_inventory_item_ev_item", "id_inventory_item"),
        Index("ix_tb_cf_inventory_item_ev_inventory", "id_inventory"),
        Index("ix_tb_cf_inventory_item_ev_tool", "id_tool"),
        {"comment": "Evidências de conferência física dos itens de inventário."},
    )

    id_inventory_item_evidence: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_inventory_item: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_inventory_item.id_inventory_item"), nullable=False
    )
    id_inventory: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_inventory.id_inventory"), nullable=False
    )
    id_tool: Mapped[int | None] = mapped_column(ForeignKey("tb_cf_tool.id_tool"), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    item: Mapped[InventoryItemModel] = relationship(
        "InventoryItemModel", back_populates="evidencias"
    )
    inventory: Mapped[InventoryModel] = relationship("InventoryModel")
    tool: Mapped[ToolModel | None] = relationship("ToolModel")
    uploaded_by: Mapped[UserModel | None] = relationship("UserModel")


# Divergência obrigatória gerada por conferências inconsistentes
class InventoryDivergenceModel(TimestampMixin, SoftDeleteMixin, BaseModel):

    __tablename__ = "tb_cf_inventory_divergence"
    __table_args__ = (
        Index("ix_tb_cf_inventory_div_inventory", "id_inventory"),
        Index("ix_tb_cf_inventory_div_item", "id_inventory_item"),
        Index("ix_tb_cf_inventory_div_tool", "id_tool"),
        Index("ix_tb_cf_inventory_div_status", "status"),
        Index("ix_tb_cf_inventory_div_type", "tipo_divergencia"),
        Index("ix_tb_cf_inventory_div_occurrence", "id_occurrence"),
        Index("ix_tb_cf_inventory_div_transfer", "id_transfer"),
        {"comment": "Divergências de inventário que exigem ação de regularização."},
    )

    id_inventory_divergence: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    id_inventory: Mapped[int] = mapped_column(
        ForeignKey("tb_cf_inventory.id_inventory"), nullable=False
    )
    id_inventory_item: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_inventory_item.id_inventory_item"), nullable=True
    )
    id_tool: Mapped[int | None] = mapped_column(ForeignKey("tb_cf_tool.id_tool"), nullable=True)
    tipo_divergencia: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    severidade: Mapped[str] = mapped_column(String(20), nullable=False, default="media")
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    acao_regularizacao: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resolucao: Mapped[str | None] = mapped_column(Text, nullable=True)
    aberta_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    aberta_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    regularizada_por_id: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_usuario.id_usuario"), nullable=True
    )
    regularizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    id_occurrence: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_occurrence.id_occurrence"), nullable=True
    )
    id_transfer: Mapped[int | None] = mapped_column(
        ForeignKey("tb_cf_transfer.id_transfer"), nullable=True
    )

    inventory: Mapped[InventoryModel] = relationship(
        "InventoryModel", back_populates="divergencias"
    )
    item: Mapped[InventoryItemModel | None] = relationship(
        "InventoryItemModel", back_populates="divergencias"
    )
    tool: Mapped[ToolModel | None] = relationship("ToolModel")
    occurrence = relationship("OccurrenceModel")
    transfer = relationship("TransferModel")
    aberta_por: Mapped[UserModel | None] = relationship("UserModel", foreign_keys=[aberta_por_id])
    regularizada_por: Mapped[UserModel | None] = relationship(
        "UserModel", foreign_keys=[regularizada_por_id]
    )
