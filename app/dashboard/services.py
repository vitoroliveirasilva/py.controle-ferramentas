from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask_login import current_user

from app.dashboard import repositories as repo


@dataclass(frozen=True)
class DashboardCard:
    title: str
    value: int
    description: str
    level: str
    url: str | None = None


@dataclass(frozen=True)
class DashboardData:
    cards: list[DashboardCard]
    tools_by_status: list[dict[str, Any]]
    tools_by_criticality: list[dict[str, Any]]
    recent_divergences: list[Any]
    pending_transfers: list[Any]
    pending_inventories: list[Any]
    top_reincidences: list[dict[str, Any]]
    transfer_age_buckets: list[dict[str, Any]]
    scope_description: str


def _scope_description(tool_ids: list[int] | None) -> str:
    if tool_ids is None:
        return "Escopo global"
    if not tool_ids:
        return "Sem ferramentas dentro do seu escopo atual"
    return f"Escopo aplicado a {len(tool_ids)} ferramenta(s)"


def build_dashboard_data() -> DashboardData:
    tool_ids = repo.scoped_tool_filter(current_user)

    total_tools = repo.total_tools(tool_ids)
    open_divergences = repo.count_open_divergences(tool_ids)
    pending_transfers = repo.count_pending_transfers(tool_ids)
    pending_inventories = repo.count_pending_inventories(tool_ids)
    overdue_inventories = repo.count_overdue_inventories(tool_ids=tool_ids)
    waiting_signature = repo.count_inventories_waiting_signature(tool_ids)
    critical_occurrences = repo.count_critical_occurrences(tool_ids)
    patrimonial_events = repo.count_patrimonial_events(tool_ids)
    without_custody = repo.active_tools_without_custody(tool_ids)

    cards = [
        DashboardCard(
            "Ferramentas controladas",
            total_tools,
            "Total visível conforme seu escopo de acesso.",
            "neutral",
            "tools.index",
        ),
        DashboardCard(
            "Divergências abertas",
            open_divergences,
            "Pendências de inventário que ainda exigem ação.",
            "danger" if open_divergences else "success",
            "inventories.index",
        ),
        DashboardCard(
            "Transferências pendentes",
            pending_transfers,
            "Processos aguardando confirmação, recusa ou cancelamento.",
            "warning" if pending_transfers else "success",
            "transfers.index",
        ),
        DashboardCard(
            "Inventários pendentes",
            pending_inventories,
            "Rascunhos, conferências em andamento e inventários aguardando assinatura.",
            "warning" if pending_inventories else "success",
            "inventories.index",
        ),
        DashboardCard(
            "Inventários vencidos",
            overdue_inventories,
            "Critério inicial: inventários abertos há mais de 30 dias.",
            "danger" if overdue_inventories else "success",
            "inventories.index",
        ),
        DashboardCard(
            "Aguardando assinatura",
            waiting_signature,
            "Inventários prontos para confirmação formal.",
            "warning" if waiting_signature else "success",
            "signatures.index",
        ),
        DashboardCard(
            "Ocorrências críticas",
            critical_occurrences,
            "Ocorrências abertas, em análise ou aguardando aprovação.",
            "danger" if critical_occurrences else "success",
            "occurrences.index",
        ),
        DashboardCard(
            "Eventos patrimoniais",
            patrimonial_events,
            "Ocorrências com impacto patrimonial registrado.",
            "warning" if patrimonial_events else "neutral",
            "occurrences.index",
        ),
        DashboardCard(
            "Ativas sem custódia",
            without_custody,
            "Ferramentas ativas que ainda precisam de responsável/local atual.",
            "danger" if without_custody else "success",
            "custody.missing_custody",
        ),
    ]

    return DashboardData(
        cards=cards,
        tools_by_status=repo.count_tools_by_status(tool_ids),
        tools_by_criticality=repo.count_tools_by_criticality(tool_ids),
        recent_divergences=repo.recent_open_divergences(tool_ids=tool_ids),
        pending_transfers=repo.pending_transfers(tool_ids=tool_ids),
        pending_inventories=repo.pending_inventories(tool_ids=tool_ids),
        top_reincidences=repo.top_reincidences(tool_ids=tool_ids),
        transfer_age_buckets=repo.transfer_sla_buckets(tool_ids=tool_ids),
        scope_description=_scope_description(tool_ids),
    )
