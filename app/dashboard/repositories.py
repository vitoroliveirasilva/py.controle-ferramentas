from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import false, func, select, true

from app.custody.models import ToolCustodyModel
from app.extensions import db
from app.inventories.models import (
    InventoryDivergenceModel,
    InventoryItemModel,
    InventoryModel,
)
from app.models.enums import (
    InventoryDivergenceStatus,
    InventoryStatus,
    OccurrenceStatus,
    ToolStatus,
    TransferStatus,
)
from app.occurrences.models import OccurrenceModel
from app.permissions.scope_filters import scoped_tool_ids
from app.tools.models import ToolModel
from app.transfers.models import TransferItemModel, TransferModel
from app.users.models import UserModel


def _now() -> datetime:
    return datetime.now(UTC)


def _tool_ids_for_user_scope(user: UserModel) -> list[int] | None:
    return scoped_tool_ids(user)


def scoped_tool_filter(user: UserModel) -> list[int] | None:
    return _tool_ids_for_user_scope(user)


def total_tools(tool_ids: list[int] | None = None) -> int:
    stmt = select(func.count(ToolModel.id_tool)).where(ToolModel.is_deleted == false())
    if tool_ids is not None:
        if not tool_ids:
            return 0
        stmt = stmt.where(ToolModel.id_tool.in_(tool_ids))
    return int(db.session.execute(stmt).scalar_one() or 0)


def active_tools_without_custody(tool_ids: list[int] | None = None) -> int:
    current_custody = (
        select(ToolCustodyModel.id_tool)
        .where(
            ToolCustodyModel.atual == true(),
            ToolCustodyModel.is_deleted == false(),
        )
        .subquery()
    )
    stmt = (
        select(func.count(ToolModel.id_tool))
        .outerjoin(current_custody, current_custody.c.id_tool == ToolModel.id_tool)
        .where(
            ToolModel.is_deleted == false(),
            ToolModel.ativo == true(),
            ToolModel.status.notin_(
                [ToolStatus.BAIXADA.value, ToolStatus.INATIVA.value]
            ),
            current_custody.c.id_tool.is_(None),
        )
    )
    if tool_ids is not None:
        if not tool_ids:
            return 0
        stmt = stmt.where(ToolModel.id_tool.in_(tool_ids))
    return int(db.session.execute(stmt).scalar_one() or 0)


def count_tools_by_status(tool_ids: list[int] | None = None) -> list[dict[str, Any]]:
    stmt = (
        select(ToolModel.status, func.count(ToolModel.id_tool))
        .where(ToolModel.is_deleted == false())
        .group_by(ToolModel.status)
        .order_by(ToolModel.status)
    )
    if tool_ids is not None:
        if not tool_ids:
            return []
        stmt = stmt.where(ToolModel.id_tool.in_(tool_ids))
    return [
        {"status": row[0], "total": int(row[1])}
        for row in db.session.execute(stmt).all()
    ]


