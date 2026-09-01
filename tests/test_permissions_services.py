from __future__ import annotations

from app.extensions import db
from app.permissions.repositories import get_role_by_code
from app.permissions.services import (
    assign_role_to_user,
    assign_scope_to_user,
    get_user_permission_codes,
    seed_permissions_and_roles,
    user_can_access_scope,
)
from app.users.repositories import create_user


def test_seed_creates_roles_and_permissions(app):
    with app.app_context():
        summary = seed_permissions_and_roles()

    assert summary.roles_count >= 7
    assert summary.permissions_count >= 40
    assert get_role_by_code("admin_sistema") is not None


def test_assign_role_grants_permissions(app):
    with app.app_context():
        user = create_user(email="admin@brasif.com.br", nome="Admin")
        db.session.commit()

        assign_role_to_user("admin@brasif.com.br", "admin_sistema")
        permissions = get_user_permission_codes(user)

    assert "permissions.manage" in permissions
    assert "tools.view" in permissions


def test_scope_helper_allows_exact_scope(app):
    with app.app_context():
        user = create_user(email="scope@brasif.com.br", nome="Scope User")
        db.session.commit()
        assign_scope_to_user("scope@brasif.com.br", "filial", "jundiai")

        allowed = user_can_access_scope(user, "filial", "jundiai")
        denied = user_can_access_scope(user, "filial", "serra")

    assert allowed is True
    assert denied is False


def test_global_scope_allows_any_scope(app):
    with app.app_context():
        user = create_user(email="global@brasif.com.br", nome="Global User")
        db.session.commit()
        assign_scope_to_user("global@brasif.com.br", "global", "*")

        allowed = user_can_access_scope(user, "local", "oficina-01")

    assert allowed is True
