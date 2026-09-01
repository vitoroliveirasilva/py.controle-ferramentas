from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import Select, false, func, or_, select, true
from sqlalchemy.sql.elements import ColumnElement

from app.custody.models import ToolCustodyModel
from app.extensions import db
from app.inventories.models import (
    InventoryDivergenceModel,
    InventoryItemModel,
    InventoryModel,
)
from app.locations.models import LocationModel
from app.models.enums import InventoryScopeType, ScopeType
from app.occurrences.models import OccurrenceModel
from app.permissions.services import (
    get_user_role_codes,
    get_user_scopes,
    user_has_global_scope,
    validate_scope_type,
)
from app.tools.models import ToolModel
from app.transfers.models import TransferItemModel, TransferModel
from app.users.models import UserModel


class ScopeAccessDenied(PermissionError):
    """Erro de domínio para tentativa de acesso fora do escopo ABAC"""


def _is_authenticated_active(user: UserModel | Any) -> bool:
    return bool(
        getattr(user, "is_authenticated", False) and getattr(user, "is_active", False)
    )


def _values_by_type(user: UserModel) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for scope in get_user_scopes(user):
        grouped.setdefault(scope.tipo_escopo, set()).add(scope.valor_escopo)
    return grouped


def _normalized_values(values: Iterable[str]) -> set[str]:
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _digits(values: Iterable[str]) -> list[int]:
    return [int(value) for value in values if str(value).strip().isdigit()]


def _non_star(values: Iterable[str]) -> set[str]:
    return {
        str(value).strip() for value in values if str(value).strip() and value != "*"
    }


def is_global_scope(user: UserModel | Any) -> bool:
    if not _is_authenticated_active(user):
        return False
    return user_has_global_scope(user) or "admin_sistema" in get_user_role_codes(user)


def _user_scope_condition(
    user: UserModel,
    user_id_column: ColumnElement[int | None],
) -> ColumnElement[bool] | None:
    if is_global_scope(user):
        return None

    scopes = _values_by_type(user)
    values = scopes.get(ScopeType.PROPRIO_USUARIO.value, set()) | scopes.get(
        ScopeType.TECNICO.value, set()
    )
    conditions: list[ColumnElement[bool]] = []

    if "*" in values:
        conditions.append(user_id_column == user.id_usuario)

    explicit_ids = _digits(_non_star(values))
    if explicit_ids:
        conditions.append(user_id_column.in_(explicit_ids))

    explicit_emails = {
        value.lower()
        for value in _non_star(values)
        if "@" in value and not value.isdigit()
    }
    if explicit_emails:
        user_ids_by_email = select(UserModel.id_usuario).where(
            UserModel.is_deleted == false(),
            UserModel.ativo == true(),
            UserModel.bloqueado == false(),
            func.lower(UserModel.email_lower).in_(explicit_emails),
        )
        conditions.append(user_id_column.in_(user_ids_by_email))

    if not conditions:
        return false()
    return or_(*conditions)


def _location_scope_condition(
    user: UserModel,
    location_id_column: ColumnElement[int | None],
) -> ColumnElement[bool] | None:
    if is_global_scope(user):
        return None

    scopes = _values_by_type(user)
    local_values = scopes.get(ScopeType.LOCAL.value, set())
    filial_values = scopes.get(ScopeType.FILIAL.value, set())
    departamento_values = scopes.get(ScopeType.DEPARTAMENTO.value, set())
    conditions: list[ColumnElement[bool]] = []

    if "*" in local_values:
        conditions.append(LocationModel.id_location.is_not(None))

    location_ids = _digits(_non_star(local_values))
    if location_ids:
        conditions.append(LocationModel.id_location.in_(location_ids))

    location_codes = {
        value.lower()
        for value in _non_star(local_values)
        if not value.isdigit() and "@" not in value
    }
    if location_codes:
        conditions.append(func.lower(LocationModel.codigo).in_(location_codes))

    if "*" in filial_values:
        conditions.append(LocationModel.filial.is_not(None))
    explicit_filiais = _normalized_values(_non_star(filial_values))
    if explicit_filiais:
        conditions.append(func.lower(LocationModel.filial).in_(explicit_filiais))

    if "*" in departamento_values:
        conditions.append(LocationModel.departamento.is_not(None))
    explicit_departamentos = _normalized_values(_non_star(departamento_values))
    if explicit_departamentos:
        conditions.append(
            func.lower(LocationModel.departamento).in_(explicit_departamentos)
        )

    if not conditions:
        return false()

    location_ids_stmt = select(LocationModel.id_location).where(
        LocationModel.is_deleted == false(),
        or_(*conditions),
    )
    return location_id_column.in_(location_ids_stmt)


