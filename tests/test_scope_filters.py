from __future__ import annotations

from app.categories.services import create_category
from app.custody.repositories import base_current_custody_query
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.locations.services import create_location
from app.permissions.scope_filters import can_access_tool, scoped_tool_ids
from app.permissions.services import assign_role_to_user, assign_scope_to_user
from app.reports.services import build_report_rows
from app.tools.repositories import base_tool_query, get_tool_by_any_identifier
from app.tools.services import create_tool
from app.users.repositories import create_user


def _login(client, email: str, name: str = "Scoped User"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def _create_tool_with_location(*, code: str, location_code: str, filial: str):
    category = create_category(
        {
            "codigo": f"CAT-{code}",
            "nome": f"Categoria {code}",
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
            "codigo": location_code,
            "nome": f"Local {location_code}",
            "tipo_local": "almoxarifado",
            "filial": filial,
            "departamento": "Serviços",
            "responsavel_nome": "Responsável",
            "endereco": "",
            "observacoes": "",
            "ativo": True,
            "motivo": "Teste",
        }
    )
    tool = create_tool(
        {
            "codigo_interno": code,
            "nome": f"Ferramenta {code}",
            "descricao": "",
            "id_categoria": category.id_categoria,
            "status": "disponivel",
            "criticidade": "patrimonial",
            "ativo_imobilizado": f"AT-{code}",
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
    return tool, location


def _scoped_fixture():
    user = create_user(email="scoped.local@brasif.com.br", nome="Usuário Escopado")
    db.session.flush()
    tool_allowed, location_allowed = _create_tool_with_location(
        code="SCOPE-A", location_code="LOC-A", filial="Jundiaí"
    )
    tool_blocked, _location_blocked = _create_tool_with_location(
        code="SCOPE-B", location_code="LOC-B", filial="Sorocaba"
    )
    assign_role_to_user(user.email, "responsavel_local")
    assign_scope_to_user(user.email, "local", str(location_allowed.id_location))
    db.session.refresh(user)
    db.session.refresh(tool_allowed)
    db.session.refresh(tool_blocked)
    return user, tool_allowed, tool_blocked


def test_scoped_tool_helpers_return_only_tools_in_user_scope(app):
    with app.app_context():
        user, tool_allowed, tool_blocked = _scoped_fixture()

        assert can_access_tool(user, tool_allowed) is True
        assert can_access_tool(user, tool_blocked) is False
        assert scoped_tool_ids(user) == [tool_allowed.id_tool]

        rows = db.session.execute(base_tool_query(user=user)).scalars().all()
        assert [tool.codigo_interno for tool in rows] == ["SCOPE-A"]

        custody_rows = (
            db.session.execute(base_current_custody_query(user=user)).scalars().all()
        )
        assert [custody.id_tool for custody in custody_rows] == [tool_allowed.id_tool]

        assert get_tool_by_any_identifier("SCOPE-A", user=user) == tool_allowed
        assert get_tool_by_any_identifier("SCOPE-B", user=user) is None


def test_tools_index_hides_tools_outside_scope(app, client):
    with app.app_context():
        user, _tool_allowed, _tool_blocked = _scoped_fixture()

    _login(client, user.email, user.nome)

    response = client.get("/admin/tools/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "SCOPE-A" in body
    assert "Categoria SCOPE-A" in body
    assert "SCOPE-B" not in body
    assert "Categoria SCOPE-B" not in body


def test_report_rows_respect_user_scope(app):
    with app.app_context():
        user, _tool_allowed, _tool_blocked = _scoped_fixture()

        definition, rows = build_report_rows("situacao-atual", {}, user=user)

        assert definition.code == "situacao-atual"
        codes = {row["codigo_interno"] for row in rows}
        assert "SCOPE-A" in codes
        assert "SCOPE-B" not in codes
