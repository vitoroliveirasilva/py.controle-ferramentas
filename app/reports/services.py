from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from flask import current_app

from app.audit.services import record_audit_log
from app.inventories.models import InventoryDivergenceModel, InventoryModel
from app.occurrences.models import OccurrenceModel
from app.reports import repositories as repo
from app.tools.models import ToolModel
from app.transfers.models import TransferModel
from app.users.models import UserModel


@dataclass(frozen=True)
class ReportDefinition:
    code: str
    title: str
    description: str
    sensitive: bool
    builder: Callable[[dict[str, str], UserModel | None], list[dict[str, Any]]]


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "sim" if value else "não"


def _custody_label(custody) -> str:
    if not custody:
        return "Sem custódia atual"
    parts = [custody.tipo_custodia]
    if custody.responsavel_snapshot:
        parts.append(custody.responsavel_snapshot)
    if custody.local_snapshot:
        parts.append(custody.local_snapshot)
    return " / ".join(parts)


def _tool_row(tool: ToolModel, custody=None) -> dict[str, Any]:
    return {
        "codigo_interno": tool.codigo_interno,
        "nome": tool.nome,
        "categoria": tool.categoria.nome if tool.categoria else "",
        "status": tool.status,
        "criticidade": tool.criticidade,
        "ativo_imobilizado": tool.ativo_imobilizado or "",
        "numero_serie": tool.numero_serie or "",
        "marca": tool.marca or "",
        "modelo": tool.modelo or "",
        "controle_individual": _bool(tool.controle_individual),
        "requer_calibracao": _bool(tool.requer_calibracao),
        "ativo": _bool(tool.ativo),
        "custodia_atual": _custody_label(custody),
        "responsavel_atual": custody.responsavel_snapshot if custody else "",
        "local_atual": custody.local_snapshot if custody else "",
        "inicio_custodia": _iso(custody.inicio_em) if custody else "",
    }


def current_situation_rows(
    filters: dict[str, str],
    user: UserModel | None = None,
) -> list[dict[str, Any]]:
    category_id_raw = filters.get("categoria", "")
    category_id = int(category_id_raw) if category_id_raw.isdigit() else None
    rows = repo.fetch_current_situation(
        search=filters.get("q") or None,
        status=filters.get("status") or None,
        category_id=category_id,
        user=user,
    )
    return [_tool_row(tool, custody) for tool, custody in rows]


def asset_tools_rows(
    _filters: dict[str, str],
    user: UserModel | None = None,
) -> list[dict[str, Any]]:
    return [
        row
        for row in current_situation_rows({}, user)
        if row["ativo_imobilizado"]
    ]


def inventory_rows(filters: dict[str, str], user: UserModel | None = None) -> list[dict[str, Any]]:
    inventories = repo.fetch_inventories(
        status=filters.get("status") or None,
        inventory_type=filters.get("tipo") or None,
        user=user,
    )
    return [_inventory_row(inventory) for inventory in inventories]


def _inventory_row(inventory: InventoryModel) -> dict[str, Any]:
    total_items = len(inventory.itens or [])
    open_divergences = sum(
        1 for divergence in inventory.divergencias or [] if divergence.status == "aberta"
    )
    return {
        "codigo": inventory.codigo,
        "titulo": inventory.titulo,
        "tipo": inventory.tipo_inventario,
        "status": inventory.status,
        "escopo_tipo": inventory.escopo_tipo,
        "escopo_responsavel": inventory.escopo_responsavel_snapshot or "",
        "escopo_local": inventory.escopo_local_snapshot or "",
        "itens": total_items,
        "divergencias_abertas": open_divergences,
        "criado_por": inventory.criado_por.email if inventory.criado_por else "",
        "iniciado_em": _iso(inventory.iniciado_em),
        "finalizado_em": _iso(inventory.finalizado_em),
        "cancelado_em": _iso(inventory.cancelado_em),
    }


def divergence_rows(filters: dict[str, str], user: UserModel | None = None) -> list[dict[str, Any]]:
    divergences = repo.fetch_divergences(status=filters.get("status") or None, user=user)
    return [_divergence_row(divergence) for divergence in divergences]


def _divergence_row(divergence: InventoryDivergenceModel) -> dict[str, Any]:
    return {
        "inventario": divergence.inventory.codigo if divergence.inventory else "",
        "ferramenta": divergence.tool.codigo_interno if divergence.tool else "",
        "nome_ferramenta": divergence.tool.nome if divergence.tool else "",
        "tipo_divergencia": divergence.tipo_divergencia,
        "status": divergence.status,
        "severidade": divergence.severidade,
        "descricao": divergence.descricao,
        "acao_regularizacao": divergence.acao_regularizacao or "",
        "resolucao": divergence.resolucao or "",
        "aberta_em": _iso(divergence.aberta_em),
        "regularizada_em": _iso(divergence.regularizada_em),
    }


def transfer_rows(filters: dict[str, str], user: UserModel | None = None) -> list[dict[str, Any]]:
    transfers = repo.fetch_transfers(status=filters.get("status") or None, user=user)
    return [_transfer_row(transfer) for transfer in transfers]


