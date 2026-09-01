from __future__ import annotations

from app.extensions import db
from app.permissions.services import assign_role_to_user
from app.users.repositories import create_user


def _login(client, email: str, name: str = "Admin User"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def test_admin_user_can_open_catalog_pages(app, client):
    with app.app_context():
        create_user(email="admin-catalog@brasif.com.br", nome="Admin Catalog")
        db.session.commit()
        assign_role_to_user("admin-catalog@brasif.com.br", "admin_sistema")

    _login(client, "admin-catalog@brasif.com.br", "Admin Catalog")

    for path, expected in (
        ("/admin/users/", "Usuários locais"),
        ("/admin/categories/", "Categorias de ferramentas"),
        ("/admin/locations/", "Locais"),
        ("/admin/tools/", "Ferramentas"),
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert expected in response.get_data(as_text=True)


def test_plain_user_cannot_open_categories(app, client):
    with app.app_context():
        create_user(email="plain-catalog@brasif.com.br", nome="Plain Catalog")
        db.session.commit()

    _login(client, "plain-catalog@brasif.com.br", "Plain Catalog")
    response = client.get("/admin/categories/")

    assert response.status_code == 403
