from __future__ import annotations

from app.extensions import db
from app.permissions.services import assign_role_to_user
from app.users.repositories import create_user


def _login(client, email: str, name: str = "Inventory Admin"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def test_admin_user_can_open_inventory_pages(app, client):
    with app.app_context():
        create_user(email="admin-inventory@brasif.com.br", nome="Admin Inventory")
        db.session.commit()
        assign_role_to_user("admin-inventory@brasif.com.br", "admin_sistema")

    _login(client, "admin-inventory@brasif.com.br", "Admin Inventory")

    response = client.get("/admin/inventories/")
    assert response.status_code == 200
    assert "Inventários" in response.get_data(as_text=True)

    response = client.get("/admin/inventories/new")
    assert response.status_code == 200
    assert "Novo inventário" in response.get_data(as_text=True)


def test_plain_user_cannot_open_inventory_pages(app, client):
    with app.app_context():
        create_user(email="plain-inventory@brasif.com.br", nome="Plain Inventory")
        db.session.commit()

    _login(client, "plain-inventory@brasif.com.br", "Plain Inventory")
    response = client.get("/admin/inventories/")

    assert response.status_code == 403
