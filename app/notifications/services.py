from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from flask import current_app
from flask_login import current_user
from sqlalchemy import false, select

from app.audit.services import record_audit_log
from app.extensions import db
from app.inventories.models import InventoryDivergenceModel, InventoryModel
from app.models.enums import (
    InventoryDivergenceStatus,
    InventoryStatus,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
    OccurrenceStatus,
    TransferStatus,
)
from app.notifications.gateway_mail import (
    BrasifGatewayMailClient,
    GatewayMailAuthError,
    GatewayMailConfigError,
    GatewayMailError,
    GatewayMailPermanentError,
    GatewayMailResponse,
    GatewayMailTimeoutError,
    GatewayMailTransientError,
    GatewayMailValidationError,
    build_gateway_mail_message,
    mask_email,
    summarize_recipients,
)
from app.notifications.models import NotificationDeliveryModel, NotificationModel
from app.notifications.repositories import (
    add_delivery,
    get_notification_by_dedupe_key,
    list_pending_email_notifications,
    list_users_with_permission,
)
from app.occurrences.models import OccurrenceModel
from app.transfers.models import TransferModel
from app.users.models import UserModel


@dataclass(frozen=True)
class NotificationScanSummary:
    created: int
    skipped_existing: int
    inventories_overdue: int
    transfers_pending: int
    signatures_pending: int
    critical_divergences: int


@dataclass(frozen=True)
class NotificationSendSummary:
    sent: int
    failed: int
    skipped: int


def _now() -> datetime:
    return datetime.now(UTC)


def _next_code() -> str:
    timestamp = _now().strftime("%Y%m%d%H%M%S%f")
    suffix = uuid4().hex[:12].upper()
    return f"NOT-{timestamp}-{suffix}"


def _active_recipients(permission_code: str = "notifications.view") -> list[UserModel]:
    users = list_users_with_permission(permission_code)
    if users:
        return users
    return list_users_with_permission("roles.manage")


def _recipient_key(user: UserModel | None, fallback_email: str | None = None) -> str:
    if user:
        return f"user:{user.id_usuario}"
    return f"email:{(fallback_email or 'system').lower()}"


def create_notification(
    *,
    tipo: str,
    titulo: str,
    mensagem: str,
    prioridade: str = NotificationPriority.MEDIA.value,
    entidade: str | None = None,
    entidade_id: str | int | None = None,
    url: str | None = None,
    usuario_destino: UserModel | None = None,
    destinatario_email: str | None = None,
    canal: str = NotificationChannel.INTERNA.value,
    dedupe_key: str | None = None,
    origem: str = "notification-scan",
    commit: bool = False,
) -> tuple[NotificationModel, bool]:
    # Cria uma notificação interna de forma idempotente
    # Retorna uma tupla com a notificação e um booleano indicando se uma nova linha foi criada
    existing = get_notification_by_dedupe_key(dedupe_key)
    if existing:
        return existing, False

    notification = NotificationModel(
        codigo=_next_code(),
        tipo_notificacao=tipo,
        titulo=titulo,
        mensagem=mensagem,
        prioridade=prioridade,
        status=NotificationStatus.PENDENTE.value,
        canal=canal,
        entidade=entidade,
        entidade_id=str(entidade_id) if entidade_id is not None else None,
        url=url,
        id_usuario_destino=(usuario_destino.id_usuario if usuario_destino else None),
        destinatario_email=(
            destinatario_email or (usuario_destino.email if usuario_destino else None)
        ),
        dedupe_key=dedupe_key,
        origem=origem,
    )
    db.session.add(notification)
    if commit:
        db.session.commit()
    return notification, True


def notify_recipients(
    recipients: Iterable[UserModel],
    *,
    tipo: str,
    titulo: str,
    mensagem: str,
    prioridade: str,
    entidade: str,
    entidade_id: int | str,
    url: str,
    dedupe_prefix: str,
) -> tuple[int, int]:
    created = 0
    skipped = 0
    for user in recipients:
        _, was_created = create_notification(
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            prioridade=prioridade,
            entidade=entidade,
            entidade_id=entidade_id,
            url=url,
            usuario_destino=user,
            dedupe_key=f"{dedupe_prefix}:{_recipient_key(user)}",
        )
        if was_created:
            created += 1
        else:
            skipped += 1
    return created, skipped


