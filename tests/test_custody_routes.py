from __future__ import annotations

from app.categories.services import create_category
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.locations.services import create_location
from app.permissions.services import assign_role_to_user
from app.tools.services import create_tool
from app.users.repositories import create_user


def _login(client, email: str, name: str = "Custody Admin"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def test_admin_can_open_custody_pages(app, client):
    with app.app_context():
        create_user(email="admin-custody@brasif.com.br", nome="Admin Custody")
        db.session.commit()
        assign_role_to_user("admin-custody@brasif.com.br", "admin_sistema")

    _login(client, "admin-custody@brasif.com.br", "Admin Custody")

    response = client.get("/admin/custody/")
    assert response.status_code == 200
    assert "Custódias atuais" in response.get_data(as_text=True)

    response = client.get("/admin/custody/missing")
    assert response.status_code == 200
    assert "Ferramentas ativas sem custódia" in response.get_data(as_text=True)


def test_plain_user_cannot_open_custody_pages(app, client):
    with app.app_context():
        create_user(email="plain-custody@brasif.com.br", nome="Plain Custody")
        db.session.commit()

    _login(client, "plain-custody@brasif.com.br", "Plain Custody")

    response = client.get("/admin/custody/")
    assert response.status_code == 403


def _tool_with_custody():
    category = create_category(
        {
            "codigo": "route-custody",
            "nome": "Route Custody",
            "descricao": "",
            "ativo": True,
            "controle_individual_padrao": True,
            "requer_numero_serie": False,
            "requer_calibracao": False,
            "motivo": "Cadastro inicial",
        }
    )
    location = create_location(
        {
            "codigo": "ALM-ROUTE",
            "nome": "Almoxarifado Route",
            "tipo_local": "almoxarifado",
            "filial": "Jundiaí",
            "departamento": "Serviços",
            "responsavel_nome": "Almoxarife",
            "endereco": "",
            "observacoes": "",
            "ativo": True,
            "motivo": "Cadastro inicial",
        }
    )
    db.session.commit()
    tool = create_tool(
        {
            "codigo_interno": "ROUTE-CUSTODY-001",
            "nome": "Ferramenta Route",
            "descricao": "",
            "id_categoria": category.id_categoria,
            "status": "disponivel",
            "criticidade": "media",
            "ativo_imobilizado": "",
            "numero_serie": "",
            "marca": "",
            "modelo": "",
            "controle_individual": True,
            "requer_calibracao": False,
            "ativo": True,
            "observacoes": "",
            "motivo": "Cadastro inicial",
        }
    )
    assign_initial_custody(
        tool,
        {
            "tipo_custodia": "almoxarifado",
            "id_responsavel_usuario": 0,
            "id_location": location.id_location,
            "motivo": "Entrada no almoxarifado",
        },
    )
    return tool


def test_responsavel_local_cannot_open_administrative_custody_change(app, client):
    with app.app_context():
        create_user(email="local-custody@brasif.com.br", nome="Local Custody")
        db.session.commit()
        assign_role_to_user("local-custody@brasif.com.br", "responsavel_local")
        tool = _tool_with_custody()
        tool_id = tool.id_tool

    _login(client, "local-custody@brasif.com.br", "Local Custody")

    response = client.get(f"/admin/custody/tools/{tool_id}/change")
    assert response.status_code == 403
