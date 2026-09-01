from __future__ import annotations

import pytest

from app.categories.services import create_category
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.inventories.repositories import list_inventory_divergences
from app.inventories.services import (
    create_inventory,
    finish_inventory,
    resolve_inventory_divergence,
    update_inventory_item_status,
)
from app.locations.services import create_location
from app.tools.services import create_tool


def _category(code: str = "cat-div"):
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


def _location(code: str = "ALM-DIV"):
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


def _tool(category_id: int, code: str = "DIV-TOOL-001"):
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


def _inventory_fixture(status: str = "em_andamento"):
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
    return create_inventory(
        {
            "titulo": "Inventário com divergências",
            "tipo_inventario": "extraordinario",
            "escopo_tipo": "local",
            "escopo_usuario_id": 0,
            "escopo_location_id": location.id_location,
            "status_inicial": status,
            "descricao": "",
        }
    )


def test_divergent_item_creates_open_divergence(app):
    with app.app_context():
        inventory = _inventory_fixture()
        item = inventory.itens[0]

        update_inventory_item_status(inventory, item, "faltante", "Não localizado")
        divergences = list_inventory_divergences(inventory.id_inventory)

        assert inventory.status == "com_divergencia"
        assert len(divergences) == 1
        assert divergences[0].tipo_divergencia == "ferramenta_faltante"
        assert divergences[0].status == "aberta"


def test_finish_inventory_is_blocked_with_open_divergence(app):
    with app.app_context():
        inventory = _inventory_fixture()
        item = inventory.itens[0]
        update_inventory_item_status(inventory, item, "danificado", "Trincado")

        with pytest.raises(ValueError, match="divergência"):
            finish_inventory(inventory, "Conferência concluída")


def test_resolve_divergence_regularizes_item_and_allows_finish(app):
    with app.app_context():
        inventory = _inventory_fixture()
        item = inventory.itens[0]
        update_inventory_item_status(inventory, item, "faltante", "Não localizado")
        divergence = list_inventory_divergences(inventory.id_inventory)[0]

        resolve_inventory_divergence(
            inventory,
            divergence,
            "recontar",
            "Ferramenta localizada na bancada após recontagem.",
        )
        finish_inventory(inventory, "Sem pendências abertas")

        assert divergence.status == "regularizada"
        assert item.status == "regularizado"
        assert inventory.status == "aguardando_assinatura"


def test_finish_inventory_requires_all_items_checked(app):
    with app.app_context():
        inventory = _inventory_fixture()

        with pytest.raises(ValueError, match="itens pendentes"):
            finish_inventory(inventory, "Tentativa prematura")