def scan_overdue_inventories(days: int = 30) -> tuple[int, int, int]:
    cutoff = _now() - timedelta(days=days)
    open_statuses = [
        InventoryStatus.RASCUNHO.value,
        InventoryStatus.EM_ANDAMENTO.value,
        InventoryStatus.COM_DIVERGENCIA.value,
        InventoryStatus.AGUARDANDO_ASSINATURA.value,
    ]
    inventories = db.session.execute(
        select(InventoryModel).where(
            InventoryModel.is_deleted == false(),
            InventoryModel.status.in_(open_statuses),
            InventoryModel.created_at < cutoff,
        )
    ).scalars().all()

    recipients = _active_recipients("notifications.view")
    created = skipped = 0
    for inventory in inventories:
        c, s = notify_recipients(
            recipients,
            tipo=NotificationType.INVENTARIO_VENCIDO.value,
            titulo=f"Inventário vencido: {inventory.codigo}",
            mensagem=(
                f"O inventário '{inventory.titulo}' está pendente há mais de {days} dias "
                f"e está com status {inventory.status}."
            ),
            prioridade=NotificationPriority.ALTA.value,
            entidade="inventory",
            entidade_id=inventory.id_inventory,
            url=f"/admin/inventories/{inventory.id_inventory}",
            dedupe_prefix=f"inventory-overdue:{inventory.id_inventory}:{inventory.status}:{days}",
        )
        created += c
        skipped += s
    return len(inventories), created, skipped


def scan_pending_transfers(days: int = 1) -> tuple[int, int, int]:
    cutoff = _now() - timedelta(days=days)
    pending_statuses = [
        TransferStatus.SOLICITADA.value,
        TransferStatus.AGUARDANDO_ORIGEM.value,
        TransferStatus.AGUARDANDO_DESTINO.value,
    ]
    transfers = db.session.execute(
        select(TransferModel).where(
            TransferModel.is_deleted == false(),
            TransferModel.status.in_(pending_statuses),
            TransferModel.created_at < cutoff,
        )
    ).scalars().all()

    recipients = _active_recipients("notifications.view")
    created = skipped = 0
    for transfer in transfers:
        c, s = notify_recipients(
            recipients,
            tipo=NotificationType.TRANSFERENCIA_PENDENTE.value,
            titulo=f"Transferência pendente: {transfer.codigo}",
            mensagem=(
                f"A transferência {transfer.codigo} está pendente no status {transfer.status}. "
                "Verifique confirmações de origem/destino ou cancele com justificativa."
            ),
            prioridade=NotificationPriority.MEDIA.value,
            entidade="transfer",
            entidade_id=transfer.id_transfer,
            url=f"/admin/transfers/{transfer.id_transfer}",
            dedupe_prefix=f"transfer-pending:{transfer.id_transfer}:{transfer.status}:{days}",
        )
        created += c
        skipped += s
    return len(transfers), created, skipped


