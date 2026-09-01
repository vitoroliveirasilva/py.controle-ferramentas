from __future__ import annotations

from sqlalchemy import Select, false, func, or_, select, true
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.inventories.models import (
    InventoryDivergenceModel,
    InventoryItemModel,
    InventoryModel,
)
from app.models.enums import InventoryDivergenceStatus
from app.permissions.scope_filters import apply_inventory_scope
from app.tools.models import ToolModel
from app.users.models import UserModel

OPEN_DIVERGENCE_STATUSES = (InventoryDivergenceStatus.ABERTA.value,)


def get_inventory_by_id(inventory_id: int) -> InventoryModel | None:
    return db.session.get(InventoryModel, inventory_id)


def get_inventory_with_items(inventory_id: int) -> InventoryModel | None:
    return db.session.execute(
        select(InventoryModel)
        .options(
            selectinload(InventoryModel.itens).joinedload(InventoryItemModel.tool),
            selectinload(InventoryModel.divergencias).joinedload(
                InventoryDivergenceModel.item
            ),
            selectinload(InventoryModel.divergencias).joinedload(
                InventoryDivergenceModel.tool
            ),
            joinedload(InventoryModel.escopo_usuario),
            joinedload(InventoryModel.escopo_location),
        )
        .where(
            InventoryModel.id_inventory == inventory_id,
            InventoryModel.is_deleted == false(),
        )
    ).scalar_one_or_none()


def get_inventory_item_by_id(item_id: int) -> InventoryItemModel | None:
    return db.session.get(InventoryItemModel, item_id)


def get_inventory_divergence_by_id(
    divergence_id: int,
) -> InventoryDivergenceModel | None:
    return db.session.get(InventoryDivergenceModel, divergence_id)


def base_inventory_query(
    search: str | None = None,
    status: str | None = None,
    *,
    user: UserModel | None = None,
) -> Select:
    stmt = (
        select(InventoryModel)
        .options(
            joinedload(InventoryModel.escopo_usuario),
            joinedload(InventoryModel.escopo_location),
        )
        .where(InventoryModel.is_deleted == false())
    )
    if user is not None:
        stmt = apply_inventory_scope(stmt, user, InventoryModel.id_inventory)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                InventoryModel.codigo.ilike(like),
                InventoryModel.titulo.ilike(like),
                InventoryModel.escopo_responsavel_snapshot.ilike(like),
                InventoryModel.escopo_local_snapshot.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(InventoryModel.status == status)
    return stmt.order_by(
        InventoryModel.created_at.desc(), InventoryModel.id_inventory.desc()
    )


def list_inventory_items(inventory_id: int) -> list[InventoryItemModel]:
    return list(
        db.session.execute(
            select(InventoryItemModel)
            .options(joinedload(InventoryItemModel.tool))
            .where(
                InventoryItemModel.id_inventory == inventory_id,
                InventoryItemModel.is_deleted == false(),
            )
            .order_by(
                InventoryItemModel.status,
                InventoryItemModel.codigo_interno_snapshot,
            )
        )
        .unique()
        .scalars()
    )


def list_inventory_divergences(inventory_id: int) -> list[InventoryDivergenceModel]:
    return list(
        db.session.execute(
            select(InventoryDivergenceModel)
            .options(
                joinedload(InventoryDivergenceModel.item),
                joinedload(InventoryDivergenceModel.tool),
                joinedload(InventoryDivergenceModel.occurrence),
                joinedload(InventoryDivergenceModel.transfer),
            )
            .where(
                InventoryDivergenceModel.id_inventory == inventory_id,
                InventoryDivergenceModel.is_deleted == false(),
            )
            .order_by(
                InventoryDivergenceModel.status,
                InventoryDivergenceModel.tipo_divergencia,
                InventoryDivergenceModel.id_inventory_divergence,
            )
        )
        .unique()
        .scalars()
    )


