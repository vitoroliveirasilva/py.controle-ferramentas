from __future__ import annotations

from app.categories.services import create_category
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.locations.services import create_location
from app.permissions.services import assign_role_to_user
from app.reports.services import build_report_rows
from app.tools.services import create_tool
from app.users.repositories import create_user


def _login(client, email: str, name: str = "Reports Admin"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def _create_report_fixture():
    user = create_user(email="reports-admin@brasif.com.br", nome="Reports Admin")
    category = create_category(
        {
            "codigo": "REL-CAT",
            "nome": "Categoria Relatório",
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
            "codigo": "REL-LOC",
            "nome": "Almoxarifado Relatório",
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
            "codigo_interno": "REL-001",
            "nome": "Ferramenta Relatório",
            "descricao": "",
            "id_categoria": category.id_categoria,
            "status": "disponivel",
            "criticidade": "patrimonial",
            "ativo_imobilizado": "AT-REL-001",
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
    return user, tool


def test_current_situation_report_returns_tools(app):
    with app.app_context():
        _user, _tool = _create_report_fixture()

        definition, rows = build_report_rows("situacao-atual", {"q": "REL-001"})

        assert definition.code == "situacao-atual"
        assert rows
        assert rows[0]["codigo_interno"] == "REL-001"
        assert rows[0]["custodia_atual"] != ""


def test_admin_can_open_reports_and_export_csv(app, client):
    with app.app_context():
        user, _tool = _create_report_fixture()

    _login(client, user.email, user.nome)

    response = client.get("/admin/reports/")
    assert response.status_code == 200
    assert "Relatórios" in response.get_data(as_text=True)

    response = client.get("/admin/reports/situacao-atual?q=REL-001")
    assert response.status_code == 200
    assert "REL-001" in response.get_data(as_text=True)

    response = client.get("/admin/reports/situacao-atual/export/csv?q=REL-001")
    assert response.status_code == 200
    assert response.mimetype.startswith("text/csv")
    assert "REL-001" in response.get_data(as_text=True)