def scan_pending_signatures() -> tuple[int, int, int]:
    recipients = _active_recipients("notifications.view")
    created = skipped = 0
    total_entities = 0

    inventories = db.session.execute(
        select(InventoryModel).where(
            InventoryModel.is_deleted == false(),
            InventoryModel.status == InventoryStatus.AGUARDANDO_ASSINATURA.value,
        )
    ).scalars().all()
    for inventory in inventories:
        total_entities += 1
        c, s = notify_recipients(
            recipients,
            tipo=NotificationType.ASSINATURA_PENDENTE.value,
            titulo=f"Inventário aguardando assinatura: {inventory.codigo}",
            mensagem=f"O inventário '{inventory.titulo}' está aguardando assinatura/finalização.",
            prioridade=NotificationPriority.ALTA.value,
            entidade="inventory",
            entidade_id=inventory.id_inventory,
            url=f"/admin/inventories/{inventory.id_inventory}",
            dedupe_prefix=f"signature-inventory:{inventory.id_inventory}:{inventory.status}",
        )
        created += c
        skipped += s

    occurrences = db.session.execute(
        select(OccurrenceModel).where(
            OccurrenceModel.is_deleted == false(),
            OccurrenceModel.status == OccurrenceStatus.AGUARDANDO_APROVACAO.value,
        )
    ).scalars().all()
    for occurrence in occurrences:
        total_entities += 1
        c, s = notify_recipients(
            recipients,
            tipo=NotificationType.ASSINATURA_PENDENTE.value,
            titulo=f"Ocorrência aguardando aprovação: {occurrence.codigo}",
            mensagem=f"A ocorrência {occurrence.codigo} exige aprovação/decisão.",
            prioridade=NotificationPriority.ALTA.value,
            entidade="occurrence",
            entidade_id=occurrence.id_occurrence,
            url=f"/admin/occurrences/{occurrence.id_occurrence}",
            dedupe_prefix=f"signature-occurrence:{occurrence.id_occurrence}:{occurrence.status}",
        )
        created += c
        skipped += s

    transfer_statuses = [
        TransferStatus.AGUARDANDO_ORIGEM.value,
        TransferStatus.AGUARDANDO_DESTINO.value,
    ]
    transfers = db.session.execute(
        select(TransferModel).where(
            TransferModel.is_deleted == false(),
            TransferModel.status.in_(transfer_statuses),
        )
    ).scalars().all()
    for transfer in transfers:
        total_entities += 1
        c, s = notify_recipients(
            recipients,
            tipo=NotificationType.ASSINATURA_PENDENTE.value,
            titulo=f"Transferência aguardando confirmação: {transfer.codigo}",
            mensagem=(
                f"A transferência {transfer.codigo} aguarda confirmação "
                f"no status {transfer.status}."
            ),
            prioridade=NotificationPriority.MEDIA.value,
            entidade="transfer",
            entidade_id=transfer.id_transfer,
            url=f"/admin/transfers/{transfer.id_transfer}",
            dedupe_prefix=f"signature-transfer:{transfer.id_transfer}:{transfer.status}",
        )
        created += c
        skipped += s

    return total_entities, created, skipped


def scan_critical_divergences() -> tuple[int, int, int]:
    critical_types = {
        "ferramenta_faltante",
        "ferramenta_danificada",
        "ferramenta_baixada_encontrada",
        "transferencia_pendente",
        "custodia_inconsistente",
    }
    divergences = db.session.execute(
        select(InventoryDivergenceModel).where(
            InventoryDivergenceModel.is_deleted == false(),
            InventoryDivergenceModel.status == InventoryDivergenceStatus.ABERTA.value,
            (
                InventoryDivergenceModel.severidade.in_(["alta", "critica"])
                | InventoryDivergenceModel.tipo_divergencia.in_(critical_types)
            ),
        )
    ).scalars().all()

    recipients = _active_recipients("notifications.view")
    created = skipped = 0
    for divergence in divergences:
        c, s = notify_recipients(
            recipients,
            tipo=NotificationType.DIVERGENCIA_CRITICA.value,
            titulo=f"Divergência crítica no inventário {divergence.inventory.codigo}",
            mensagem=(
                f"Divergência aberta: {divergence.tipo_divergencia}. "
                "Regularize para liberar o inventário."
            ),
            prioridade=NotificationPriority.CRITICA.value,
            entidade="inventory_divergence",
            entidade_id=divergence.id_inventory_divergence,
            url=f"/admin/inventories/{divergence.id_inventory}",
            dedupe_prefix=(
                f"critical-divergence:{divergence.id_inventory_divergence}:{divergence.status}"
            ),
        )
        created += c
        skipped += s
    return len(divergences), created, skipped


def run_notification_scan(
    *,
    inventory_overdue_days: int = 30,
    transfer_pending_days: int = 1,
) -> NotificationScanSummary:
    inv_total, inv_created, inv_skipped = scan_overdue_inventories(inventory_overdue_days)
    tr_total, tr_created, tr_skipped = scan_pending_transfers(transfer_pending_days)
    sig_total, sig_created, sig_skipped = scan_pending_signatures()
    div_total, div_created, div_skipped = scan_critical_divergences()

    created = inv_created + tr_created + sig_created + div_created
    skipped = inv_skipped + tr_skipped + sig_skipped + div_skipped
    db.session.commit()

    record_audit_log(
        action="notifications.scan",
        entity="notification",
        entity_id="scheduler",
        after={
            "created": created,
            "skipped_existing": skipped,
            "inventories_overdue": inv_total,
            "transfers_pending": tr_total,
            "signatures_pending": sig_total,
            "critical_divergences": div_total,
        },
        reason="Varredura de notificações sem Redis executada por CLI ou usuário autorizado.",
        commit=True,
    )
    return NotificationScanSummary(
        created=created,
        skipped_existing=skipped,
        inventories_overdue=inv_total,
        transfers_pending=tr_total,
        signatures_pending=sig_total,
        critical_divergences=div_total,
    )


