from __future__ import annotations

import pytest

from app.categories.services import create_category
from app.custody.repositories import get_current_custody
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.locations.services import create_location
from app.occurrences.services import (
    approve_occurrence,
    create_occurrence,
    resolve_occurrence,
)
from app.tools.services import create_tool


def _category(code: str = "cat-occ"):
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


def _location(code: str = "ALM-OCC"):
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


def _tool(category_id: int, code: str = "OCC-TOOL-001", asset: str = ""):
    return create_tool(
        {
            "codigo_interno": code,
            "nome": f"Ferramenta {code}",
            "descricao": "",
            "id_categoria": category_id,
            "status": "disponivel",
            "criticidade": "media",
            "ativo_imobilizado": asset,
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


def _tool_with_custody(code: str = "OCC-TOOL-001", asset: str = ""):
    category = _category(f"cat-{code.lower()}")
    location = _location(f"LOC-{code[-3:]}")
    db.session.commit()
    tool = _tool(category.id_categoria, code, asset)
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


def test_create_occurrence_for_damage_starts_open(app):
    with app.app_context():
        tool = _tool_with_custody("OCC-DAMAGE")

        occurrence = create_occurrence(
            {
                "codigo_ferramenta": tool.codigo_interno,
                "tipo_ocorrencia": "dano",
                "motivo": "Dano identificado",
                "descricao": "Ferramenta apresentou trinca no corpo durante uso.",
            }
        )

        assert occurrence.codigo.startswith("OCO-")
        assert occurrence.status == "aberta"
        assert occurrence.responsavel_atual_snapshot is not None


def test_patrimonial_loss_requires_approval_and_approval_lowers_tool(app):
    with app.app_context():
        tool = _tool_with_custody("OCC-LOSS", "ATIVO-777")

        occurrence = create_occurrence(
            {
                "codigo_ferramenta": tool.codigo_interno,
                "tipo_ocorrencia": "perda",
                "motivo": "Perda patrimonial",
                "descricao": "Ferramenta não foi localizada após conferência operacional completa.",
            }
        )
        approve_occurrence(occurrence, "Aprovação da baixa por perda patrimonial")

        assert occurrence.status == "aprovada"
        assert occurrence.impacto_patrimonial is True
        assert tool.status == "baixada"
        assert tool.ativo is False
        assert get_current_custody(tool.id_tool) is None


def test_resolve_approved_occurrence(app):
    with app.app_context():
        tool = _tool_with_custody("OCC-MAINT")
        occurrence = create_occurrence(
            {
                "codigo_ferramenta": tool.codigo_interno,
                "tipo_ocorrencia": "manutencao",
                "motivo": "Manutenção necessária",
                "descricao": "Ferramenta enviada para manutenção preventiva programada.",
            }
        )
        approve_occurrence(occurrence, "Manutenção aprovada pelo responsável")
        resolve_occurrence(
            occurrence, "Ferramenta retornou da manutenção e foi testada."
        )

        assert occurrence.status == "resolvida"
        assert occurrence.resolvido_em is not None


def test_create_occurrence_requires_existing_tool(app):
    with app.app_context(), pytest.raises(
        ValueError, match="Ferramenta não encontrada"
    ):
        create_occurrence(
            {
                "codigo_ferramenta": "NAO-EXISTE",
                "tipo_ocorrencia": "dano",
                "motivo": "Dano",
                "descricao": "Descrição suficientemente grande para validar.",
            }
        )


def test_reintegration_without_current_custody_requires_administrative_flow(app):
    with app.app_context():
        tool = _tool_with_custody("OCC-REINT")
        occurrence = create_occurrence(
            {
                "codigo_ferramenta": tool.codigo_interno,
                "tipo_ocorrencia": "baixa",
                "motivo": "Baixa patrimonial",
                "descricao": "Ferramenta retirada da operação após conferência completa.",
            }
        )
        approve_occurrence(occurrence, "Baixa aprovada pela área responsável")

        reintegration = create_occurrence(
            {
                "codigo_ferramenta": tool.codigo_interno,
                "tipo_ocorrencia": "reintegracao",
                "motivo": "Reintegração solicitada",
                "descricao": "Ferramenta foi localizada e precisa retornar ao controle.",
            }
        )

        with pytest.raises(ValueError, match="Reintegração exige custódia atual"):
            approve_occurrence(reintegration, "Reintegração aprovada sem custódia")
