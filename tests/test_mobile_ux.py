from __future__ import annotations

from io import BytesIO

from app.categories.services import create_category
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.inventories.models import InventoryItemEvidenceModel
from app.inventories.services import (
    create_inventory,
    save_inventory_item_evidence,
    scan_inventory_item,
)
from app.locations.services import create_location
from app.permissions.services import assign_role_to_user
from app.tools.services import create_tool, save_reference_photo
from app.users.repositories import create_user


def _make_admin(email: str = "mobile-admin@brasif.com.br"):
    user = create_user(email=email, nome="Mobile Admin")
    db.session.commit()
    assign_role_to_user(email, "admin_sistema")
    return user


def _login(client, email: str, name: str = "Mobile Admin"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def _create_basic_tool():
    category = create_category(
        {
            "codigo": "mobile",
            "nome": "Mobile",
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
            "codigo": "almox-mobile",
            "nome": "Almox Mobile",
            "tipo_local": "almoxarifado",
            "filial": "Jundiaí",
            "departamento": "Serviços",
            "responsavel_nome": "Responsável",
            "endereco": "",
            "observacoes": "",
            "ativo": True,
            "motivo": "Cadastro inicial",
        }
    )
    tool = create_tool(
        {
            "codigo_interno": "MOB-001",
            "nome": "Ferramenta mobile",
            "descricao": "",
            "id_categoria": category.id_categoria,
            "status": "disponivel",
            "criticidade": "media",
            "ativo_imobilizado": "PAT-MOB-001",
            "numero_serie": "SER-MOB-001",
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
            "id_location": location.id_location,
            "id_responsavel_usuario": 0,
            "motivo": "Custódia inicial",
        },
    )
    return tool, location


def _tiny_png() -> BytesIO:
    return BytesIO(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01"
        b"\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_reference_photo_upload_and_qr_routes(app, client):
    with app.app_context():
        user = _make_admin()
        tool, _location = _create_basic_tool()
        save_reference_photo(
            tool,
            FileLikeStorage(_tiny_png(), "referencia.png", "image/png"),
            "Foto inicial",
        )
        tool_id = tool.id_tool

    _login(client, user.email)
    response = client.get(f"/admin/tools/{tool_id}/qr.svg")
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"

    response = client.get(f"/admin/tools/{tool_id}/label")
    assert response.status_code == 200
    assert "Etiqueta da ferramenta" in response.get_data(as_text=True)

    response = client.get(f"/admin/tools/{tool_id}/reference-photo")
    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_inventory_scan_and_evidence_upload(app):
    with app.app_context():
        _make_admin("mobile-inventory@brasif.com.br")
        _tool, location = _create_basic_tool()
        inventory = create_inventory(
            {
                "titulo": "Inventário mobile",
                "tipo_inventario": "extraordinario",
                "escopo_tipo": "local",
                "escopo_usuario_id": 0,
                "escopo_location_id": location.id_location,
                "status_inicial": "em_andamento",
                "descricao": "",
            }
        )
        item = inventory.itens[0]

        scanned = scan_inventory_item(inventory, "MOB-001")
        assert scanned.status == "encontrado"

        evidence = save_inventory_item_evidence(
            inventory,
            item,
            FileLikeStorage(_tiny_png(), "evidencia.png", "image/png"),
            "Foto da conferência",
        )
        db.session.flush()

        saved = db.session.get(
            InventoryItemEvidenceModel, evidence.id_inventory_item_evidence
        )
        assert saved is not None
        assert saved.original_filename == "evidencia.png"


class FileLikeStorage:
    def __init__(self, stream: BytesIO, filename: str, mimetype: str):
        self.stream = stream
        self.filename = filename
        self.mimetype = mimetype

    def save(self, destination):
        self.stream.seek(0)
        with open(destination, "wb") as output:
            output.write(self.stream.read())
