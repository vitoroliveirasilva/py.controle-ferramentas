from __future__ import annotations

from app.categories.services import create_category
from app.extensions import db
from app.locations.services import create_location
from app.permissions.services import assign_role_to_user, assign_scope_to_user
from app.tools.services import create_tool
from app.users.repositories import create_user


def _login_admin(client):
    with client.application.app_context():
        user = create_user(email="occ-admin@brasif.com.br", nome="Occ Admin")
        db.session.commit()
        assign_role_to_user(user.email_lower, "admin_sistema")
        assign_scope_to_user(user.email_lower, "global", "*")
        db.session.commit()
    return client.post(
        "/auth/login",
        data={"email": "occ-admin@brasif.com.br"},
        follow_redirects=True,
    )


def _create_tool():
    category = create_category(
        {
            "codigo": "cat-occ-route",
            "nome": "Categoria Occ Route",
            "descricao": "",
            "ativo": True,
            "controle_individual_padrao": True,
            "requer_numero_serie": False,
            "requer_calibracao": False,
            "motivo": "Cadastro inicial",
        }
    )
    create_location(
        {
            "codigo": "LOC-OCC-ROUTE",
            "nome": "Local Occ Route",
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
    return create_tool(
        {
            "codigo_interno": "OCC-ROUTE-001",
            "nome": "Ferramenta Occ Route",
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


def test_occurrence_index_requires_login(client):
    response = client.get("/admin/occurrences/")
    assert response.status_code in {302, 401, 403}


def test_admin_can_open_occurrence_index(client):
    _login_admin(client)
    response = client.get("/admin/occurrences/")
    assert response.status_code == 200
    assert "Ocorrências" in response.get_data(as_text=True)


def test_admin_can_create_occurrence(client):
    _login_admin(client)
    with client.application.app_context():
        _create_tool()

    response = client.post(
        "/admin/occurrences/create",
        data={
            "codigo_ferramenta": "OCC-ROUTE-001",
            "tipo_ocorrencia": "dano",
            "motivo": "Dano no item",
            "descricao": "Ferramenta apresentou dano durante uso operacional.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Ocorrência registrada" in response.get_data(as_text=True)
