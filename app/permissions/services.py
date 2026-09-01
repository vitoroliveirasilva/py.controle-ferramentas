from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from flask import g
from flask_login import current_user
from sqlalchemy import false, select, true

from app.extensions import db
from app.models.enums import ScopeType
from app.permissions.constants import PERMISSIONS, ROLE_DEFINITIONS
from app.permissions.models import (
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    UserRoleModel,
    UserScopeModel,
)
from app.permissions.repositories import (
    get_permission_by_code,
    get_role_by_code,
    get_role_permission,
    get_user_role,
    get_user_scope,
    list_permissions,
    list_roles,
)
from app.users.models import UserModel
from app.users.repositories import get_user_by_email


@dataclass(frozen=True)
class AccessSummary:
    roles_count: int
    permissions_count: int
    role_permissions_count: int


def normalize_scope_value(scope_value: str | None) -> str:
    value = (scope_value or "*").strip()
    return value or "*"


def validate_scope_type(scope_type: str) -> str:
    normalized = scope_type.strip().lower()
    allowed = {item.value for item in ScopeType}
    if normalized not in allowed:
        raise ValueError(
            f"Tipo de escopo inválido: {scope_type}. Válidos: {', '.join(sorted(allowed))}"
        )
    return normalized


def seed_permissions_and_roles() -> AccessSummary:
    permission_map: dict[str, PermissionModel] = {}
    for definition in PERMISSIONS:
        permission = get_permission_by_code(definition.code)
        if not permission:
            permission = PermissionModel(codigo=definition.code)
            db.session.add(permission)
        permission.nome = definition.name
        permission.grupo = definition.group
        permission.descricao = definition.description
        permission.ativo = True
        permission.sistema = True
        permission_map[definition.code] = permission

    role_map: dict[str, RoleModel] = {}
    for definition in ROLE_DEFINITIONS:
        role = get_role_by_code(definition.code)
        if not role:
            role = RoleModel(codigo=definition.code)
            db.session.add(role)
        role.nome = definition.name
        role.descricao = definition.description
        role.ativo = True
        role.sistema = True
        role_map[definition.code] = role

    db.session.flush()

    for definition in ROLE_DEFINITIONS:
        role = role_map[definition.code]
        for permission_code in definition.permissions:
            permission = permission_map[permission_code]
            if not get_role_permission(role, permission):
                db.session.add(
                    RolePermissionModel(
                        id_role=role.id_role,
                        id_permission=permission.id_permission,
                    )
                )

    db.session.commit()
    role_permissions_count = (
        db.session.execute(select(RolePermissionModel)).scalars().all()
    )
    return AccessSummary(
        roles_count=len(role_map),
        permissions_count=len(permission_map),
        role_permissions_count=len(role_permissions_count),
    )


def assign_role_to_user(email: str, role_code: str) -> UserRoleModel:
    user = get_user_by_email(email)
    if not user:
        raise ValueError(f"Usuário não encontrado: {email}")

    role = get_role_by_code(role_code)
    if not role:
        raise ValueError(
            f"Perfil não encontrado: {role_code}. Rode access-seed primeiro."
        )

    assignment = get_user_role(user, role)
    if not assignment:
        assignment = UserRoleModel(
            id_usuario=user.id_usuario, id_role=role.id_role, ativo=True
        )
        db.session.add(assignment)
    else:
        assignment.ativo = True

    db.session.commit()
    return assignment


def revoke_role_from_user(email: str, role_code: str) -> bool:
    user = get_user_by_email(email)
    role = get_role_by_code(role_code)
    if not user or not role:
        return False

    assignment = get_user_role(user, role)
    if not assignment:
        return False

    db.session.delete(assignment)
    db.session.commit()
    return True


def assign_scope_to_user(
    email: str,
    scope_type: str,
    scope_value: str | None = None,
    description: str | None = None,
) -> UserScopeModel:
    user = get_user_by_email(email)
    if not user:
        raise ValueError(f"Usuário não encontrado: {email}")

    normalized_type = validate_scope_type(scope_type)
    normalized_value = normalize_scope_value(scope_value)
    scope = get_user_scope(user, normalized_type, normalized_value)
    if not scope:
        scope = UserScopeModel(
            id_usuario=user.id_usuario,
            tipo_escopo=normalized_type,
            valor_escopo=normalized_value,
        )
        db.session.add(scope)

    scope.descricao = description
    scope.ativo = True
    scope.is_deleted = False
    scope.deleted_at = None
    db.session.commit()
    return scope