# Retorna filtro SQL para ferramentas acessíveis pelo escopo do usuário
# None significa acesso global/irrestrito. false() significa nenhum escopo aplicável
def tool_scope_condition(
    user: UserModel | Any,
    tool_id_column: ColumnElement[int] = ToolModel.id_tool,
) -> ColumnElement[bool] | None:
    if not _is_authenticated_active(user):
        return false()
    if is_global_scope(user):
        return None

    user_condition = _user_scope_condition(
        user, ToolCustodyModel.id_responsavel_usuario
    )
    location_condition = _location_scope_condition(user, ToolCustodyModel.id_location)

    conditions = [
        condition
        for condition in (user_condition, location_condition)
        if condition is not None
    ]
    if not conditions:
        return false()

    accessible_tools = (
        select(ToolCustodyModel.id_tool)
        .outerjoin(
            LocationModel, LocationModel.id_location == ToolCustodyModel.id_location
        )
        .where(
            ToolCustodyModel.atual == true(),
            ToolCustodyModel.is_deleted == false(),
            or_(*conditions),
        )
    )
    return tool_id_column.in_(accessible_tools)


def apply_tool_scope(
    statement: Select,
    user: UserModel | Any,
    tool_id_column: ColumnElement[int] = ToolModel.id_tool,
) -> Select:
    condition = tool_scope_condition(user, tool_id_column)
    if condition is None:
        return statement
    return statement.where(condition)


# Lista IDs de ferramentas acessíveis. None indica escopo global
def scoped_tool_ids(user: UserModel | Any) -> list[int] | None:
    condition = tool_scope_condition(user, ToolModel.id_tool)
    if condition is None:
        return None
    rows = db.session.execute(
        select(ToolModel.id_tool)
        .where(ToolModel.is_deleted == false(), condition)
        .order_by(ToolModel.id_tool)
    ).all()
    return [row[0] for row in rows]


def can_access_tool(user: UserModel | Any, tool_or_id: ToolModel | int | None) -> bool:
    if tool_or_id is None:
        return False
    if not _is_authenticated_active(user):
        return False
    if is_global_scope(user):
        return True

    tool_id = tool_or_id if isinstance(tool_or_id, int) else tool_or_id.id_tool
    condition = tool_scope_condition(user, ToolModel.id_tool)
    if condition is None:
        return True
    return bool(
        db.session.execute(
            select(ToolModel.id_tool).where(
                ToolModel.id_tool == tool_id,
                ToolModel.is_deleted == false(),
                condition,
            )
        ).first()
    )


def assert_can_access_tool(
    user: UserModel | Any, tool_or_id: ToolModel | int | None
) -> None:
    if not can_access_tool(user, tool_or_id):
        raise ScopeAccessDenied("Você não possui escopo para acessar esta ferramenta.")


def can_access_location(
    user: UserModel | Any, location_or_id: LocationModel | int | None
) -> bool:
    if location_or_id is None:
        return False
    if not _is_authenticated_active(user):
        return False
    if is_global_scope(user):
        return True

    location_id = (
        location_or_id
        if isinstance(location_or_id, int)
        else location_or_id.id_location
    )
    condition = _location_scope_condition(user, LocationModel.id_location)
    if condition is None:
        return True
    return bool(
        db.session.execute(
            select(LocationModel.id_location).where(
                LocationModel.id_location == location_id,
                LocationModel.is_deleted == false(),
                condition,
            )
        ).first()
    )


def can_access_user_scope_target(
    user: UserModel | Any, target_user_id: int | None
) -> bool:
    if not target_user_id:
        return False
    if not _is_authenticated_active(user):
        return False
    if is_global_scope(user):
        return True
    condition = _user_scope_condition(user, UserModel.id_usuario)
    if condition is None:
        return True
    return bool(
        db.session.execute(
            select(UserModel.id_usuario).where(
                UserModel.id_usuario == target_user_id,
                UserModel.is_deleted == false(),
                condition,
            )
        ).first()
    )


