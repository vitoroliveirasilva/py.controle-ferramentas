from __future__ import annotations

from datetime import UTC, datetime, timedelta

import app.notifications.services as notification_services
from app.audit.models import AuditLogModel
from app.categories.services import create_category
from app.custody.services import assign_initial_custody
from app.extensions import db
from app.inventories.services import create_inventory, update_inventory_item_status
from app.locations.services import create_location
from app.models.enums import NotificationStatus
from app.notifications.gateway_mail import GatewayMailResponse, GatewayMailValidationError
from app.notifications.repositories import count_unread_notifications
from app.notifications.services import (
    create_notification,
    mark_as_read,
    run_notification_scan,
    send_pending_email_notifications,
)
from app.permissions.services import assign_role_to_user, assign_scope_to_user
from app.tools.services import create_tool
from app.users.repositories import create_user


def _login(client, email: str, name: str = "Notification Admin"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def _admin_user(email: str = "notify-admin@brasif.com.br"):
    user = create_user(email=email, nome="Notification Admin")
    db.session.commit()
    assign_role_to_user(user.email, "admin_sistema")
    assign_scope_to_user(user.email, "global", "*")
    return user


def _inventory_fixture():
    admin = _admin_user()
    category = create_category(
        {
            "codigo": "NOT-CAT",
            "nome": "Categoria Notificação",
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
            "codigo": "NOT-LOC",
            "nome": "Almoxarifado Notificação",
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
    db.session.commit()
    tool = create_tool(
        {
            "codigo_interno": "NOT-001",
            "nome": "Ferramenta Notificação",
            "descricao": "",
            "id_categoria": category.id_categoria,
            "status": "disponivel",
            "criticidade": "alta",
            "ativo_imobilizado": "",
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
    inventory = create_inventory(
        {
            "titulo": "Inventário Notificação",
            "tipo_inventario": "anual",
            "escopo_tipo": "local",
            "escopo_usuario_id": 0,
            "escopo_location_id": location.id_location,
            "status_inicial": "em_andamento",
            "descricao": "",
        }
    )
    inventory.created_at = datetime.now(UTC) - timedelta(days=45)
    db.session.commit()
    return admin, inventory


def test_create_notification_is_idempotent(app):
    with app.app_context():
        user = _admin_user("notify-idempotent@brasif.com.br")
        first, created_first = create_notification(
            tipo="sistema",
            titulo="Teste",
            mensagem="Mensagem",
            usuario_destino=user,
            dedupe_key="same-key",
            commit=True,
        )
        second, created_second = create_notification(
            tipo="sistema",
            titulo="Teste 2",
            mensagem="Mensagem 2",
            usuario_destino=user,
            dedupe_key="same-key",
            commit=True,
        )

        assert created_first is True
        assert created_second is False
        assert first.id_notification == second.id_notification
        assert count_unread_notifications(user.id_usuario) == 1


def test_create_notification_codes_are_unique_when_clock_repeats(app, monkeypatch):
    fixed_now = datetime(2026, 5, 21, 17, 41, 34, 320513, tzinfo=UTC)
    monkeypatch.setattr(notification_services, "_now", lambda: fixed_now)

    with app.app_context():
        user = _admin_user("notify-code@brasif.com.br")
        notifications = []
        for index in range(5):
            notification, created = create_notification(
                tipo="sistema",
                titulo=f"Código único {index}",
                mensagem="Mensagem",
                usuario_destino=user,
                dedupe_key=f"unique-code-{index}",
                commit=False,
            )
            assert created is True
            notifications.append(notification)

        db.session.commit()

        codes = [notification.codigo for notification in notifications]
        assert len(codes) == len(set(codes))
        assert all(code.startswith("NOT-20260521174134320513-") for code in codes)


def test_mark_notification_as_read(app):
    with app.app_context():
        user = _admin_user("notify-read@brasif.com.br")
        notification, _created = create_notification(
            tipo="sistema",
            titulo="Leitura",
            mensagem="Mensagem",
            usuario_destino=user,
            dedupe_key="read-key",
            commit=True,
        )

        mark_as_read(notification, user)

        assert notification.status == NotificationStatus.LIDA.value
        assert notification.lida_em is not None


def test_notification_scan_generates_overdue_inventory_and_divergence_notifications(
    app,
):
    with app.app_context():
        _admin, inventory = _inventory_fixture()
        item = inventory.itens[0]
        update_inventory_item_status(inventory, item, "faltante", "Não localizado")
        db.session.commit()

        summary = run_notification_scan(
            inventory_overdue_days=30, transfer_pending_days=0
        )

        assert summary.created >= 2
        assert summary.inventories_overdue == 1
        assert summary.critical_divergences == 1


def test_send_pending_email_notifications_dry_run_records_delivery(app):
    with app.app_context():
        user = _admin_user("notify-email@brasif.com.br")
        notification, _created = create_notification(
            tipo="sistema",
            titulo="E-mail",
            mensagem="Mensagem",
            usuario_destino=user,
            dedupe_key="email-key",
            commit=True,
        )

        summary = send_pending_email_notifications(limit=10, dry_run=True)

        assert summary.skipped >= 1
        assert notification.tentativas_envio == 1
        assert notification.entregas[0].status == "dry_run"


def test_notifications_page_renders_for_admin(app, client):
    with app.app_context():
        user = _admin_user("notify-page@brasif.com.br")
        create_notification(
            tipo="sistema",
            titulo="Página",
            mensagem="Mensagem",
            usuario_destino=user,
            dedupe_key="page-key",
            commit=True,
        )

    _login(client, user.email, user.nome)
    response = client.get("/admin/notifications/")

    assert response.status_code == 200
    assert "Notificações internas" in response.get_data(as_text=True)


class FakeGatewayMailClient:
    def __init__(self, response=None, error=None):
        self.response = response or GatewayMailResponse(
            status_code=202, body='{"ok": true}', attempts=1, duration_ms=15
        )
        self.error = error
        self.messages = []

    def send(self, message):
        self.messages.append(message)
        if self.error:
            raise self.error
        return self.response


def test_send_pending_email_notifications_uses_gateway_and_audits(app):
    with app.app_context():
        app.config["NOTIFICATIONS_EMAIL_ENABLED"] = True
        app.config["BRASIF_GATEWAY_BASE_URL"] = "https://howard.brasif.local"
        app.config["BRASIF_GATEWAY_API_KEY"] = "super-secret-key"
        app.config["BRASIF_GATEWAY_RETRY_BACKOFF_SECONDS"] = 0
        user = _admin_user("notify-gateway@brasif.com.br")
        notification, _created = create_notification(
            tipo="sistema",
            titulo="Gateway",
            mensagem="Mensagem",
            usuario_destino=user,
            dedupe_key="gateway-key",
            commit=True,
        )
        client = FakeGatewayMailClient()

        summary = send_pending_email_notifications(limit=10, client=client)

        assert summary.sent == 1
        assert summary.failed == 0
        assert notification.status == NotificationStatus.ENVIADA.value
        assert notification.enviada_em is not None
        assert notification.entregas[0].status == "sent"
        assert notification.entregas[0].destino == "no***@brasif.com.br"
        assert client.messages[0].to_recipients == ["notify-gateway@brasif.com.br"]

        audit = (
            db.session.query(AuditLogModel)
            .filter(AuditLogModel.acao == "notifications.email_send")
            .one()
        )
        assert "super-secret-key" not in (audit.depois or "")
        assert "notify-gateway@brasif.com.br" not in (audit.depois or "")
        assert "no***@brasif.com.br" in (audit.depois or "")


def test_send_pending_email_notifications_records_validation_failure(app):
    with app.app_context():
        app.config["NOTIFICATIONS_EMAIL_ENABLED"] = True
        app.config["BRASIF_GATEWAY_API_KEY"] = "super-secret-key"
        user = _admin_user("notify-invalid@brasif.com.br")
        notification, _created = create_notification(
            tipo="sistema",
            titulo="",
            mensagem="Mensagem",
            usuario_destino=user,
            dedupe_key="gateway-invalid-key",
            commit=True,
        )
        client = FakeGatewayMailClient(
            error=GatewayMailValidationError("Payload inválido sem segredo")
        )

        summary = send_pending_email_notifications(limit=10, client=client)

        assert summary.sent == 0
        assert summary.failed == 1
        assert notification.status == NotificationStatus.FALHA.value
        assert notification.entregas[0].status == "failed_permanent"
        assert "super-secret-key" not in notification.entregas[0].resposta
