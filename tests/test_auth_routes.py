from __future__ import annotations

from app.extensions import db
from app.users.repositories import create_user, get_user_by_email


def test_login_page_renders_dev_form(client):
    response = client.get("/auth/login")

    assert response.status_code == 200
    assert "Login de desenvolvimento ativo" in response.get_data(as_text=True)


def test_dev_login_allows_existing_active_user(app, client):
    with app.app_context():
        create_user(email="active@brasif.com.br", nome="Active User")
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={
            "email": "active@brasif.com.br",
            "nome": "Active User",
            "microsoft_oid": "oid-active",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Active User" in response.get_data(as_text=True)

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.get_json()["email"] == "active@brasif.com.br"


def test_dev_login_blocks_unknown_user(client):
    response = client.post(
        "/auth/login",
        data={
            "email": "unknown@brasif.com.br",
            "nome": "Unknown",
            "microsoft_oid": "oid-x",
        },
    )

    assert response.status_code == 200
    assert "não cadastrado" in response.get_data(as_text=True)


def test_logout_clears_session(app, client):
    with app.app_context():
        create_user(email="logout@brasif.com.br", nome="Logout User")
        db.session.commit()

    client.post(
        "/auth/login",
        data={
            "email": "logout@brasif.com.br",
            "nome": "Logout User",
            "microsoft_oid": "oid-logout",
        },
    )
    response = client.post("/auth/logout", follow_redirects=True)

    assert response.status_code == 200
    me = client.get("/auth/me", headers={"Accept": "application/json"})
    assert me.status_code == 401


def test_session_user_loader_rejects_user_deactivated_after_login(app, client):
    with app.app_context():
        create_user(email="deactivated@brasif.com.br", nome="Inactive Later")
        db.session.commit()

    client.post(
        "/auth/login",
        data={
            "email": "deactivated@brasif.com.br",
            "nome": "Inactive Later",
            "microsoft_oid": "oid-deactivated",
        },
    )

    with app.app_context():
        deactivated_user = get_user_by_email("deactivated@brasif.com.br")
        deactivated_user.ativo = False
        db.session.commit()

    response = client.get("/auth/me", headers={"Accept": "application/json"})

    assert response.status_code == 401