def assert_can_access_inventory_scope(
    user: UserModel | Any, scope: dict[str, Any]
) -> None:
    if not _is_authenticated_active(user) or is_global_scope(user):
        return

    scope_type = validate_scope_type(str(scope.get("escopo_tipo") or ""))
    if scope_type == InventoryScopeType.TECNICO.value:
        if can_access_user_scope_target(user, scope.get("escopo_usuario_id")):
            return
    elif scope_type == InventoryScopeType.LOCAL.value and can_access_location(
        user, scope.get("escopo_location_id")
    ):
        return

    raise ScopeAccessDenied("Você não possui escopo para criar inventário neste alvo.")


def inventory_scope_condition(
    user: UserModel | Any,
    inventory_id_column: ColumnElement[int] = InventoryModel.id_inventory,
) -> ColumnElement[bool] | None:
    if not _is_authenticated_active(user):
        return false()
    if is_global_scope(user):
        return None

    direct_conditions: list[ColumnElement[bool]] = []
    user_condition = _user_scope_condition(user, InventoryModel.escopo_usuario_id)
    if user_condition is not None:
        direct_conditions.append(
            (InventoryModel.escopo_tipo == InventoryScopeType.TECNICO.value)
            & user_condition
        )

    location_condition = _location_scope_condition(
        user, InventoryModel.escopo_location_id
    )
    if location_condition is not None:
        direct_conditions.append(
            (InventoryModel.escopo_tipo == InventoryScopeType.LOCAL.value)
            & location_condition
        )

    tool_condition = tool_scope_condition(user, InventoryItemModel.id_tool)
    if tool_condition is not None:
        inventory_ids_by_tool = select(InventoryItemModel.id_inventory).where(
            InventoryItemModel.is_deleted == false(),
            tool_condition,
        )
        direct_conditions.append(inventory_id_column.in_(inventory_ids_by_tool))

    if not direct_conditions:
        return false()
    return or_(*direct_conditions)


def apply_inventory_scope(
    statement: Select,
    user: UserModel | Any,
    inventory_id_column: ColumnElement[int] = InventoryModel.id_inventory,
) -> Select:
    condition = inventory_scope_condition(user, inventory_id_column)
    if condition is None:
        return statement
    return statement.where(condition)


def can_access_inventory(
    user: UserModel | Any,
    inventory_or_id: InventoryModel | int | None,
) -> bool:
    if inventory_or_id is None:
        return False
    if not _is_authenticated_active(user):
        return False
    if is_global_scope(user):
        return True

    inventory_id = (
        inventory_or_id
        if isinstance(inventory_or_id, int)
        else inventory_or_id.id_inventory
    )
    condition = inventory_scope_condition(user, InventoryModel.id_inventory)
    if condition is None:
        return True
    return bool(
        db.session.execute(
            select(InventoryModel.id_inventory).where(
                InventoryModel.id_inventory == inventory_id,
                InventoryModel.is_deleted == false(),
                condition,
            )
        ).first()
    )


def assert_can_access_inventory(
    user: UserModel | Any,
    inventory_or_id: InventoryModel | int | None,
) -> None:
    if not can_access_inventory(user, inventory_or_id):
        raise ScopeAccessDenied("Você não possui escopo para acessar este inventário.")


def transfer_scope_condition(
    user: UserModel | Any,
    transfer_id_column: ColumnElement[int] = TransferModel.id_transfer,
) -> ColumnElement[bool] | None:
    if not _is_authenticated_active(user):
        return false()
    if is_global_scope(user):
        return None

    conditions: list[ColumnElement[bool]] = [
        TransferModel.solicitado_por_id == user.id_usuario
    ]

    tool_condition = tool_scope_condition(user, TransferItemModel.id_tool)
    if tool_condition is not None:
        transfer_ids_by_tool = select(TransferItemModel.id_transfer).where(
            TransferItemModel.is_deleted == false(),
            tool_condition,
        )
        conditions.append(transfer_id_column.in_(transfer_ids_by_tool))

    destination_user_condition = _user_scope_condition(
        user, TransferModel.destino_usuario_id
    )
    if destination_user_condition is not None:
        conditions.append(destination_user_condition)

    destination_location_condition = _location_scope_condition(
        user,
        TransferModel.destino_location_id,
    )
    if destination_location_condition is not None:
        conditions.append(destination_location_condition)

    return or_(*conditions) if conditions else false()


