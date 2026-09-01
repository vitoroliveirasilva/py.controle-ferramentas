from __future__ import annotations

import pytest

from app.categories.services import create_category
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.inventories.services import (
    cancel_inventory,
    create_inventory,
    inventory_progress,
    start_inventory,
    update_inventory_item_status,
)
from app.locations.services import create_location
from app.tools.services import create_tool
from app.users.repositories import create_user


def _category(code: str = "cat-inventory"):
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


def _tool(category_id: int, code: str = "INV-TOOL-001"):
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


def _location(code: str = "ALM-INV"):
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


def _inventory_fixture():
    technician = create_user(
        email="tech-inventory@brasif.com.br", nome="Tech Inventory"
    )
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
    return technician, location, tool


def test_create_inventory_loads_expected_items_from_current_custody(app):
    with app.app_context():
        _technician, location, tool = _inventory_fixture()

        inventory = create_inventory(
            {
                "titulo": "Inventário do almoxarifado",
                "tipo_inventario": "anual",
                "escopo_tipo": "local",
                "escopo_usuario_id": 0,
                "escopo_location_id": location.id_location,
                "status_inicial": "rascunho",
                "descricao": "",
            }
        )

        assert inventory.status == "rascunho"
        assert len(inventory.itens) == 1
        assert inventory.itens[0].id_tool == tool.id_tool
        assert inventory.itens[0].status == "pendente"
        assert tool.status == "disponivel"


def test_start_inventory_locks_expected_tools(app):
    with app.app_context():
        _technician, location, tool = _inventory_fixture()
        inventory = create_inventory(
            {
                "titulo": "Inventário em andamento",
                "tipo_inventario": "extraordinario",
                "escopo_tipo": "local",
                "escopo_usuario_id": 0,
                "escopo_location_id": location.id_location,
                "status_inicial": "rascunho",
                "descricao": "",
            }
        )

        start_inventory(inventory)

        assert inventory.status == "em_andamento"
        assert tool.status == "inventario"


def test_item_divergence_marks_inventory_with_divergence(app):
    with app.app_context():
        _technician, location, _tool = _inventory_fixture()
        inventory = create_inventory(
            {
                "titulo": "Inventário com divergência",
                "tipo_inventario": "extraordinario",
                "escopo_tipo": "local",
                "escopo_usuario_id": 0,
                "escopo_location_id": location.id_location,
                "status_inicial": "em_andamento",
                "descricao": "",
            }
        )
        item = inventory.itens[0]

        update_inventory_item_status(
            inventory, item, "faltante", "Não localizado na bancada"
        )
        progress = inventory_progress(inventory)

        assert item.status == "faltante"
        assert inventory.status == "com_divergencia"
        assert progress["divergent"] == 1


def test_cancel_inventory_restores_tool_status(app):
    with app.app_context():
        _technician, location, tool = _inventory_fixture()
        inventory = create_inventory(
            {
                "titulo": "Inventário para cancelar",
                "tipo_inventario": "extraordinario",
                "escopo_tipo": "local",
                "escopo_usuario_id": 0,
                "escopo_location_id": location.id_location,
                "status_inicial": "em_andamento",
                "descricao": "",
            }
        )

        assert tool.status == "inventario"
        cancel_inventory(inventory, "Inventário aberto por engano")

        assert inventory.status == "cancelado"
        assert tool.status == "disponivel"


def test_cannot_create_inventory_without_expected_tools(app):
    with app.app_context():
        location = _location("ALM-EMPTY")
        db.session.commit()

        with pytest.raises(ValueError, match="Nenhuma ferramenta"):
            create_inventory(
                {
                    "titulo": "Inventário vazio",
                    "tipo_inventario": "anual",
                    "escopo_tipo": "local",
                    "escopo_usuario_id": 0,
                    "escopo_location_id": location.id_location,
                    "status_inicial": "rascunho",
                    "descricao": "",
                }
            )


def test_scan_unexpected_existing_tool_registers_excess_divergence(app):
    from app.inventories.repositories import list_inventory_divergences
    from app.inventories.services import scan_inventory_item

    with app.app_context():
        _technician, location, _expected_tool = _inventory_fixture()
        other_location = _location("ALM-EXTRA")
        category = _category("cat-extra")
        db.session.commit()
        extra_tool = _tool(category.id_categoria, "INV-EXTRA-001")
        assign_initial_custody(
            extra_tool,
            {
                "tipo_custodia": "almoxarifado",
                "id_responsavel_usuario": 0,
                "id_location": other_location.id_location,
                "motivo": "Entrada em outro almoxarifado",
            },
        )
        inventory = create_inventory(
            {
                "titulo": "Inventário com excedente",
                "tipo_inventario": "extraordinario",
                "escopo_tipo": "local",
                "escopo_usuario_id": 0,
                "escopo_location_id": location.id_location,
                "status_inicial": "em_andamento",
                "descricao": "",
            }
        )

        item = scan_inventory_item(
            inventory,
            "INV-EXTRA-001",
            "Encontrada fisicamente na bancada do inventário.",
        )
        divergences = list_inventory_divergences(inventory.id_inventory)

        assert item.status == "excedente"
        assert item.id_tool == extra_tool.id_tool
        assert inventory.status == "com_divergencia"
        assert len(divergences) == 1
        assert divergences[0].tipo_divergencia in {
            "ferramenta_excedente",
            "custodia_inconsistente",
        }


def test_resolve_loss_divergence_opens_linked_occurrence(app):
    from app.inventories.repositories import list_inventory_divergences
    from app.inventories.services import resolve_inventory_divergence
    from app.occurrences.models import OccurrenceModel

    with app.app_context():
        _technician, location, _tool = _inventory_fixture()
        inventory = create_inventory(
            {
                "titulo": "Inventário com perda",
                "tipo_inventario": "extraordinario",
                "escopo_tipo": "local",
                "escopo_usuario_id": 0,
                "escopo_location_id": location.id_location,
                "status_inicial": "em_andamento",
                "descricao": "",
            }
        )
        item = inventory.itens[0]
        update_inventory_item_status(inventory, item, "faltante", "Não localizado")
        divergence = list_inventory_divergences(inventory.id_inventory)[0]

        resolve_inventory_divergence(
            inventory,
            divergence,
            "baixar_por_perda",
            "Ferramenta perdida após recontagem e validação com responsável.",
        )
        occurrence = db.session.get(OccurrenceModel, divergence.id_occurrence)

        assert divergence.status == "regularizada"
        assert divergence.id_occurrence is not None
        assert occurrence is not None
        assert occurrence.tipo_ocorrencia == "perda"
        assert occurrence.status == "aguardando_aprovacao"


def test_transfer_resolution_requires_linked_transfer(app):
    from app.inventories.repositories import list_inventory_divergences
    from app.inventories.services import resolve_inventory_divergence

    with app.app_context():
        _technician, location, _tool = _inventory_fixture()
        inventory = create_inventory(
            {
                "titulo": "Inventário com transferência pendente",
                "tipo_inventario": "extraordinario",
                "escopo_tipo": "local",
                "escopo_usuario_id": 0,
                "escopo_location_id": location.id_location,
                "status_inicial": "em_andamento",
                "descricao": "",
            }
        )
        item = inventory.itens[0]
        update_inventory_item_status(inventory, item, "faltante", "Não localizado")
        divergence = list_inventory_divergences(inventory.id_inventory)[0]

        with pytest.raises(ValueError, match="transferência vinculada"):
            resolve_inventory_divergence(
                inventory,
                divergence,
                "transferir",
                "Será corrigida por transferência formal.",
            )