def _transfer_row(transfer: TransferModel) -> dict[str, Any]:
    return {
        "codigo": transfer.codigo,
        "tipo": transfer.tipo_transferencia,
        "status": transfer.status,
        "destino": transfer.destino_responsavel_snapshot,
        "destino_local": transfer.destino_local_snapshot or "",
        "quantidade_itens": len(transfer.itens or []),
        "ferramentas": ", ".join(item.tool.codigo_interno for item in transfer.itens if item.tool),
        "motivo": transfer.motivo,
        "solicitado_em": _iso(transfer.solicitado_em),
        "origem_confirmada_em": _iso(transfer.origem_confirmada_em),
        "destino_confirmado_em": _iso(transfer.destino_confirmado_em),
        "recusado_em": _iso(transfer.recusado_em),
        "cancelado_em": _iso(transfer.cancelado_em),
    }


def occurrence_rows(filters: dict[str, str], user: UserModel | None = None) -> list[dict[str, Any]]:
    occurrences = repo.fetch_occurrences(
        status=filters.get("status") or None,
        occurrence_type=filters.get("tipo") or None,
        user=user,
    )
    return [_occurrence_row(occurrence) for occurrence in occurrences]


def _occurrence_row(occurrence: OccurrenceModel) -> dict[str, Any]:
    return {
        "codigo": occurrence.codigo,
        "ferramenta": occurrence.tool.codigo_interno if occurrence.tool else "",
        "nome_ferramenta": occurrence.tool.nome if occurrence.tool else "",
        "tipo": occurrence.tipo_ocorrencia,
        "status": occurrence.status,
        "motivo": occurrence.motivo,
        "impacto_patrimonial": _bool(occurrence.impacto_patrimonial),
        "ativo_imobilizado": occurrence.ativo_imobilizado_snapshot or "",
        "registrante": occurrence.registrante_email or "",
        "registrado_em": _iso(occurrence.registrado_em),
        "aprovado_em": _iso(occurrence.aprovado_em),
        "resolvido_em": _iso(occurrence.resolvido_em),
    }


def tool_history_rows(
    filters: dict[str, str],
    user: UserModel | None = None,
) -> list[dict[str, Any]]:
    tool = repo.find_tool_for_history(filters.get("q"), user=user)
    if not tool:
        return []
    return [
        {
            "codigo_interno": tool.codigo_interno,
            "ferramenta": tool.nome,
            "evento": event.event_type,
            "titulo": event.titulo,
            "descricao": event.descricao or "",
            "ator": event.actor_email or "",
            "ocorrido_em": _iso(event.occurred_at),
            "correlation_id": event.correlation_id or "",
        }
        for event in repo.fetch_tool_history(tool.id_tool)
    ]


def report_definitions() -> dict[str, ReportDefinition]:
    definitions = (
        ReportDefinition(
            "situacao-atual",
            "Situação atual",
            "Ferramentas, status e custódia atual.",
            True,
            current_situation_rows,
        ),
        ReportDefinition(
            "historico-ferramenta",
            "Histórico por ferramenta",
            "Linha do tempo operacional de uma ferramenta.",
            True,
            tool_history_rows,
        ),
        ReportDefinition(
            "inventarios",
            "Inventários realizados e pendentes",
            "Inventários por status, escopo e tipo.",
            True,
            inventory_rows,
        ),
        ReportDefinition(
            "divergencias",
            "Divergências",
            "Divergências abertas, regularizadas e justificadas.",
            True,
            divergence_rows,
        ),
        ReportDefinition(
            "transferencias",
            "Transferências",
            "Transferências pendentes, concluídas, recusadas e canceladas.",
            True,
            transfer_rows,
        ),
        ReportDefinition(
            "ocorrencias",
            "Baixas, substituições e ocorrências",
            "Eventos de perda, dano, baixa, substituição e manutenção.",
            True,
            occurrence_rows,
        ),
        ReportDefinition(
            "ativos-imobilizados",
            "Ferramentas com ativo imobilizado",
            "Ferramentas com vínculo patrimonial e custódia atual.",
            True,
            asset_tools_rows,
        ),
    )
    return {definition.code: definition for definition in definitions}


def build_report_rows(
    report_code: str,
    filters: dict[str, str],
    *,
    user: UserModel | None = None,
) -> tuple[ReportDefinition, list[dict[str, Any]]]:
    definitions = report_definitions()
    if report_code not in definitions:
        raise ValueError("Relatório não encontrado.")
    definition = definitions[report_code]
    return definition, definition.builder(filters, user)


def enforce_report_export_limit(rows_count: int) -> None:
    max_rows = int(current_app.config.get("REPORT_EXPORT_MAX_ROWS", 500))
    if rows_count > max_rows:
        raise ValueError(
            f"Exportação limitada a {max_rows} linha(s). Refine os filtros do relatório."
        )


def record_report_export(
    report_code: str,
    export_format: str,
    rows_count: int,
    filters: dict[str, str] | None = None,
) -> None:
    record_audit_log(
        action="reports.export",
        entity="report",
        entity_id=report_code,
        after={"formato": export_format, "linhas": rows_count, "filtros": filters or {}},
        reason="Exportação de relatório sensível.",
        commit=True,
    )
