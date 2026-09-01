from __future__ import annotations

from datetime import timedelta

import pytest
from flask_login import login_user

from app.categories.services import create_category
from app.custody.repositories import get_current_custody
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.locations.services import create_location
from app.permissions.services import assign_role_to_user, assign_scope_to_user
from app.tools.services import create_tool
from app.transfers.services import (
    cancel_transfer,
    confirm_destination,
    confirm_origin,
    create_transfer,
    expire_transfer,
    refuse_transfer,
)
from app.users.repositories import create_user


def _category(code: str = "cat-transfer"):
    return create_category(
        {
            "codigo": code,
            "nome": f"Categoria {code}",
            "descricao": "",
            "ativo": True,
            "controle_individual_padrao": True,
            "requer_numero_serie": False,
            "requer_calibracao": False,
            "motivo": "Cadastro inicial",
        }
    )


def _tool(category_id: int, code: str = "TRF-TOOL-001"):
    return create_tool(
        {
            "codigo_interno": code,
            "nome": f"Ferramenta {code}",
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


def _location(code: str = "ALM-TRF"):
    return create_location(
        {
            "codigo": code,
            "nome": f"Almoxarifado {code}",
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


def _transfer_fixture():
    origin = create_user(email="origin-transfer@brasif.com.br", nome="Origin Transfer")
    destination = create_user(email="dest-transfer@brasif.com.br", nome="Dest Transfer")
    category = _category()
    location = _location()
    db.session.commit()
    tool = _tool(category.id_categoria)
    assign_initial_custody(
        tool,
        {
            "tipo_custodia": "almoxarifado",
            "id_responsavel_usuario": 0,
            "id_location": location.id_location,
            "motivo": "Entrada no almoxarifado",
        },
    )
    return origin, destination, tool


def test_create_transfer_changes_tool_to_transfer_status(app):
    with app.app_context():
        _origin, destination, tool = _transfer_fixture()

        transfer = create_transfer(
            {
                "tipo_transferencia": "almoxarifado_para_tecnico",
                "destino_tipo_custodia": "tecnico",
                "destino_usuario_id": destination.id_usuario,
                "destino_location_id": 0,
                "codigos_ferramentas": tool.codigo_interno,
                "motivo": "Entrega formal ao técnico",
                "observacoes": "",
            }
        )

        assert transfer.status == "aguardando_confirmacao_origem"
        assert transfer.itens[0].status == "pendente"
        assert tool.status == "transferencia"


def test_transfer_confirm_destination_updates_custody(app):
    with app.app_context():
        _origin, destination, tool = _transfer_fixture()
        transfer = create_transfer(
            {
                "tipo_transferencia": "almoxarifado_para_tecnico",
                "destino_tipo_custodia": "tecnico",
                "destino_usuario_id": destination.id_usuario,
                "destino_location_id": 0,
                "codigos_ferramentas": tool.codigo_interno,
                "motivo": "Entrega formal ao técnico",
                "observacoes": "",
            }
        )

        confirm_origin(transfer)
        confirm_destination(transfer)
        current = get_current_custody(tool.id_tool)

        assert transfer.status == "concluida"
        assert transfer.itens[0].status == "concluido"
        assert current is not None
        assert current.id_responsavel_usuario == destination.id_usuario
        assert current.tipo_custodia == "tecnico"
        assert tool.status == "em_uso"


def test_transfer_refuse_keeps_current_custody_and_restores_tool_status(app):
    with app.app_context():
        _origin, destination, tool = _transfer_fixture()
        previous_custody = get_current_custody(tool.id_tool)
        transfer = create_transfer(
            {
                "tipo_transferencia": "almoxarifado_para_tecnico",
                "destino_tipo_custodia": "tecnico",
                "destino_usuario_id": destination.id_usuario,
                "destino_location_id": 0,
                "codigos_ferramentas": tool.codigo_interno,
                "motivo": "Entrega formal ao técnico",
                "observacoes": "",
            }
        )

        refuse_transfer(transfer, "Destino recusou o recebimento")
        current = get_current_custody(tool.id_tool)

        assert transfer.status == "recusada"
        assert transfer.itens[0].status == "recusado"
        assert current is not None
        assert current.id_custody == previous_custody.id_custody
        assert tool.status == "disponivel"


def test_cannot_transfer_tool_without_current_custody(app):
    with app.app_context():
        destination = create_user(
            email="dest-no-custody@brasif.com.br", nome="Dest No Custody"
        )
        category = _category("cat-transfer-no-custody")
        db.session.commit()
        tool = _tool(category.id_categoria, "TRF-NO-CUSTODY")

        with pytest.raises(ValueError, match="não possui custódia atual"):
            create_transfer(
                {
                    "tipo_transferencia": "almoxarifado_para_tecnico",
                    "destino_tipo_custodia": "tecnico",
                    "destino_usuario_id": destination.id_usuario,
                    "destino_location_id": 0,
                    "codigos_ferramentas": tool.codigo_interno,
                    "motivo": "Tentativa sem custódia",
                    "observacoes": "",
                }
            )


def _create_default_transfer(destination, tool):
    return create_transfer(
        {
            "tipo_transferencia": "almoxarifado_para_tecnico",
            "destino_tipo_custodia": "tecnico",
            "destino_usuario_id": destination.id_usuario,
            "destino_location_id": 0,
            "codigos_ferramentas": tool.codigo_interno,
            "motivo": "Entrega formal ao técnico",
            "observacoes": "",
        }
    )


def test_destination_user_cannot_confirm_origin_without_origin_relation(app):
    with app.app_context():
        _origin, destination, tool = _transfer_fixture()
        transfer = _create_default_transfer(destination, tool)

        with app.test_request_context("/admin/transfers/confirm-origin"):
            login_user(destination)
            with pytest.raises(ValueError, match="origem"):
                confirm_origin(transfer, "Tentativa de confirmar origem")


def test_origin_scope_and_destination_relation_can_confirm_transfer(app):
    with app.app_context():
        origin_responsible = create_user(
            email="origin-scope@brasif.com.br",
            nome="Origin Scope",
        )
        db.session.commit()
        assign_role_to_user(origin_responsible.email, "responsavel_local")

        _origin, destination, tool = _transfer_fixture()
        origin_custody = get_current_custody(tool.id_tool)
        assign_scope_to_user(
            origin_responsible.email,
            "local",
            str(origin_custody.id_location),
        )
        db.session.refresh(origin_responsible)
        db.session.refresh(destination)

        transfer = _create_default_transfer(destination, tool)

        with app.test_request_context("/admin/transfers/confirm-origin"):
            login_user(origin_responsible)
            confirm_origin(transfer, "Origem confirmou a saída")

        with app.test_request_context("/admin/transfers/confirm-destination"):
            login_user(destination)
            confirm_destination(transfer, "Destino confirmou o recebimento")

        current = get_current_custody(tool.id_tool)
        assert transfer.status == "concluida"
        assert current.id_responsavel_usuario == destination.id_usuario


def test_cannot_create_duplicate_pending_transfer_for_same_tool(app):
    with app.app_context():
        _origin, destination, tool = _transfer_fixture()
        _create_default_transfer(destination, tool)

        with pytest.raises(ValueError, match="já está na transferência pendente"):
            _create_default_transfer(destination, tool)


def test_completed_transfer_cannot_be_force_cancelled(app):
    with app.app_context():
        _origin, destination, tool = _transfer_fixture()
        transfer = _create_default_transfer(destination, tool)
        confirm_origin(transfer)
        confirm_destination(transfer)

        with pytest.raises(ValueError, match="não pode ser cancelada"):
            cancel_transfer(transfer, "Correção posterior", force=True)


def test_expire_transfer_restores_open_items_and_tool_status(app):
    with app.app_context():
        _origin, destination, tool = _transfer_fixture()
        transfer = _create_default_transfer(destination, tool)
        transfer.solicitado_em = transfer.solicitado_em - timedelta(days=10)
        db.session.commit()

        expire_transfer(transfer)

        assert transfer.status == "expirada"
        assert transfer.itens[0].status == "expirado"
        assert tool.status == "disponivel"
