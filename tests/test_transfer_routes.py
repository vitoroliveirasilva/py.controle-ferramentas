from __future__ import annotations

from app.extensions import db
from app.permissions.services import assign_role_to_user
from app.users.repositories import create_user


def _login(client, email: str, name: str = "Transfer Admin"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def test_admin_user_can_open_transfer_pages(app, client):
    with app.app_context():
        create_user(email="admin-transfer@brasif.com.br", nome="Admin Transfer")
        db.session.commit()
        assign_role_to_user("admin-transfer@brasif.com.br", "admin_sistema")

    _login(client, "admin-transfer@brasif.com.br", "Admin Transfer")

    response = client.get("/admin/transfers/")
    assert response.status_code == 200
    assert "Transferências" in response.get_data(as_text=True)

    response = client.get("/admin/transfers/create")
    assert response.status_code == 200
    assert "Nova transferência" in response.get_data(as_text=True)


def test_plain_user_cannot_open_transfer_pages(app, client):
    with app.app_context():
        create_user(email="plain-transfer@brasif.com.br", nome="Plain Transfer")
        db.session.commit()

    _login(client, "plain-transfer@brasif.com.br", "Plain Transfer")
    response = client.get("/admin/transfers/")

    assert response.status_code == 403
