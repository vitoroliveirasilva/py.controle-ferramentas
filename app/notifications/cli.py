from __future__ import annotations

import click
from flask import Flask

from app.notifications.services import (
    run_notification_scan,
    send_pending_email_notifications,
)


@click.command("notifications-scan")
@click.option("--inventory-overdue-days", default=30, show_default=True, type=int)
@click.option("--transfer-pending-days", default=1, show_default=True, type=int)
def notifications_scan_command(
    inventory_overdue_days: int, transfer_pending_days: int
) -> None:
    # Gera notificações para itens operacionais pendentes
    summary = run_notification_scan(
        inventory_overdue_days=inventory_overdue_days,
        transfer_pending_days=transfer_pending_days,
    )
    click.echo(
        "Varredura concluída: "
        f"{summary.created} novas, "
        f"{summary.skipped_existing} existentes, "
        f"{summary.inventories_overdue} inventários vencidos, "
        f"{summary.transfers_pending} transferências pendentes, "
        f"{summary.signatures_pending} assinaturas pendentes, "
        f"{summary.critical_divergences} divergências críticas."
    )


@click.command("notifications-send-pending")
@click.option("--limit", default=50, show_default=True, type=int)
@click.option(
    "--dry-run", is_flag=True, help="Registra tentativa simulada sem enviar e-mail."
)
def notifications_send_pending_command(limit: int, dry_run: bool) -> None:
    # Envia notificações por e-mail que estão pendentes
    # O limite e a opção de simulação (dry-run) são respeitados
    summary = send_pending_email_notifications(limit=limit, dry_run=dry_run)
    click.echo(
        "Envio processado: "
        f"{summary.sent} enviados, {summary.failed} falhas, {summary.skipped} ignorados/simulados."
    )


def register_notification_commands(app: Flask) -> None:
    app.cli.add_command(notifications_scan_command)
    app.cli.add_command(notifications_send_pending_command)