def list_open_inventory_divergences(
    inventory_id: int,
) -> list[InventoryDivergenceModel]:
    return list(
        db.session.execute(
            select(InventoryDivergenceModel)
            .where(
                InventoryDivergenceModel.id_inventory == inventory_id,
                InventoryDivergenceModel.status.in_(OPEN_DIVERGENCE_STATUSES),
                InventoryDivergenceModel.is_deleted == false(),
            )
            .order_by(InventoryDivergenceModel.id_inventory_divergence)
        ).scalars()
    )


def find_open_item_divergence(
    item: InventoryItemModel,
    divergence_type: str,
) -> InventoryDivergenceModel | None:
    return db.session.execute(
        select(InventoryDivergenceModel).where(
            InventoryDivergenceModel.id_inventory_item == item.id_inventory_item,
            InventoryDivergenceModel.tipo_divergencia == divergence_type,
            InventoryDivergenceModel.status.in_(OPEN_DIVERGENCE_STATUSES),
            InventoryDivergenceModel.is_deleted == false(),
        )
    ).scalar_one_or_none()


def count_open_inventory_divergences(inventory_id: int) -> int:
    return int(
        db.session.execute(
            select(func.count(InventoryDivergenceModel.id_inventory_divergence)).where(
                InventoryDivergenceModel.id_inventory == inventory_id,
                InventoryDivergenceModel.status.in_(OPEN_DIVERGENCE_STATUSES),
                InventoryDivergenceModel.is_deleted == false(),
            )
        ).scalar_one()
    )


def has_pending_inventory_items(inventory_id: int) -> bool:
    return bool(
        db.session.execute(
            select(InventoryItemModel.id_inventory_item).where(
                InventoryItemModel.id_inventory == inventory_id,
                InventoryItemModel.status == "pendente",
                InventoryItemModel.is_deleted == false(),
            )
        ).first()
    )


def count_open_inventories_for_tool(tool_id: int) -> int:
    return int(
        db.session.execute(
            select(func.count(InventoryItemModel.id_inventory_item))
            .join(
                InventoryModel,
                InventoryModel.id_inventory == InventoryItemModel.id_inventory,
            )
            .where(
                InventoryItemModel.id_tool == tool_id,
                InventoryItemModel.is_deleted == false(),
                InventoryModel.is_deleted == false(),
                InventoryModel.status.in_(
                    (
                        "rascunho",
                        "em_andamento",
                        "com_divergencia",
                        "aguardando_assinatura",
                    )
                ),
            )
        ).scalar_one()
    )


def inventory_has_open_divergence(inventory: InventoryModel) -> bool:
    return any(
        divergence.status == InventoryDivergenceStatus.ABERTA.value
        and divergence.is_deleted == false()
        for divergence in inventory.divergencias
    )


def mark_all_inventory_tools_as_available(inventory: InventoryModel) -> None:
    for item in inventory.itens:
        if item.tool and item.tool.ativo == true():
            item.tool.status = item.status_ferramenta_esperado


def get_inventory_item_evidence_by_id(evidence_id: int):
    from app.inventories.models import InventoryItemEvidenceModel

    return db.session.get(InventoryItemEvidenceModel, evidence_id)


def find_inventory_item_by_identifier(
    inventory: InventoryModel,
    identifier: str | None,
) -> InventoryItemModel | None:
    normalized = (identifier or "").strip().upper()
    if not normalized:
        return None
    return db.session.execute(
        select(InventoryItemModel)
        .join(
            InventoryModel,
            InventoryModel.id_inventory == InventoryItemModel.id_inventory,
        )
        .join(InventoryItemModel.tool)
        .where(
            InventoryItemModel.id_inventory == inventory.id_inventory,
            InventoryItemModel.is_deleted == false(),
            or_(
                InventoryItemModel.codigo_interno_snapshot == normalized,
                InventoryItemModel.ativo_imobilizado_snapshot == normalized,
                InventoryItemModel.numero_serie_snapshot == normalized,
                ToolModel.codigo_interno == normalized,
                ToolModel.ativo_imobilizado == normalized,
                ToolModel.numero_serie == normalized,
            ),
        )
    ).scalar_one_or_none()