def revoke_scope_from_user(
    email: str, scope_type: str, scope_value: str | None = None
) -> bool:
    user = get_user_by_email(email)
    if not user:
        return False

    normalized_type = validate_scope_type(scope_type)
    normalized_value = normalize_scope_value(scope_value)
    scope = get_user_scope(user, normalized_type, normalized_value)
    if not scope:
        return False

    db.session.delete(scope)
    db.session.commit()
    return True


def get_user_role_codes(user: UserModel) -> set[str]:
    if not getattr(user, "is_authenticated", False):
        return set()

    rows = db.session.execute(
        select(RoleModel.codigo)
        .join(UserRoleModel, UserRoleModel.id_role == RoleModel.id_role)
        .where(
            UserRoleModel.id_usuario == user.id_usuario,
            UserRoleModel.ativo == true(),
            RoleModel.ativo == true(),
            RoleModel.is_deleted == false(),
        )
    ).all()
    return {row[0] for row in rows}


def get_user_permission_codes(user: UserModel) -> set[str]:
    if not getattr(user, "is_authenticated", False):
        return set()
    if not user.is_active:
        return set()

    cache_key = f"permissions_user_{user.id_usuario}"
    cached = getattr(g, cache_key, None)
    if cached is not None:
        return set(cached)

    rows = db.session.execute(
        select(PermissionModel.codigo)
        .join(
            RolePermissionModel,
            RolePermissionModel.id_permission == PermissionModel.id_permission,
        )
        .join(RoleModel, RoleModel.id_role == RolePermissionModel.id_role)
        .join(UserRoleModel, UserRoleModel.id_role == RoleModel.id_role)
        .where(
            UserRoleModel.id_usuario == user.id_usuario,
            UserRoleModel.ativo == true(),
            RoleModel.ativo == true(),
            RoleModel.is_deleted == false(),
            PermissionModel.ativo == true(),
            PermissionModel.is_deleted == false(),
        )
    ).all()
    permissions = {row[0] for row in rows}
    setattr(g, cache_key, permissions)
    return permissions


def has_permission(user: UserModel, permission_code: str) -> bool:
    return permission_code in get_user_permission_codes(user)


def current_user_can(permission_code: str) -> bool:
    if not getattr(current_user, "is_authenticated", False):
        return False
    return has_permission(current_user, permission_code)


def current_user_any_permission(permission_codes: Iterable[str]) -> bool:
    return any(current_user_can(permission) for permission in permission_codes)


def get_user_scopes(
    user: UserModel, scope_type: str | None = None
) -> list[UserScopeModel]:
    if not getattr(user, "is_authenticated", False):
        return []

    stmt = select(UserScopeModel).where(
        UserScopeModel.id_usuario == user.id_usuario,
        UserScopeModel.ativo == true(),
        UserScopeModel.is_deleted == false(),
    )
    if scope_type:
        stmt = stmt.where(UserScopeModel.tipo_escopo == validate_scope_type(scope_type))

    return (
        db.session.execute(
            stmt.order_by(UserScopeModel.tipo_escopo, UserScopeModel.valor_escopo)
        )
        .scalars()
        .all()
    )


def user_has_global_scope(user: UserModel) -> bool:
    return any(
        scope.tipo_escopo == ScopeType.GLOBAL.value for scope in get_user_scopes(user)
    )


def user_can_access_scope(
    user: UserModel, scope_type: str, scope_value: str | int | None
) -> bool:
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False

    normalized_type = validate_scope_type(scope_type)
    normalized_value = normalize_scope_value(
        str(scope_value) if scope_value is not None else "*"
    )

    if user_has_global_scope(user):
        return True

    if normalized_type == ScopeType.PROPRIO_USUARIO.value:
        return normalized_value in {"*", str(user.id_usuario), user.email_lower}

    for scope in get_user_scopes(user, normalized_type):
        if (
            scope.valor_escopo == "*"
            or scope.valor_escopo.lower() == normalized_value.lower()
        ):
            return True

    return False


def group_permissions_by_group() -> dict[str, list[PermissionModel]]:
    grouped: dict[str, list[PermissionModel]] = defaultdict(list)
    for permission in list_permissions():
        grouped[permission.grupo].append(permission)
    return dict(grouped)


def get_access_matrix() -> dict[str, object]:
    return {
        "roles": list_roles(),
        "permissions_by_group": group_permissions_by_group(),
    }
