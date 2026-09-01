from __future__ import annotations

from app.extensions import db
from app.permissions.services import assign_role_to_user
from app.users.repositories import create_user


def _login(client, email: str, name: str = "Access User"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def test_access_matrix_requires_permission(app, client):
    with app.app_context():
        create_user(email="plain@brasif.com.br", nome="Plain User")
        db.session.commit()

    _login(client, "plain@brasif.com.br", "Plain User")

    response = client.get("/admin/access/", follow_redirects=False)

    assert response.status_code == 403


def test_access_matrix_renders_for_admin(app, client):
    with app.app_context():
        create_user(email="admin-matrix@brasif.com.br", nome="Admin Matrix")
        db.session.commit()
        assign_role_to_user("admin-matrix@brasif.com.br", "admin_sistema")

    _login(client, "admin-matrix@brasif.com.br", "Admin Matrix")

    response = client.get("/admin/access/")

    assert response.status_code == 200
    assert "Matriz inicial de acessos" in response.get_data(as_text=True)


def test_my_access_returns_permissions_and_scopes(app, client):
    with app.app_context():
        create_user(email="manager@brasif.com.br", nome="Manager")
        db.session.commit()
        assign_role_to_user("manager@brasif.com.br", "gestor")

    _login(client, "manager@brasif.com.br", "Manager")

    response = client.get("/admin/access/me")

    assert response.status_code == 200
    payload = response.get_json()
    assert "dashboard.view" in payload["permissions"]
