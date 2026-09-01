from __future__ import annotations

import pytest

from app.categories.services import create_category
from app.custody.repositories import (
    get_current_custody,
    list_custody_history,
    list_timeline_events,
)
from app.custody.services import assign_initial_custody, change_custody
from app.extensions import db
from app.locations.services import create_location
from app.tools.services import create_tool
from app.users.repositories import create_user


def _category():
    return create_category(
        {
            "codigo": "geral-custody",
            "nome": "Geral Custody",
            "descricao": "",
            "ativo": True,
            "controle_individual_padrao": True,
            "requer_numero_serie": False,
            "requer_calibracao": False,
            "motivo": "Cadastro inicial",
        }
    )


def _tool(category_id: int):
    return create_tool(
        {
            "codigo_interno": "CT-001",
            "nome": "Ferramenta de custódia",
            "descricao": "",
            "id_categoria": category_id,
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


def test_assign_initial_custody_to_user(app):
    with app.app_context():
        user = create_user(email="tech@brasif.com.br", nome="Tech One")
        category = _category()
        db.session.commit()
        tool = _tool(category.id_categoria)

        custody = assign_initial_custody(
            tool,
            {
                "tipo_custodia": "tecnico",
                "id_responsavel_usuario": user.id_usuario,
                "id_location": 0,
                "motivo": "Entrega inicial ao técnico",
            },
        )

        current = get_current_custody(tool.id_tool)
        events = list_timeline_events(tool.id_tool)

    assert custody.atual is True
    assert current is not None
    assert current.id_responsavel_usuario == user.id_usuario
    assert events[0].event_type == "custodia_inicial"


def test_cannot_assign_two_current_custodies(app):
    with app.app_context():
        user = create_user(email="tech2@brasif.com.br", nome="Tech Two")
        category = _category()
        db.session.commit()
        tool = _tool(category.id_categoria)
        assign_initial_custody(
            tool,
            {
                "tipo_custodia": "tecnico",
                "id_responsavel_usuario": user.id_usuario,
                "id_location": 0,
                "motivo": "Entrega inicial ao técnico",
            },
        )

        with pytest.raises(ValueError, match="já possui custódia"):
            assign_initial_custody(
                tool,
                {
                    "tipo_custodia": "tecnico",
                    "id_responsavel_usuario": user.id_usuario,
                    "id_location": 0,
                    "motivo": "Nova entrega indevida",
                },
            )


def test_change_custody_closes_previous_current(app):
    with app.app_context():
        user = create_user(email="tech3@brasif.com.br", nome="Tech Three")
        category = _category()
        location = create_location(
            {
                "codigo": "ALM-CENTRAL",
                "nome": "Almoxarifado Central",
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
        tool = _tool(category.id_categoria)
        first = assign_initial_custody(
            tool,
            {
                "tipo_custodia": "tecnico",
                "id_responsavel_usuario": user.id_usuario,
                "id_location": 0,
                "motivo": "Entrega inicial ao técnico",
            },
        )
        second = change_custody(
            tool,
            {
                "tipo_custodia": "almoxarifado",
                "id_responsavel_usuario": 0,
                "id_location": location.id_location,
                "motivo": "Retorno para o almoxarifado",
            },
        )
        history = list_custody_history(tool.id_tool)

    assert first.id_custody != second.id_custody
    assert second.atual is True
    assert any(item.fim_em is not None and item.atual is False for item in history)
    assert get_current_custody(tool.id_tool).id_custody == second.id_custody


def test_baixada_tool_cannot_receive_custody(app):
    with app.app_context():
        user = create_user(email="tech4@brasif.com.br", nome="Tech Four")
        category = _category()
        db.session.commit()
        tool = _tool(category.id_categoria)
        tool.status = "baixada"
        tool.ativo = False
        db.session.commit()

        with pytest.raises(ValueError, match="inativa ou baixada"):
            assign_initial_custody(
                tool,
                {
                    "tipo_custodia": "tecnico",
                    "id_responsavel_usuario": user.id_usuario,
                    "id_location": 0,
                    "motivo": "Tentativa indevida",
                },
            )


def test_administrative_custody_change_requires_strong_reason(app):
    with app.app_context():
        user = create_user(email="tech-force@brasif.com.br", nome="Tech Force")
        category = _category()
        location = create_location(
            {
                "codigo": "ALM-FORCE",
                "nome": "Almoxarifado Force",
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
        tool = _tool(category.id_categoria)
        assign_initial_custody(
            tool,
            {
                "tipo_custodia": "tecnico",
                "id_responsavel_usuario": user.id_usuario,
                "id_location": 0,
                "motivo": "Entrega inicial ao técnico",
            },
        )

        with pytest.raises(ValueError, match="justificativa administrativa"):
            change_custody(
                tool,
                {
                    "tipo_custodia": "almoxarifado",
                    "id_responsavel_usuario": 0,
                    "id_location": location.id_location,
                    "motivo": "Ajuste",
                },
            )
