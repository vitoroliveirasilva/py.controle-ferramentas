from __future__ import annotations

from sqlalchemy import select

from app.extensions import db
from app.permissions.models import (
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    UserRoleModel,
    UserScopeModel,
)
from app.users.models import UserModel


def get_permission_by_code(code: str) -> PermissionModel | None:
    return db.session.execute(
        select(PermissionModel).where(PermissionModel.codigo == code)
    ).scalar_one_or_none()


def get_role_by_code(code: str) -> RoleModel | None:
    return db.session.execute(
        select(RoleModel).where(RoleModel.codigo == code)
    ).scalar_one_or_none()


def list_roles() -> list[RoleModel]:
    return (
        db.session.execute(select(RoleModel).order_by(RoleModel.nome)).scalars().all()
    )


def list_permissions() -> list[PermissionModel]:
    return (
        db.session.execute(
            select(PermissionModel).order_by(
                PermissionModel.grupo, PermissionModel.codigo
            )
        )
        .scalars()
        .all()
    )


def get_user_role(user: UserModel, role: RoleModel) -> UserRoleModel | None:
    return db.session.execute(
        select(UserRoleModel).where(
            UserRoleModel.id_usuario == user.id_usuario,
            UserRoleModel.id_role == role.id_role,
        )
    ).scalar_one_or_none()


def get_role_permission(
    role: RoleModel, permission: PermissionModel
) -> RolePermissionModel | None:
    return db.session.execute(
        select(RolePermissionModel).where(
            RolePermissionModel.id_role == role.id_role,
            RolePermissionModel.id_permission == permission.id_permission,
        )
    ).scalar_one_or_none()


def get_user_scope(
    user: UserModel,
    scope_type: str,
    scope_value: str,
) -> UserScopeModel | None:
    return db.session.execute(
        select(UserScopeModel).where(
            UserScopeModel.id_usuario == user.id_usuario,
            UserScopeModel.tipo_escopo == scope_type,
            UserScopeModel.valor_escopo == scope_value,
        )
    ).scalar_one_or_none()
