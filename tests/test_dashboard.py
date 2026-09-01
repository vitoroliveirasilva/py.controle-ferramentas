from __future__ import annotations

from app.categories.services import create_category
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.locations.services import create_location
from app.permissions.services import assign_role_to_user, assign_scope_to_user
from app.tools.services import create_tool
from app.users.repositories import create_user


def _login(client, email: str, name: str = "Dashboard Admin"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def _create_dashboard_fixture():
    user = create_user(email="dashboard-admin@brasif.com.br", nome="Dashboard Admin")
    category = create_category(
        {
            "codigo": "DASH-CAT",
            "nome": "Categoria Dashboard",
            "descricao": "",
            "ativo": True,
            "controle_individual_padrao": True,
            "requer_numero_serie": False,
            "requer_calibracao": False,
            "motivo": "Teste",
        }
    )
    location = create_location(
        {
            "codigo": "DASH-LOC",
            "nome": "Almoxarifado Dashboard",
            "tipo_local": "almoxarifado",
            "filial": "Jundiaí",
            "departamento": "Serviços",
            "responsavel_nome": "Almoxarife",
            "endereco": "",
            "observacoes": "",
            "ativo": True,
            "motivo": "Teste",
        }
    )
    tool = create_tool(
        {
            "codigo_interno": "DASH-001",
            "nome": "Ferramenta Dashboard",
            "descricao": "",
            "id_categoria": category.id_categoria,
            "status": "disponivel",
            "criticidade": "alta",
            "ativo_imobilizado": "AT-DASH-001",
            "numero_serie": "",
            "marca": "",
            "modelo": "",
            "controle_individual": True,
            "requer_calibracao": False,
            "ativo": True,
            "observacoes": "",
            "motivo": "Teste",
        }
    )
    assign_initial_custody(
        tool,
        {
            "tipo_custodia": "almoxarifado",
            "id_responsavel_usuario": 0,
            "id_location": location.id_location,
            "motivo": "Entrada inicial",
        },
    )
    db.session.commit()
    assign_role_to_user(user.email, "admin_sistema")
    assign_scope_to_user(user.email, "global", "*")
    return user


def test_dashboard_page_renders_for_admin(app, client):
    with app.app_context():
        user = _create_dashboard_fixture()

    _login(client, user.email, user.nome)

    response = client.get("/admin/dashboard/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Dashboard operacional" in html
    assert "Ferramentas controladas" in html
    assert "Ferramentas por status" in html


def test_dashboard_data_endpoint_returns_cards(app, client):
    with app.app_context():
        user = _create_dashboard_fixture()

    _login(client, user.email, user.nome)

    response = client.get("/admin/dashboard/data")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["scope"] == "Escopo global"
    assert any(card["title"] == "Ferramentas controladas" for card in payload["cards"])
    assert payload["tools_by_status"]