def count_tools_by_criticality(
    tool_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    stmt = (
        select(ToolModel.criticidade, func.count(ToolModel.id_tool))
        .where(ToolModel.is_deleted == false())
        .group_by(ToolModel.criticidade)
        .order_by(ToolModel.criticidade)
    )
    if tool_ids is not None:
        if not tool_ids:
            return []
        stmt = stmt.where(ToolModel.id_tool.in_(tool_ids))
    return [
        {"criticidade": row[0], "total": int(row[1])}
        for row in db.session.execute(stmt).all()
    ]


def count_open_divergences(tool_ids: list[int] | None = None) -> int:
    stmt = select(func.count(InventoryDivergenceModel.id_inventory_divergence)).where(
        InventoryDivergenceModel.is_deleted == false(),
        InventoryDivergenceModel.status == InventoryDivergenceStatus.ABERTA.value,
    )
    if tool_ids is not None:
        if not tool_ids:
            return 0
        stmt = stmt.where(InventoryDivergenceModel.id_tool.in_(tool_ids))
    return int(db.session.execute(stmt).scalar_one() or 0)


def count_pending_transfers(tool_ids: list[int] | None = None) -> int:
    pending_statuses = [
        TransferStatus.SOLICITADA.value,
        TransferStatus.AGUARDANDO_ORIGEM.value,
        TransferStatus.AGUARDANDO_DESTINO.value,
    ]
    stmt = select(func.count(func.distinct(TransferModel.id_transfer))).where(
        TransferModel.is_deleted == false(),
        TransferModel.status.in_(pending_statuses),
    )
    if tool_ids is not None:
        if not tool_ids:
            return 0
        stmt = stmt.join(
            TransferItemModel,
            TransferItemModel.id_transfer == TransferModel.id_transfer,
        )
        stmt = stmt.where(TransferItemModel.id_tool.in_(tool_ids))
    return int(db.session.execute(stmt).scalar_one() or 0)


def count_inventories_waiting_signature(tool_ids: list[int] | None = None) -> int:
    stmt = select(func.count(func.distinct(InventoryModel.id_inventory))).where(
        InventoryModel.is_deleted == false(),
        InventoryModel.status == InventoryStatus.AGUARDANDO_ASSINATURA.value,
    )
    if tool_ids is not None:
        if not tool_ids:
            return 0
        stmt = stmt.join(
            InventoryItemModel,
            InventoryItemModel.id_inventory == InventoryModel.id_inventory,
        )
        stmt = stmt.where(InventoryItemModel.id_tool.in_(tool_ids))
    return int(db.session.execute(stmt).scalar_one() or 0)


def count_pending_inventories(tool_ids: list[int] | None = None) -> int:
    open_statuses = [
        InventoryStatus.RASCUNHO.value,
        InventoryStatus.EM_ANDAMENTO.value,
        InventoryStatus.COM_DIVERGENCIA.value,
        InventoryStatus.AGUARDANDO_ASSINATURA.value,
    ]
    stmt = select(func.count(func.distinct(InventoryModel.id_inventory))).where(
        InventoryModel.is_deleted == false(),
        InventoryModel.status.in_(open_statuses),
    )
    if tool_ids is not None:
        if not tool_ids:
            return 0
        stmt = stmt.join(
            InventoryItemModel,
            InventoryItemModel.id_inventory == InventoryModel.id_inventory,
        )
        stmt = stmt.where(InventoryItemModel.id_tool.in_(tool_ids))
    return int(db.session.execute(stmt).scalar_one() or 0)


def count_overdue_inventories(days: int = 30, tool_ids: list[int] | None = None) -> int:
    cutoff = _now() - timedelta(days=days)
    open_statuses = [
        InventoryStatus.RASCUNHO.value,
        InventoryStatus.EM_ANDAMENTO.value,
        InventoryStatus.COM_DIVERGENCIA.value,
        InventoryStatus.AGUARDANDO_ASSINATURA.value,
    ]
    stmt = select(func.count(func.distinct(InventoryModel.id_inventory))).where(
        InventoryModel.is_deleted == false(),
        InventoryModel.status.in_(open_statuses),
        InventoryModel.created_at < cutoff,
    )
    if tool_ids is not None:
        if not tool_ids:
            return 0
        stmt = stmt.join(
            InventoryItemModel,
            InventoryItemModel.id_inventory == InventoryModel.id_inventory,
        )
        stmt = stmt.where(InventoryItemModel.id_tool.in_(tool_ids))
    return int(db.session.execute(stmt).scalar_one() or 0)


def count_critical_occurrences(tool_ids: list[int] | None = None) -> int:
    critical_statuses = [
        OccurrenceStatus.ABERTA.value,
        OccurrenceStatus.EM_ANALISE.value,
        OccurrenceStatus.AGUARDANDO_APROVACAO.value,
    ]
    stmt = select(func.count(OccurrenceModel.id_occurrence)).where(
        OccurrenceModel.is_deleted == false(),
        OccurrenceModel.status.in_(critical_statuses),
    )
    if tool_ids is not None:
        if not tool_ids:
            return 0
        stmt = stmt.where(OccurrenceModel.id_tool.in_(tool_ids))
    return int(db.session.execute(stmt).scalar_one() or 0)


def count_patrimonial_events(tool_ids: list[int] | None = None) -> int:
    stmt = select(func.count(OccurrenceModel.id_occurrence)).where(
        OccurrenceModel.is_deleted == false(),
        OccurrenceModel.impacto_patrimonial == true(),
    )
    if tool_ids is not None:
        if not tool_ids:
            return 0
        stmt = stmt.where(OccurrenceModel.id_tool.in_(tool_ids))
    return int(db.session.execute(stmt).scalar_one() or 0)


def recent_open_divergences(limit: int = 8, tool_ids: list[int] | None = None):
    stmt = (
        select(InventoryDivergenceModel)
        .where(
            InventoryDivergenceModel.is_deleted == false(),
            InventoryDivergenceModel.status == InventoryDivergenceStatus.ABERTA.value,
        )
        .order_by(
            InventoryDivergenceModel.aberta_em.desc(),
            InventoryDivergenceModel.id_inventory_divergence.desc(),
        )
        .limit(limit)
    )
    if tool_ids is not None:
        if not tool_ids:
            return []
        stmt = stmt.where(InventoryDivergenceModel.id_tool.in_(tool_ids))
    return list(db.session.execute(stmt).scalars())


def pending_transfers(limit: int = 8, tool_ids: list[int] | None = None):
    pending_statuses = [
        TransferStatus.SOLICITADA.value,
        TransferStatus.AGUARDANDO_ORIGEM.value,
        TransferStatus.AGUARDANDO_DESTINO.value,
    ]
    stmt = (
        select(TransferModel)
        .where(
            TransferModel.is_deleted == false(),
            TransferModel.status.in_(pending_statuses),
        )
        .order_by(TransferModel.solicitado_em.desc(), TransferModel.id_transfer.desc())
        .limit(limit)
    )
    if tool_ids is not None:
        if not tool_ids:
            return []
        stmt = stmt.join(
            TransferItemModel,
            TransferItemModel.id_transfer == TransferModel.id_transfer,
        )
        stmt = stmt.where(TransferItemModel.id_tool.in_(tool_ids)).distinct()
    return list(db.session.execute(stmt).unique().scalars())


def pending_inventories(limit: int = 8, tool_ids: list[int] | None = None):
    pending_statuses = [
        InventoryStatus.RASCUNHO.value,
        InventoryStatus.EM_ANDAMENTO.value,
        InventoryStatus.COM_DIVERGENCIA.value,
        InventoryStatus.AGUARDANDO_ASSINATURA.value,
    ]
    stmt = (
        select(InventoryModel)
        .where(
            InventoryModel.is_deleted == false(),
            InventoryModel.status.in_(pending_statuses),
        )
        .order_by(InventoryModel.created_at.desc(), InventoryModel.id_inventory.desc())
        .limit(limit)
    )
    if tool_ids is not None:
        if not tool_ids:
            return []
        stmt = stmt.join(
            InventoryItemModel,
            InventoryItemModel.id_inventory == InventoryModel.id_inventory,
        )
        stmt = stmt.where(InventoryItemModel.id_tool.in_(tool_ids)).distinct()
    return list(db.session.execute(stmt).unique().scalars())


def top_reincidences(
    limit: int = 8, tool_ids: list[int] | None = None
) -> list[dict[str, Any]]:
    divergence_count = func.count(
        func.distinct(InventoryDivergenceModel.id_inventory_divergence)
    )
    occurrence_count = func.count(func.distinct(OccurrenceModel.id_occurrence))
    total_events = divergence_count + occurrence_count

    stmt = (
        select(
            ToolModel.codigo_interno,
            ToolModel.nome,
            divergence_count.label("divergencias"),
            occurrence_count.label("ocorrencias"),
            total_events.label("total_eventos"),
        )
        .outerjoin(
            InventoryDivergenceModel,
            (InventoryDivergenceModel.id_tool == ToolModel.id_tool)
            & (InventoryDivergenceModel.is_deleted == false()),
        )
        .outerjoin(
            OccurrenceModel,
            (OccurrenceModel.id_tool == ToolModel.id_tool)
            & (OccurrenceModel.is_deleted == false()),
        )
        .where(ToolModel.is_deleted == false())
        .group_by(ToolModel.id_tool, ToolModel.codigo_interno, ToolModel.nome)
        .having(total_events > 0)
        .order_by(total_events.desc(), ToolModel.codigo_interno)
        .limit(limit)
    )
    if tool_ids is not None:
        if not tool_ids:
            return []
        stmt = stmt.where(ToolModel.id_tool.in_(tool_ids))

    return [
        {
            "codigo_interno": row.codigo_interno,
            "nome": row.nome,
            "divergencias": int(row.divergencias or 0),
            "ocorrencias": int(row.ocorrencias or 0),
            "total_eventos": int(row.total_eventos or 0),
        }
        for row in db.session.execute(stmt).all()
    ]


def transfer_sla_buckets(tool_ids: list[int] | None = None) -> list[dict[str, Any]]:
    now = _now()
    # O SQL Server e o SQLite diferem na aritmética de datas
    # Por esse motivo os buckets são calculados em Python para garantir portabilidade
    transfers = pending_transfers(limit=100, tool_ids=tool_ids)
    buckets = {"0-2 dias": 0, "3-7 dias": 0, "+7 dias": 0}
    for transfer in transfers:
        delta = now - transfer.solicitado_em.replace(tzinfo=UTC)
        if delta.days <= 2:
            buckets["0-2 dias"] += 1
        elif delta.days <= 7:
            buckets["3-7 dias"] += 1
        else:
            buckets["+7 dias"] += 1
    return [{"faixa": key, "total": value} for key, value in buckets.items()]