def mark_as_read(notification: NotificationModel, user: UserModel | None = None) -> None:
    if notification.status == NotificationStatus.LIDA.value:
        return
    if user and notification.id_usuario_destino not in {None, user.id_usuario}:
        raise ValueError("Notificação não pertence ao usuário informado.")
    notification.status = NotificationStatus.LIDA.value
    notification.lida_em = _now()
    db.session.commit()


def _gateway_mail_configured() -> bool:
    return bool(
        current_app.config.get("NOTIFICATIONS_EMAIL_ENABLED")
        and current_app.config.get("BRASIF_GATEWAY_BASE_URL")
        and current_app.config.get("BRASIF_GATEWAY_API_KEY")
    )


def build_gateway_mail_client() -> BrasifGatewayMailClient:
    return BrasifGatewayMailClient(
        base_url=current_app.config.get("BRASIF_GATEWAY_BASE_URL", ""),
        api_key=current_app.config.get("BRASIF_GATEWAY_API_KEY", ""),
        timeout_seconds=int(
            current_app.config.get("BRASIF_GATEWAY_TIMEOUT_SECONDS", 10)
        ),
        verify_ssl=bool(current_app.config.get("BRASIF_GATEWAY_VERIFY_SSL", True)),
        max_retries=int(current_app.config.get("BRASIF_GATEWAY_MAX_RETRIES", 2)),
        retry_backoff_seconds=float(
            current_app.config.get("BRASIF_GATEWAY_RETRY_BACKOFF_SECONDS", 0.25)
        ),
    )


def _notification_email_body(notification: NotificationModel) -> str:
    lines = [
        notification.mensagem,
        "",
        f"Código da notificação: {notification.codigo}",
        f"Prioridade: {notification.prioridade}",
    ]
    if notification.entidade:
        lines.append(
            f"Entidade relacionada: {notification.entidade} "
            f"#{notification.entidade_id or '-'}"
        )
    if notification.url:
        lines.extend(["", f"Acesse no sistema: {notification.url}"])
    return "\n".join(lines)


def _build_notification_mail_message(notification: NotificationModel):
    recipient = notification.destinatario_email or (
        notification.usuario_destino.email if notification.usuario_destino else ""
    )
    return build_gateway_mail_message(
        sender_email=current_app.config.get("MAIL_DEFAULT_SENDER") or None,
        subject=notification.titulo,
        body=_notification_email_body(notification),
        to_recipients=[recipient],
        cc_recipients=[],
        is_html=False,
        attachments=[],
        max_recipients=int(current_app.config.get("MAIL_MAX_RECIPIENTS", 50)),
        max_body_length=int(current_app.config.get("MAIL_MAX_BODY_LENGTH", 50000)),
        max_attachment_mb=int(current_app.config.get("MAIL_MAX_ATTACHMENT_MB", 10)),
    )


def _delivery_status_for_error(exc: Exception) -> str:
    if isinstance(exc, GatewayMailValidationError | GatewayMailPermanentError):
        return "failed_permanent"
    if isinstance(exc, GatewayMailAuthError | GatewayMailConfigError):
        return "failed_config"
    if isinstance(exc, GatewayMailTimeoutError | GatewayMailTransientError):
        return "failed_transient"
    return "failed"


def _notification_status_for_error(exc: Exception) -> str:
    if isinstance(
        exc,
        GatewayMailValidationError | GatewayMailPermanentError | GatewayMailConfigError,
    ):
        return NotificationStatus.FALHA.value
    return NotificationStatus.PENDENTE.value


def _audit_email_attempt(
    notification: NotificationModel,
    *,
    status: str,
    attempted_at: datetime,
    response: GatewayMailResponse | None = None,
    error: Exception | None = None,
    commit: bool = False,
) -> None:
    recipient = notification.destinatario_email or (
        notification.usuario_destino.email if notification.usuario_destino else None
    )
    http_status = response.status_code if response else getattr(error, "status_code", None)
    attempts = response.attempts if response else getattr(error, "attempts", 1)
    duration_ms = response.duration_ms if response else getattr(error, "duration_ms", None)
    error_summary = str(error)[:300] if error else None
    record_audit_log(
        action="notifications.email_send",
        entity=notification.entidade or "notification",
        entity_id=notification.entidade_id or str(notification.id_notification),
        before=None,
        after={
            "notification_id": notification.id_notification,
            "notification_code": notification.codigo,
            "notification_type": notification.tipo_notificacao,
            "subject": notification.titulo,
            "to_recipients": summarize_recipients([recipient] if recipient else []),
            "cc_recipients": summarize_recipients([]),
            "status": status,
            "http_status": http_status,
            "attempts": attempts,
            "duration_ms": duration_ms,
            "attempted_at": attempted_at.isoformat(),
            "error": error_summary,
        },
        reason="Envio de e-mail via Brasif Gateway Microsoft Graph.",
        commit=commit,
    )


