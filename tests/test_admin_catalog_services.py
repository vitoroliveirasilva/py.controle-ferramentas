from __future__ import annotations

import pytest

from app.audit.models import AuditLogModel
from app.categories.services import create_category
from app.custody.repositories import get_current_custody
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.locations.services import create_location
from app.tools.services import create_tool, update_tool


def test_create_category_records_audit_log(app):
    with app.app_context():
        category = create_category(
            {
                "codigo": "manual",
                "nome": "Ferramentas manuais",
                "descricao": "Itens manuais",
                "ativo": True,
                "controle_individual_padrao": True,
                "requer_numero_serie": False,
                "requer_calibracao": False,
                "motivo": "Cadastro inicial",
            }
        )
        log = db.session.execute(db.select(AuditLogModel)).scalar_one()

    assert category.codigo == "manual"
    assert log.acao == "categories.create"
    assert log.entidade_id == str(category.id_categoria)


def test_create_location_normalizes_code(app):
    with app.app_context():
        location = create_location(
            {
                "codigo": " OFI-JDI ",
                "nome": "Oficina Jundiaí",
                "tipo_local": "oficina",
                "filial": "Jundiaí",
                "departamento": "Serviços",
                "responsavel_nome": "Responsável",
                "endereco": "",
                "observacoes": "",
                "ativo": True,
                "motivo": "Cadastro inicial",
            }
        )

    assert location.codigo == "ofi-jdi"


def test_tool_requires_serial_when_category_requires_it(app):
    with app.app_context():
        category = create_category(
            {
                "codigo": "calibracao",
                "nome": "Calibração",
                "descricao": "",
                "ativo": True,
                "controle_individual_padrao": True,
                "requer_numero_serie": True,
                "requer_calibracao": True,
                "motivo": "Cadastro inicial",
            }
        )
        with pytest.raises(ValueError, match="número de série"):
            create_tool(
                {
                    "codigo_interno": "TL-001",
                    "nome": "Torquímetro",
                    "descricao": "",
                    "id_categoria": category.id_categoria,
                    "status": "disponivel",
                    "criticidade": "alta",
                    "ativo_imobilizado": "",
                    "numero_serie": "",
                    "marca": "",
                    "modelo": "",
                    "controle_individual": True,
                    "requer_calibracao": True,
                    "ativo": True,
                    "observacoes": "",
                    "motivo": "Cadastro inicial",
                }
            )


def test_tool_critical_update_requires_permission_and_reason(app):
    with app.app_context():
        category = create_category(
            {
                "codigo": "geral",
                "nome": "Geral",
                "descricao": "",
                "ativo": True,
                "controle_individual_padrao": True,
                "requer_numero_serie": False,
                "requer_calibracao": False,
                "motivo": "Cadastro inicial",
            }
        )
        tool = create_tool(
            {
                "codigo_interno": "TL-002",
                "nome": "Chave combinada",
                "descricao": "",
                "id_categoria": category.id_categoria,
                "status": "disponivel",
                "criticidade": "media",
                "ativo_imobilizado": "",
                "numero_serie": "",
                "marca": "Gedore",
                "modelo": "10mm",
                "controle_individual": True,
                "requer_calibracao": False,
                "ativo": True,
                "observacoes": "",
                "motivo": "Cadastro inicial",
            }
        )
        payload = {
            "codigo_interno": "TL-002-A",
            "nome": "Chave combinada",
            "descricao": "",
            "id_categoria": category.id_categoria,
            "status": "disponivel",
            "criticidade": "media",
            "ativo_imobilizado": "",
            "numero_serie": "",
            "marca": "Gedore",
            "modelo": "10mm",
            "controle_individual": True,
            "requer_calibracao": False,
            "ativo": True,
            "observacoes": "",
            "motivo": "",
        }

        with pytest.raises(PermissionError):
            update_tool(tool, payload, can_critical_update=False)

        with pytest.raises(ValueError, match="motivo"):
            update_tool(tool, payload, can_critical_update=True)


def test_tool_baixa_closes_current_custody(app):
    with app.app_context():
        category = create_category(
            {
                "codigo": "baixa-custody",
                "nome": "Baixa Custody",
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
                "codigo": "ALM-BAIXA",
                "nome": "Almoxarifado Baixa",
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
                "codigo_interno": "TL-BAIXA-001",
                "nome": "Ferramenta para baixa",
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

        update_tool(
            tool,
            {
                "codigo_interno": tool.codigo_interno,
                "nome": tool.nome,
                "descricao": tool.descricao or "",
                "id_categoria": category.id_categoria,
                "status": "baixada",
                "criticidade": tool.criticidade,
                "ativo_imobilizado": "",
                "numero_serie": "",
                "marca": tool.marca or "",
                "modelo": tool.modelo or "",
                "controle_individual": tool.controle_individual,
                "requer_calibracao": tool.requer_calibracao,
                "ativo": False,
                "observacoes": tool.observacoes or "",
                "motivo": "Baixa administrativa com encerramento de custódia",
            },
            can_critical_update=True,
        )

        assert tool.status == "baixada"
        assert tool.ativo is False
        assert get_current_custody(tool.id_tool) is None
