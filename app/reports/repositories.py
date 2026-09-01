from __future__ import annotations

from sqlalchemy import Select, false, or_, select, true
from sqlalchemy.orm import joinedload

from app.audit.models import AuditLogModel
from app.custody.models import ToolCustodyModel, ToolTimelineEventModel
from app.extensions import db
from app.inventories.models import (
    InventoryDivergenceModel,
    InventoryModel,
)
from app.occurrences.models import OccurrenceModel
from app.permissions.scope_filters import (
    apply_divergence_scope,
    apply_inventory_scope,
    apply_occurrence_scope,
    apply_tool_scope,
    apply_transfer_scope,
    can_access_tool,
)
from app.tools.models import ToolModel
from app.transfers.models import TransferItemModel, TransferModel
from app.users.models import UserModel

DEFAULT_LIMIT = 500


def _like(value: str) -> str:
    return f"%{value.strip()}%"


def current_situation_statement(
    search: str | None = None,
    status: str | None = None,
    category_id: int | None = None,
    *,
    user: UserModel | None = None,
) -> Select:
    stmt = (
        select(ToolModel, ToolCustodyModel)
        .outerjoin(
            ToolCustodyModel,
            (ToolCustodyModel.id_tool == ToolModel.id_tool)
            & (ToolCustodyModel.atual == true())
            & (ToolCustodyModel.is_deleted == false()),
        )
        .options(joinedload(ToolModel.categoria))
        .where(ToolModel.is_deleted == false())
        .order_by(ToolModel.codigo_interno)
    )
    if user is not None:
        stmt = apply_tool_scope(stmt, user, ToolModel.id_tool)
    if search:
        like = _like(search)
        stmt = stmt.where(
            or_(
                ToolModel.codigo_interno.ilike(like),
                ToolModel.nome.ilike(like),
                ToolModel.ativo_imobilizado.ilike(like),
                ToolModel.numero_serie.ilike(like),
                ToolCustodyModel.responsavel_snapshot.ilike(like),
                ToolCustodyModel.local_snapshot.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(ToolModel.status == status)
    if category_id:
        stmt = stmt.where(ToolModel.id_categoria == category_id)
    return stmt


def fetch_current_situation(
    search: str | None = None,
    status: str | None = None,
    category_id: int | None = None,
    limit: int = DEFAULT_LIMIT,
    *,
    user: UserModel | None = None,
) -> list[tuple[ToolModel, ToolCustodyModel | None]]:
    return list(
        db.session.execute(
            current_situation_statement(search, status, category_id, user=user).limit(
                limit
            )
        )
        .unique()
        .all()
    )


def inventory_statement(
    status: str | None = None,
    inventory_type: str | None = None,
    *,
    user: UserModel | None = None,
) -> Select:
    stmt = (
        select(InventoryModel)
        .options(
            joinedload(InventoryModel.escopo_usuario),
            joinedload(InventoryModel.escopo_location),
            joinedload(InventoryModel.criado_por),
        )
        .where(InventoryModel.is_deleted == false())
        .order_by(InventoryModel.created_at.desc(), InventoryModel.id_inventory.desc())
    )
    if user is not None:
        stmt = apply_inventory_scope(stmt, user, InventoryModel.id_inventory)
    if status:
        stmt = stmt.where(InventoryModel.status == status)
    if inventory_type:
        stmt = stmt.where(InventoryModel.tipo_inventario == inventory_type)
    return stmt


def fetch_inventories(
    status: str | None = None,
    inventory_type: str | None = None,
    limit: int = DEFAULT_LIMIT,
    *,
    user: UserModel | None = None,
) -> list[InventoryModel]:
    statement = inventory_statement(status, inventory_type, user=user).limit(limit)
    return list(db.session.execute(statement).unique().scalars())


def divergence_statement(
    status: str | None = None, *, user: UserModel | None = None
) -> Select:
    stmt = (
        select(InventoryDivergenceModel)
        .options(
            joinedload(InventoryDivergenceModel.inventory),
            joinedload(InventoryDivergenceModel.item),
            joinedload(InventoryDivergenceModel.tool),
        )
        .where(InventoryDivergenceModel.is_deleted == false())
        .order_by(
            InventoryDivergenceModel.status,
            InventoryDivergenceModel.created_at.desc(),
            InventoryDivergenceModel.id_inventory_divergence.desc(),
        )
    )
    if user is not None:
        stmt = apply_divergence_scope(stmt, user)
    if status:
        stmt = stmt.where(InventoryDivergenceModel.status == status)
    return stmt


def fetch_divergences(
    status: str | None = None,
    limit: int = DEFAULT_LIMIT,
    *,
    user: UserModel | None = None,
) -> list[InventoryDivergenceModel]:
    return list(
        db.session.execute(
            divergence_statement(status, user=user).limit(limit)
        ).scalars()
    )


def transfer_statement(
    status: str | None = None, *, user: UserModel | None = None
) -> Select:
    stmt = (
        select(TransferModel)
        .options(
            joinedload(TransferModel.destino_usuario),
            joinedload(TransferModel.destino_location),
            joinedload(TransferModel.itens).joinedload(TransferItemModel.tool),
        )
        .where(TransferModel.is_deleted == false())
        .order_by(TransferModel.solicitado_em.desc(), TransferModel.id_transfer.desc())
    )
    if user is not None:
        stmt = apply_transfer_scope(stmt, user, TransferModel.id_transfer)
    if status:
        stmt = stmt.where(TransferModel.status == status)
    return stmt


def fetch_transfers(
    status: str | None = None,
    limit: int = DEFAULT_LIMIT,
    *,
    user: UserModel | None = None,
) -> list[TransferModel]:
    statement = transfer_statement(status, user=user).limit(limit)
    return list(db.session.execute(statement).unique().scalars())


def occurrence_statement(
    status: str | None = None,
    occurrence_type: str | None = None,
    *,
    user: UserModel | None = None,
) -> Select:
    stmt = (
        select(OccurrenceModel)
        .options(
            joinedload(OccurrenceModel.tool), joinedload(OccurrenceModel.registrante)
        )
        .where(OccurrenceModel.is_deleted == false())
        .order_by(
            OccurrenceModel.registrado_em.desc(), OccurrenceModel.id_occurrence.desc()
        )
    )
    if user is not None:
        stmt = apply_occurrence_scope(stmt, user)
    if status:
        stmt = stmt.where(OccurrenceModel.status == status)
    if occurrence_type:
        stmt = stmt.where(OccurrenceModel.tipo_ocorrencia == occurrence_type)
    return stmt


def fetch_occurrences(
    status: str | None = None,
    occurrence_type: str | None = None,
    limit: int = DEFAULT_LIMIT,
    *,
    user: UserModel | None = None,
) -> list[OccurrenceModel]:
    statement = occurrence_statement(status, occurrence_type, user=user).limit(limit)
    return list(db.session.execute(statement).scalars())


def fetch_asset_tools(
    limit: int = DEFAULT_LIMIT,
    *,
    user: UserModel | None = None,
) -> list[tuple[ToolModel, ToolCustodyModel | None]]:
    return fetch_current_situation(
        search=None,
        status=None,
        category_id=None,
        limit=limit,
        user=user,
    )


def fetch_tool_history(
    tool_id: int, limit: int = DEFAULT_LIMIT
) -> list[ToolTimelineEventModel]:
    return list(
        db.session.execute(
            select(ToolTimelineEventModel)
            .options(joinedload(ToolTimelineEventModel.actor))
            .where(ToolTimelineEventModel.id_tool == tool_id)
            .order_by(
                ToolTimelineEventModel.occurred_at.desc(),
                ToolTimelineEventModel.id_event.desc(),
            )
            .limit(limit)
        ).scalars()
    )


def fetch_audit_for_tool(tool_id: int, limit: int = 100) -> list[AuditLogModel]:
    return list(
        db.session.execute(
            select(AuditLogModel)
            .where(
                AuditLogModel.entidade.in_(
                    [
                        "tool",
                        "tool_custody",
                        "transfer",
                        "inventory",
                        "inventory_divergence",
                        "occurrence",
                    ]
                )
            )
            .order_by(
                AuditLogModel.occurred_at.desc(), AuditLogModel.id_audit_log.desc()
            )
            .limit(limit)
        ).scalars()
    )


def find_tool_for_history(
    query: str | None, *, user: UserModel | None = None
) -> ToolModel | None:
    if not query:
        return None
    cleaned = query.strip()
    if cleaned.isdigit():
        tool = db.session.get(ToolModel, int(cleaned))
        if tool and (user is None or can_access_tool(user, tool)):
            return tool
    stmt = select(ToolModel).where(
        ToolModel.is_deleted == false(),
        or_(
            ToolModel.codigo_interno == cleaned.upper(),
            ToolModel.ativo_imobilizado == cleaned.upper(),
            ToolModel.numero_serie == cleaned.upper(),
            ToolModel.nome.ilike(_like(cleaned)),
        ),
    )
    if user is not None:
        stmt = apply_tool_scope(stmt, user, ToolModel.id_tool)
    return db.session.execute(stmt).scalar_one_or_none()