def _send_email(
    notification: NotificationModel,
    *,
    client: BrasifGatewayMailClient | None = None,
) -> GatewayMailResponse:
    if not _gateway_mail_configured():
        raise GatewayMailConfigError("Envio de e-mail via Brasif Gateway não configurado.")

    message = _build_notification_mail_message(notification)
    mail_client = client or build_gateway_mail_client()
    return mail_client.send(message)


def send_pending_email_notifications(
    limit: int = 50,
    dry_run: bool = False,
    *,
    client: BrasifGatewayMailClient | None = None,
) -> NotificationSendSummary:
    pending = list_pending_email_notifications(limit)
    if not current_app.config.get("NOTIFICATIONS_EMAIL_ENABLED") and not dry_run:
        return NotificationSendSummary(sent=0, failed=0, skipped=len(pending))

    sent = failed = skipped = 0
    for notification in pending:
        attempted_at = _now()
        notification.tentativas_envio += 1
        notification.ultima_tentativa_em = attempted_at
        recipient = notification.destinatario_email or (
            notification.usuario_destino.email if notification.usuario_destino else None
        )
        masked_recipient = mask_email(recipient)

        if dry_run:
            add_delivery(
                NotificationDeliveryModel(
                    id_notification=notification.id_notification,
                    canal=NotificationChannel.EMAIL.value,
                    destino=masked_recipient,
                    status="dry_run",
                    resposta="Envio simulado.",
                    attempted_at=attempted_at,
                    sent_at=None,
                )
            )
            skipped += 1
            continue

        try:
            response = _send_email(notification, client=client)
        except GatewayMailError as exc:
            notification.status = _notification_status_for_error(exc)
            notification.erro_envio = str(exc)[:2000]
            add_delivery(
                NotificationDeliveryModel(
                    id_notification=notification.id_notification,
                    canal=NotificationChannel.EMAIL.value,
                    destino=masked_recipient,
                    status=_delivery_status_for_error(exc),
                    resposta=str(exc)[:2000],
                    attempted_at=attempted_at,
                    sent_at=None,
                )
            )
            _audit_email_attempt(
                notification,
                status="failed",
                attempted_at=attempted_at,
                error=exc,
            )
            failed += 1
        except Exception as exc:
            notification.erro_envio = "Falha inesperada no envio da notificação."
            add_delivery(
                NotificationDeliveryModel(
                    id_notification=notification.id_notification,
                    canal=NotificationChannel.EMAIL.value,
                    destino=masked_recipient,
                    status="failed_unexpected",
                    resposta="Falha inesperada no envio da notificação.",
                    attempted_at=attempted_at,
                    sent_at=None,
                )
            )
            _audit_email_attempt(
                notification,
                status="failed",
                attempted_at=attempted_at,
                error=exc,
            )
            failed += 1
        else:
            notification.status = NotificationStatus.ENVIADA.value
            notification.enviada_em = _now()
            notification.erro_envio = None
            add_delivery(
                NotificationDeliveryModel(
                    id_notification=notification.id_notification,
                    canal=NotificationChannel.EMAIL.value,
                    destino=masked_recipient,
                    status="sent",
                    resposta=(
                        f"E-mail enviado via gateway. HTTP {response.status_code}; "
                        f"tentativas: {response.attempts}."
                    ),
                    attempted_at=attempted_at,
                    sent_at=notification.enviada_em,
                )
            )
            _audit_email_attempt(
                notification,
                status="sent",
                attempted_at=attempted_at,
                response=response,
            )
            sent += 1

    db.session.commit()
    return NotificationSendSummary(sent=sent, failed=failed, skipped=skipped)


def user_can_see_all_notifications() -> bool:
    if not getattr(current_user, "is_authenticated", False):
        return False
    from app.permissions.services import current_user_can

    return current_user_can("notifications.manage")
