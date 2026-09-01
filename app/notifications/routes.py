from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.core.pagination import clamp_page, paginate
from app.models.enums import NotificationStatus
from app.notifications.forms import NotificationScanForm, NotificationSendForm
from app.notifications.repositories import (
    base_notification_query,
    get_notification_by_id,
)
from app.notifications.services import (
    mark_as_read,
    run_notification_scan,
    send_pending_email_notifications,
    user_can_see_all_notifications,
)
from app.permissions.decorators import permission_required
from app.permissions.scope_filters import is_global_scope

bp = Blueprint("notifications", __name__, url_prefix="/admin/notifications")


def _can_manage_all_notifications_by_scope() -> bool:
    return user_can_see_all_notifications() and is_global_scope(current_user)


@bp.get("/")
@permission_required("notifications.view")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    can_manage_all = _can_manage_all_notifications_by_scope()
    only_user_id = None if can_manage_all else current_user.id_usuario
    result = paginate(
        base_notification_query(search, status, only_user_id),
        page=page,
        per_page=20,
    )
    return render_template(
        "notifications/index.html",
        page=result,
        search=search,
        status=status,
        statuses=NotificationStatus.choices(),
        scan_form=NotificationScanForm(),
        send_form=NotificationSendForm(),
        can_manage=can_manage_all,
    )


@bp.get("/<int:notification_id>")
@permission_required("notifications.view")
def detail(notification_id: int):
    notification = get_notification_by_id(notification_id)
    if not notification or notification.is_deleted:
        flash("Notificação não encontrada.", "warning")
        return redirect(url_for("notifications.index"))
    if (
        not _can_manage_all_notifications_by_scope()
        and notification.id_usuario_destino != current_user.id_usuario
    ):
        flash("Você não tem acesso a esta notificação.", "danger")
        return redirect(url_for("notifications.index"))
    return render_template("notifications/detail.html", notification=notification)


@bp.post("/<int:notification_id>/read")
@permission_required("notifications.view")
def mark_read(notification_id: int):
    notification = get_notification_by_id(notification_id)
    if not notification or notification.is_deleted:
        flash("Notificação não encontrada.", "warning")
        return redirect(url_for("notifications.index"))
    try:
        mark_as_read(
            notification,
            None if _can_manage_all_notifications_by_scope() else current_user,
        )
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Notificação marcada como lida.", "success")
    return redirect(url_for("notifications.detail", notification_id=notification_id))


@bp.post("/scan")
@permission_required("notifications.manage")
def scan():
    form = NotificationScanForm()
    if form.validate_on_submit():
        summary = run_notification_scan(
            inventory_overdue_days=form.inventory_overdue_days.data,
            transfer_pending_days=form.transfer_pending_days.data,
        )
        flash(
            "Varredura concluída: "
            f"{summary.created} novas, {summary.skipped_existing} já existentes.",
            "success",
        )
    else:
        flash("Parâmetros inválidos para varredura.", "danger")
    return redirect(url_for("notifications.index"))


@bp.post("/send-pending")
@permission_required("notifications.manage")
def send_pending():
    form = NotificationSendForm()
    if form.validate_on_submit():
        summary = send_pending_email_notifications(
            limit=form.limit.data,
            dry_run=bool(form.dry_run.data),
        )
        flash(
            "Envio processado: "
            f"{summary.sent} enviados, {summary.failed} falhas, "
            f"{summary.skipped} ignorados/simulados.",
            "success",
        )
    else:
        flash("Parâmetros inválidos para envio.", "danger")
    return redirect(url_for("notifications.index"))