def apply_transfer_scope(
    statement: Select,
    user: UserModel | Any,
    transfer_id_column: ColumnElement[int] = TransferModel.id_transfer,
) -> Select:
    condition = transfer_scope_condition(user, transfer_id_column)
    if condition is None:
        return statement
    return statement.where(condition)


def can_access_transfer(
    user: UserModel | Any, transfer_or_id: TransferModel | int | None
) -> bool:
    if transfer_or_id is None:
        return False
    if not _is_authenticated_active(user):
        return False
    if is_global_scope(user):
        return True

    transfer_id = (
        transfer_or_id
        if isinstance(transfer_or_id, int)
        else transfer_or_id.id_transfer
    )
    condition = transfer_scope_condition(user, TransferModel.id_transfer)
    if condition is None:
        return True
    return bool(
        db.session.execute(
            select(TransferModel.id_transfer).where(
                TransferModel.id_transfer == transfer_id,
                TransferModel.is_deleted == false(),
                condition,
            )
        ).first()
    )


def assert_can_access_transfer(
    user: UserModel | Any,
    transfer_or_id: TransferModel | int | None,
) -> None:
    if not can_access_transfer(user, transfer_or_id):
        raise ScopeAccessDenied(
            "Você não possui escopo para acessar esta transferência."
        )


def occurrence_scope_condition(
    user: UserModel | Any,
    occurrence_id_column: ColumnElement[int] = OccurrenceModel.id_occurrence,
) -> ColumnElement[bool] | None:
    if not _is_authenticated_active(user):
        return false()
    if is_global_scope(user):
        return None

    tool_condition = tool_scope_condition(user, OccurrenceModel.id_tool)
    if tool_condition is None:
        return None
    return tool_condition


def apply_occurrence_scope(
    statement: Select,
    user: UserModel | Any,
) -> Select:
    condition = occurrence_scope_condition(user)
    if condition is None:
        return statement
    return statement.where(condition)


def can_access_occurrence(
    user: UserModel | Any,
    occurrence_or_id: OccurrenceModel | int | None,
) -> bool:
    if occurrence_or_id is None:
        return False
    if not _is_authenticated_active(user):
        return False
    if is_global_scope(user):
        return True

    occurrence_id = (
        occurrence_or_id
        if isinstance(occurrence_or_id, int)
        else occurrence_or_id.id_occurrence
    )
    condition = occurrence_scope_condition(user, OccurrenceModel.id_occurrence)
    if condition is None:
        return True
    return bool(
        db.session.execute(
            select(OccurrenceModel.id_occurrence).where(
                OccurrenceModel.id_occurrence == occurrence_id,
                OccurrenceModel.is_deleted == false(),
                condition,
            )
        ).first()
    )


def assert_can_access_occurrence(
    user: UserModel | Any,
    occurrence_or_id: OccurrenceModel | int | None,
) -> None:
    if not can_access_occurrence(user, occurrence_or_id):
        raise ScopeAccessDenied("Você não possui escopo para acessar esta ocorrência.")


def divergence_scope_condition(
    user: UserModel | Any,
    divergence_id_column: ColumnElement[
        int
    ] = InventoryDivergenceModel.id_inventory_divergence,
) -> ColumnElement[bool] | None:
    if not _is_authenticated_active(user):
        return false()
    if is_global_scope(user):
        return None

    conditions: list[ColumnElement[bool]] = []
    tool_condition = tool_scope_condition(user, InventoryDivergenceModel.id_tool)
    if tool_condition is not None:
        conditions.append(tool_condition)

    inventory_condition = inventory_scope_condition(user, InventoryModel.id_inventory)
    if inventory_condition is not None:
        scoped_inventory_ids = select(InventoryModel.id_inventory).where(
            InventoryModel.is_deleted == false(),
            inventory_condition,
        )
        conditions.append(
            InventoryDivergenceModel.id_inventory.in_(scoped_inventory_ids)
        )

    if not conditions:
        return false()
    return or_(*conditions)


def apply_divergence_scope(statement: Select, user: UserModel | Any) -> Select:
    condition = divergence_scope_condition(user)
    if condition is None:
        return statement
    return statement.where(condition)


def assert_scope(condition: bool, message: str) -> None:
    if not condition:
        raise ScopeAccessDenied(message)
