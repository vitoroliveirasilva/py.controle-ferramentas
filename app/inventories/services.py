from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import current_app
from flask_login import current_user
from sqlalchemy import false, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from werkzeug.datastructures import FileStorage

from app.audit.services import record_audit_log
from app.core.uploads import remove_upload_file, safe_upload_path, store_upload
from app.custody.models import ToolCustodyModel, ToolTimelineEventModel
from app.extensions import db
from app.inventories.models import (
    InventoryDivergenceModel,
    InventoryItemEvidenceModel,
    InventoryItemModel,
    InventoryModel,
)
from app.inventories.repositories import (
    count_open_inventory_divergences,
    find_inventory_item_by_identifier,
    find_open_item_divergence,
    has_pending_inventory_items,
)
from app.locations.repositories import get_location_by_id
from app.models.enums import (
    InventoryDivergenceAction,
    InventoryDivergenceStatus,
    InventoryDivergenceType,
    InventoryItemStatus,
    InventoryScopeType,
    InventoryStatus,
    InventoryType,
    OccurrenceStatus,
    OccurrenceType,
    SignatureAction,
    SignatureResult,
    ToolStatus,
    ToolTimelineEventType,
    TransferStatus,
)
from app.occurrences.models import OccurrenceModel
from app.permissions.scope_filters import (
    ScopeAccessDenied,
    assert_can_access_inventory_scope,
)
from app.signatures.services import record_internal_signature
from app.tools.models import ToolModel
from app.tools.repositories import get_tool_by_any_identifier
from app.transfers.models import TransferItemModel, TransferModel
from app.users.repositories import get_user_by_id

OPEN_INVENTORY_STATUSES = {
    InventoryStatus.RASCUNHO.value,
    InventoryStatus.EM_ANDAMENTO.value,
    InventoryStatus.COM_DIVERGENCIA.value,
}
DIVERGENCE_ITEM_STATUSES = {
    InventoryItemStatus.FALTANTE.value,
    InventoryItemStatus.EXCEDENTE.value,
    InventoryItemStatus.DANIFICADO.value,
    InventoryItemStatus.SUBSTITUIDO.value,
}
BLOCKED_TOOL_STATUSES = {
    ToolStatus.BAIXADA.value,
    ToolStatus.INATIVA.value,
    ToolStatus.TRANSFERENCIA.value,
}
ITEM_STATUS_TO_DIVERGENCE_TYPE = {
    InventoryItemStatus.FALTANTE.value: InventoryDivergenceType.FERRAMENTA_FALTANTE.value,
    InventoryItemStatus.EXCEDENTE.value: InventoryDivergenceType.FERRAMENTA_EXCEDENTE.value,
    InventoryItemStatus.DANIFICADO.value: InventoryDivergenceType.FERRAMENTA_DANIFICADA.value,
    InventoryItemStatus.SUBSTITUIDO.value: (
        InventoryDivergenceType.SUBSTITUICAO_NAO_REGISTRADA.value
    ),
}
DIVERGENCE_SEVERITY = {
    InventoryDivergenceType.FERRAMENTA_FALTANTE.value: "alta",
    InventoryDivergenceType.FERRAMENTA_EXCEDENTE.value: "media",
    InventoryDivergenceType.FERRAMENTA_DANIFICADA.value: "alta",
    InventoryDivergenceType.SUBSTITUICAO_NAO_REGISTRADA.value: "alta",
    InventoryDivergenceType.FERRAMENTA_BAIXADA_ENCONTRADA.value: "alta",
    InventoryDivergenceType.TRANSFERENCIA_PENDENTE.value: "alta",
    InventoryDivergenceType.CUSTODIA_INCONSISTENTE.value: "alta",
    InventoryDivergenceType.CODIGO_DIVERGENTE.value: "media",
    InventoryDivergenceType.ATIVO_IMOBILIZADO_DIVERGENTE.value: "media",
}
ACTIONS_THAT_KEEP_STATUS_JUSTIFIED = {
    InventoryDivergenceAction.JUSTIFICAR_COM_APROVACAO.value,
}
ACTIONS_THAT_CANCEL = {
    InventoryDivergenceAction.CANCELAR_PROCESSO_COM_MOTIVO.value,
}
ACTIONS_THAT_OPEN_OCCURRENCE = {
    InventoryDivergenceAction.ABRIR_OCORRENCIA.value,
    InventoryDivergenceAction.BAIXAR_POR_PERDA.value,
    InventoryDivergenceAction.REGISTRAR_DANO.value,
    InventoryDivergenceAction.REGISTRAR_SUBSTITUICAO.value,
    InventoryDivergenceAction.REINTEGRAR_FERRAMENTA.value,
}
OCCURRENCE_ACTION_TYPE = {
    InventoryDivergenceAction.ABRIR_OCORRENCIA.value: (
        OccurrenceType.REGULARIZACAO_CADASTRAL.value
    ),
    InventoryDivergenceAction.BAIXAR_POR_PERDA.value: OccurrenceType.PERDA.value,
    InventoryDivergenceAction.REGISTRAR_DANO.value: OccurrenceType.DANO.value,
    InventoryDivergenceAction.REGISTRAR_SUBSTITUICAO.value: (
        OccurrenceType.SUBSTITUICAO.value
    ),
    InventoryDivergenceAction.REINTEGRAR_FERRAMENTA.value: OccurrenceType.REINTEGRACAO.value,
}
TRANSFER_CLOSING_STATUSES = {
    TransferStatus.CONCLUIDA.value,
    TransferStatus.AGUARDANDO_DESTINO.value,
    TransferStatus.AGUARDANDO_ORIGEM.value,
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def _json_dumps(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _actor_id() -> int | None:
    if not getattr(current_user, "is_authenticated", False):
        return None
    return getattr(current_user, "id_usuario", None)


def _actor_email() -> str | None:
    if not getattr(current_user, "is_authenticated", False):
        return None
    return getattr(current_user, "email_lower", None)


def _generate_inventory_code(now: datetime) -> str:
    return f"INV-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6].upper()}"


def inventory_snapshot(inventory: InventoryModel) -> dict[str, Any]:
    return {
        "id_inventory": inventory.id_inventory,
        "codigo": inventory.codigo,
        "titulo": inventory.titulo,
        "tipo_inventario": inventory.tipo_inventario,
        "status": inventory.status,
        "escopo_tipo": inventory.escopo_tipo,
        "escopo_usuario_id": inventory.escopo_usuario_id,
        "escopo_location_id": inventory.escopo_location_id,
        "escopo_responsavel_snapshot": inventory.escopo_responsavel_snapshot,
        "escopo_local_snapshot": inventory.escopo_local_snapshot,
        "item_count": len(inventory.itens or []),
        "finalizado_em": inventory.finalizado_em,
        "finalizado_por_id": inventory.finalizado_por_id,
    }


def item_snapshot(item: InventoryItemModel) -> dict[str, Any]:
    return {
        "id_inventory_item": item.id_inventory_item,
        "id_inventory": item.id_inventory,
        "id_tool": item.id_tool,
        "status": item.status,
        "codigo_interno_snapshot": item.codigo_interno_snapshot,
        "ferramenta_nome_snapshot": item.ferramenta_nome_snapshot,
        "observacao": item.observacao,
        "conferido_em": item.conferido_em,
    }


def divergence_snapshot(divergence: InventoryDivergenceModel) -> dict[str, Any]:
    return {
        "id_inventory_divergence": divergence.id_inventory_divergence,
        "id_inventory": divergence.id_inventory,
        "id_inventory_item": divergence.id_inventory_item,
        "id_tool": divergence.id_tool,
        "tipo_divergencia": divergence.tipo_divergencia,
        "status": divergence.status,
        "severidade": divergence.severidade,
        "descricao": divergence.descricao,
        "acao_regularizacao": divergence.acao_regularizacao,
        "resolucao": divergence.resolucao,
        "regularizada_em": divergence.regularizada_em,
        "id_occurrence": divergence.id_occurrence,
        "id_transfer": divergence.id_transfer,
    }


def inventory_progress(inventory: InventoryModel) -> dict[str, int | float]:
    total = len(inventory.itens or [])
    completed = sum(
        1 for item in inventory.itens if item.status != InventoryItemStatus.PENDENTE.value
    )
    divergent = sum(1 for item in inventory.itens if item.status in DIVERGENCE_ITEM_STATUSES)
    open_divergences = sum(
        1
        for divergence in inventory.divergencias or []
        if divergence.status == InventoryDivergenceStatus.ABERTA.value
    )
    percent = round((completed / total) * 100, 1) if total else 0
    return {
        "total": total,
        "completed": completed,
        "pending": total - completed,
        "divergent": divergent,
        "open_divergences": open_divergences,
        "percent": percent,
    }


def _build_scope(data: dict[str, Any]) -> dict[str, Any]:
    scope_type = (data.get("escopo_tipo") or "").strip()
    if scope_type not in {item.value for item in InventoryScopeType}:
        raise ValueError("Escopo de inventário inválido.")

    if scope_type == InventoryScopeType.TECNICO.value:
        user_id = int(data.get("escopo_usuario_id") or 0)
        user = get_user_by_id(user_id) if user_id else None
        if not user or not user.is_active:
            raise ValueError("Selecione um técnico/usuário ativo para o inventário.")
        return {
            "escopo_tipo": scope_type,
            "escopo_usuario_id": user.id_usuario,
            "escopo_location_id": None,
            "escopo_responsavel_snapshot": f"{user.nome} <{user.email_lower}>",
            "escopo_local_snapshot": None,
        }

    location_id = int(data.get("escopo_location_id") or 0)
    location = get_location_by_id(location_id) if location_id else None
    if not location or location.is_deleted or not location.ativo:
        raise ValueError("Selecione um local ativo para o inventário.")
    return {
        "escopo_tipo": scope_type,
        "escopo_usuario_id": None,
        "escopo_location_id": location.id_location,
        "escopo_responsavel_snapshot": location.responsavel_nome or location.nome,
        "escopo_local_snapshot": f"{location.nome} ({location.codigo})",
    }


def _expected_custodies_for_scope(scope: dict[str, Any]) -> list[ToolCustodyModel]:
    stmt = (
        select(ToolCustodyModel)
        .options(joinedload(ToolCustodyModel.tool).joinedload(ToolModel.categoria))
        .where(
            ToolCustodyModel.atual == true(),
            ToolCustodyModel.is_deleted == false(),
        )
        .join(ToolModel, ToolModel.id_tool == ToolCustodyModel.id_tool)
        .where(
            ToolModel.is_deleted == false(),
            ToolModel.ativo == true(),
            ToolModel.status.notin_(BLOCKED_TOOL_STATUSES),
        )
        .order_by(ToolModel.codigo_interno)
    )
    if scope["escopo_tipo"] == InventoryScopeType.TECNICO.value:
        stmt = stmt.where(ToolCustodyModel.id_responsavel_usuario == scope["escopo_usuario_id"])
    else:
        stmt = stmt.where(ToolCustodyModel.id_location == scope["escopo_location_id"])
    return list(db.session.execute(stmt).unique().scalars())


def _create_inventory_event(
    *,
    tool: ToolModel,
    event_type: str,
    title: str,
    description: str,
    after: dict[str, Any] | None,
    occurred_at: datetime,
    correlation_id: str,
) -> None:
    db.session.add(
        ToolTimelineEventModel(
            id_tool=tool.id_tool,
            event_type=event_type,
            titulo=title,
            descricao=description,
            before_payload=None,
            after_payload=_json_dumps(after),
            actor_user_id=_actor_id(),
            actor_email=_actor_email(),
            occurred_at=occurred_at,
            correlation_id=correlation_id,
        )
    )


def _lock_inventory_tools(inventory: InventoryModel) -> None:
    for item in inventory.itens:
        tool = item.tool
        if tool.status not in {
            ToolStatus.INVENTARIO.value,
            ToolStatus.BAIXADA.value,
            ToolStatus.INATIVA.value,
        }:
            tool.status = ToolStatus.INVENTARIO.value


def _restore_inventory_tools(inventory: InventoryModel) -> None:
    for item in inventory.itens:
        tool = item.tool
        if tool.status == ToolStatus.INVENTARIO.value:
            tool.status = item.status_ferramenta_esperado


def _build_divergence_description(item: InventoryItemModel, divergence_type: str) -> str:
    return (
        f"{item.codigo_interno_snapshot} - {item.ferramenta_nome_snapshot}: "
        f"divergência do tipo {divergence_type} registrada no inventário."
    )


def _ensure_divergence_for_item(
    inventory: InventoryModel,
    item: InventoryItemModel,
) -> InventoryDivergenceModel | None:
    divergence_type = ITEM_STATUS_TO_DIVERGENCE_TYPE.get(item.status)
    if not divergence_type:
        return None

    existing = find_open_item_divergence(item, divergence_type)
    if existing:
        return existing

    now = utc_now()
    divergence = InventoryDivergenceModel(
        id_inventory=inventory.id_inventory,
        id_inventory_item=item.id_inventory_item,
        id_tool=item.id_tool,
        tipo_divergencia=divergence_type,
        status=InventoryDivergenceStatus.ABERTA.value,
        severidade=DIVERGENCE_SEVERITY.get(divergence_type, "media"),
        descricao=_build_divergence_description(item, divergence_type),
        aberta_por_id=_actor_id(),
        aberta_em=now,
    )
    db.session.add(divergence)
    db.session.flush()
    _create_inventory_event(
        tool=item.tool,
        event_type=ToolTimelineEventType.INVENTARIO_DIVERGENCIA_ABERTA.value,
        title="Divergência de inventário aberta",
        description=divergence.descricao,
        after=divergence_snapshot(divergence),
        occurred_at=now,
        correlation_id=str(uuid4()),
    )
    record_audit_log(
        action="inventories.divergence.create",
        entity="inventory_divergence",
        entity_id=divergence.id_inventory_divergence,
        after=divergence_snapshot(divergence),
        reason=item.observacao or "Divergência gerada pela conferência física.",
    )
    return divergence


def _divergence_type_for_excess_tool(
    inventory: InventoryModel,
    tool: ToolModel,
) -> str:
    if not tool.ativo or tool.status == ToolStatus.BAIXADA.value:
        return InventoryDivergenceType.FERRAMENTA_BAIXADA_ENCONTRADA.value
    if tool.status == ToolStatus.TRANSFERENCIA.value:
        return InventoryDivergenceType.TRANSFERENCIA_PENDENTE.value

    current_custody = db.session.execute(
        select(ToolCustodyModel).where(
            ToolCustodyModel.id_tool == tool.id_tool,
            ToolCustodyModel.atual == true(),
            ToolCustodyModel.is_deleted == false(),
        )
    ).scalar_one_or_none()
    if current_custody:
        if inventory.escopo_tipo == InventoryScopeType.TECNICO.value:
            if current_custody.id_responsavel_usuario != inventory.escopo_usuario_id:
                return InventoryDivergenceType.CUSTODIA_INCONSISTENTE.value
        elif current_custody.id_location != inventory.escopo_location_id:
            return InventoryDivergenceType.CUSTODIA_INCONSISTENTE.value

    return InventoryDivergenceType.FERRAMENTA_EXCEDENTE.value


def _build_excess_item(
    inventory: InventoryModel,
    tool: ToolModel,
    observation: str,
) -> InventoryItemModel:
    current_custody = db.session.execute(
        select(ToolCustodyModel).where(
            ToolCustodyModel.id_tool == tool.id_tool,
            ToolCustodyModel.atual == true(),
            ToolCustodyModel.is_deleted == false(),
        )
    ).scalar_one_or_none()
    item = InventoryItemModel(
        id_inventory=inventory.id_inventory,
        id_tool=tool.id_tool,
        id_custody_snapshot=(current_custody.id_custody if current_custody else None),
        status=InventoryItemStatus.EXCEDENTE.value,
        codigo_interno_snapshot=tool.codigo_interno,
        ferramenta_nome_snapshot=tool.nome,
        categoria_snapshot=tool.categoria.nome if tool.categoria else None,
        status_ferramenta_esperado=tool.status,
        tipo_custodia_esperada=(
            current_custody.tipo_custodia if current_custody else "sem_custodia"
        ),
        responsavel_snapshot=(current_custody.responsavel_snapshot if current_custody else None),
        local_snapshot=(current_custody.local_snapshot if current_custody else None),
        ativo_imobilizado_snapshot=tool.ativo_imobilizado,
        numero_serie_snapshot=tool.numero_serie,
        conferido_por_id=_actor_id(),
        conferido_em=utc_now(),
        observacao=observation,
    )
    inventory.itens.append(item)
    db.session.add(item)
    db.session.flush()
    return item


def _open_divergence_occurrence(
    divergence: InventoryDivergenceModel,
    action: str,
    resolution: str,
    now: datetime,
) -> OccurrenceModel:
    if not divergence.tool:
        raise ValueError("Esta ação exige uma ferramenta vinculada à divergência.")
    occurrence_type = OCCURRENCE_ACTION_TYPE[action]
    occurrence = OccurrenceModel(
        codigo=f"OCO-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6].upper()}",
        id_tool=divergence.tool.id_tool,
        tipo_ocorrencia=occurrence_type,
        status=OccurrenceStatus.AGUARDANDO_APROVACAO.value,
        motivo=f"Regularização da divergência {divergence.id_inventory_divergence}",
        descricao=resolution,
        responsavel_atual_snapshot=(
            divergence.item.responsavel_snapshot
            if divergence.item and divergence.item.responsavel_snapshot
            else divergence.item.local_snapshot
            if divergence.item
            else None
        ),
        custodia_snapshot=None,
        ativo_imobilizado_snapshot=divergence.tool.ativo_imobilizado,
        impacto_patrimonial=bool(divergence.tool.ativo_imobilizado),
        fato_em=now,
        registrado_em=now,
        registrante_id=_actor_id(),
        registrante_email=_actor_email(),
    )
    db.session.add(occurrence)
    db.session.flush()
    divergence.id_occurrence = occurrence.id_occurrence
    _create_inventory_event(
        tool=divergence.tool,
        event_type=ToolTimelineEventType.OCORRENCIA_ABERTA.value,
        title="Ocorrência aberta por divergência de inventário",
        description=f"{occurrence.codigo}: {resolution}",
        after={
            "id_occurrence": occurrence.id_occurrence,
            "codigo": occurrence.codigo,
            "tipo_ocorrencia": occurrence.tipo_ocorrencia,
        },
        occurred_at=now,
        correlation_id=occurrence.codigo,
    )
    record_audit_log(
        action="inventories.divergence.open_occurrence",
        entity="inventory_divergence",
        entity_id=divergence.id_inventory_divergence,
        after={"id_occurrence": occurrence.id_occurrence, "action": action},
        reason=resolution,
    )
    return occurrence


def _linked_occurrence(occurrence_id: int | None) -> OccurrenceModel | None:
    if not occurrence_id:
        return None
    return db.session.execute(
        select(OccurrenceModel).where(
            OccurrenceModel.id_occurrence == occurrence_id,
            OccurrenceModel.is_deleted == false(),
        )
    ).scalar_one_or_none()


def _linked_transfer(transfer_id: int | None) -> TransferModel | None:
    if not transfer_id:
        return None
    return db.session.execute(
        select(TransferModel).where(
            TransferModel.id_transfer == transfer_id,
            TransferModel.is_deleted == false(),
        )
    ).scalar_one_or_none()


def _assert_transfer_matches_divergence(
    divergence: InventoryDivergenceModel,
    transfer: TransferModel | None,
) -> TransferModel:
    if not transfer:
        raise ValueError("Informe a transferência vinculada à regularização.")
    if transfer.status not in TRANSFER_CLOSING_STATUSES:
        raise ValueError("A transferência vinculada não está em status válido.")
    if divergence.tool:
        match = db.session.execute(
            select(TransferItemModel.id_transfer_item).where(
                TransferItemModel.id_transfer == transfer.id_transfer,
                TransferItemModel.id_tool == divergence.tool.id_tool,
                TransferItemModel.is_deleted == false(),
            )
        ).first()
        if not match:
            raise ValueError("A transferência não contém a ferramenta da divergência.")
    return transfer


def _validate_resolution_action(
    divergence: InventoryDivergenceModel,
    action: str,
    occurrence_id: int | None,
    transfer_id: int | None,
    resolution: str,
    now: datetime,
) -> None:
    if action in ACTIONS_THAT_OPEN_OCCURRENCE:
        occurrence = _linked_occurrence(occurrence_id)
        if occurrence is not None:
            if divergence.tool and occurrence.id_tool != divergence.tool.id_tool:
                raise ValueError("A ocorrência informada pertence a outra ferramenta.")
            divergence.id_occurrence = occurrence.id_occurrence
        else:
            _open_divergence_occurrence(divergence, action, resolution, now)
    elif action == InventoryDivergenceAction.TRANSFERIR.value:
        transfer = _assert_transfer_matches_divergence(
            divergence,
            _linked_transfer(transfer_id),
        )
        divergence.id_transfer = transfer.id_transfer
    elif action == InventoryDivergenceAction.CADASTRAR_ITEM_EXCEDENTE.value:
        if divergence.tipo_divergencia not in {
            InventoryDivergenceType.FERRAMENTA_EXCEDENTE.value,
            InventoryDivergenceType.CUSTODIA_INCONSISTENTE.value,
            InventoryDivergenceType.FERRAMENTA_BAIXADA_ENCONTRADA.value,
        }:
            raise ValueError("Ação permitida apenas para divergência de excedente.")
        if not divergence.tool:
            raise ValueError("Excedente sem ferramenta deve virar ocorrência cadastral.")
    elif action == InventoryDivergenceAction.VINCULAR_RESPONSAVEL_CORRETO.value:
        occurrence = _linked_occurrence(occurrence_id)
        transfer = _linked_transfer(transfer_id)
        if not occurrence and not transfer:
            raise ValueError(
                "Vincular responsável correto exige ocorrência ou transferência vinculada."
            )
        if occurrence:
            if divergence.tool and occurrence.id_tool != divergence.tool.id_tool:
                raise ValueError("A ocorrência informada pertence a outra ferramenta.")
            divergence.id_occurrence = occurrence.id_occurrence
        if transfer:
            transfer = _assert_transfer_matches_divergence(divergence, transfer)
            divergence.id_transfer = transfer.id_transfer
    elif action == InventoryDivergenceAction.RECONTAR.value:
        # A recontagem é a própria ação operacional de regularização
        pass


def _refresh_inventory_status_after_divergences(inventory: InventoryModel) -> None:
    if inventory.status not in {
        InventoryStatus.EM_ANDAMENTO.value,
        InventoryStatus.COM_DIVERGENCIA.value,
    }:
        return
    open_count = count_open_inventory_divergences(inventory.id_inventory)
    if open_count:
        inventory.status = InventoryStatus.COM_DIVERGENCIA.value
    else:
        inventory.status = InventoryStatus.EM_ANDAMENTO.value


def create_inventory(data: dict[str, Any]) -> InventoryModel:
    title = (data.get("titulo") or "").strip()
    if len(title) < 3:
        raise ValueError("Informe um título para o inventário.")

    inventory_type = (data.get("tipo_inventario") or "").strip()
    if inventory_type not in {item.value for item in InventoryType}:
        raise ValueError("Tipo de inventário inválido.")

    initial_status = (data.get("status_inicial") or InventoryStatus.RASCUNHO.value).strip()
    if initial_status not in {InventoryStatus.RASCUNHO.value, InventoryStatus.EM_ANDAMENTO.value}:
        raise ValueError("Status inicial inválido.")

    scope = _build_scope(data)
    if getattr(current_user, "is_authenticated", False):
        try:
            assert_can_access_inventory_scope(current_user, scope)
        except ScopeAccessDenied as exc:
            raise ValueError("Você não possui escopo para criar inventário neste alvo.") from exc
    expected = _expected_custodies_for_scope(scope)
    if not expected:
        raise ValueError("Nenhuma ferramenta com custódia atual foi encontrada para este escopo.")

    now = utc_now()
    correlation_id = str(uuid4())
    inventory = InventoryModel(
        codigo=_generate_inventory_code(now),
        titulo=title,
        tipo_inventario=inventory_type,
        status=initial_status,
        descricao=(data.get("descricao") or "").strip() or None,
        criado_por_id=_actor_id(),
        iniciado_em=now if initial_status == InventoryStatus.EM_ANDAMENTO.value else None,
        **scope,
    )
    db.session.add(inventory)
    db.session.flush()

    for custody in expected:
        tool = custody.tool
        item = InventoryItemModel(
            id_tool=tool.id_tool,
            id_custody_snapshot=custody.id_custody,
            status=InventoryItemStatus.PENDENTE.value,
            codigo_interno_snapshot=tool.codigo_interno,
            ferramenta_nome_snapshot=tool.nome,
            categoria_snapshot=tool.categoria.nome if tool.categoria else None,
            status_ferramenta_esperado=tool.status,
            tipo_custodia_esperada=custody.tipo_custodia,
            responsavel_snapshot=custody.responsavel_snapshot,
            local_snapshot=custody.local_snapshot,
            ativo_imobilizado_snapshot=tool.ativo_imobilizado,
            numero_serie_snapshot=tool.numero_serie,
        )
        inventory.itens.append(item)
        db.session.add(item)
        _create_inventory_event(
            tool=tool,
            event_type=ToolTimelineEventType.INVENTARIO_ABERTO.value,
            title="Inventário aberto",
            description=f"{inventory.codigo}: {inventory.titulo}",
            after={"inventory": inventory.codigo, "status": initial_status},
            occurred_at=now,
            correlation_id=correlation_id,
        )

    db.session.flush()
    if initial_status == InventoryStatus.EM_ANDAMENTO.value:
        _lock_inventory_tools(inventory)

    record_audit_log(
        action="inventories.create",
        entity="inventory",
        entity_id=inventory.id_inventory,
        after=inventory_snapshot(inventory),
        reason=inventory.titulo,
    )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ValueError("Não foi possível criar o inventário com segurança.") from exc
    return inventory


def start_inventory(inventory: InventoryModel) -> InventoryModel:
    if inventory.status != InventoryStatus.RASCUNHO.value:
        raise ValueError("Apenas inventários em rascunho podem ser iniciados.")
    before = inventory_snapshot(inventory)
    inventory.status = InventoryStatus.EM_ANDAMENTO.value
    inventory.iniciado_em = utc_now()
    _lock_inventory_tools(inventory)
    record_audit_log(
        action="inventories.start",
        entity="inventory",
        entity_id=inventory.id_inventory,
        before=before,
        after=inventory_snapshot(inventory),
        reason="Início da conferência física.",
    )
    db.session.commit()
    return inventory


def update_inventory_item_status(
    inventory: InventoryModel,
    item: InventoryItemModel,
    status: str,
    observation: str | None = None,
) -> InventoryItemModel:
    if item.id_inventory != inventory.id_inventory:
        raise ValueError("Item não pertence ao inventário informado.")
    if inventory.status not in {
        InventoryStatus.EM_ANDAMENTO.value,
        InventoryStatus.COM_DIVERGENCIA.value,
    }:
        raise ValueError("A conferência só pode ser alterada com inventário em andamento.")
    if status not in {item.value for item in InventoryItemStatus}:
        raise ValueError("Status de item inválido.")

    before = item_snapshot(item)
    item.status = status
    item.observacao = (observation or "").strip() or None
    item.conferido_por_id = _actor_id()
    item.conferido_em = utc_now()

    _ensure_divergence_for_item(inventory, item)

    if status in DIVERGENCE_ITEM_STATUSES:
        inventory.status = InventoryStatus.COM_DIVERGENCIA.value
    else:
        _refresh_inventory_status_after_divergences(inventory)

    _create_inventory_event(
        tool=item.tool,
        event_type=ToolTimelineEventType.INVENTARIO_ITEM_CONFERIDO.value,
        title="Item de inventário conferido",
        description=f"{inventory.codigo}: {item.codigo_interno_snapshot} marcado como {status}",
        after=item_snapshot(item),
        occurred_at=item.conferido_em,
        correlation_id=str(uuid4()),
    )
    record_audit_log(
        action="inventories.item.update",
        entity="inventory_item",
        entity_id=item.id_inventory_item,
        before=before,
        after=item_snapshot(item),
        reason=item.observacao or "Conferência física.",
    )
    db.session.commit()
    return item


def resolve_inventory_divergence(
    inventory: InventoryModel,
    divergence: InventoryDivergenceModel,
    action: str,
    resolution: str,
    *,
    occurrence_id: int | None = None,
    transfer_id: int | None = None,
) -> InventoryDivergenceModel:
    if divergence.id_inventory != inventory.id_inventory:
        raise ValueError("Divergência não pertence ao inventário informado.")
    if divergence.status != InventoryDivergenceStatus.ABERTA.value:
        raise ValueError("Apenas divergências abertas podem ser regularizadas.")
    if action not in {item.value for item in InventoryDivergenceAction}:
        raise ValueError("Ação de regularização inválida.")
    resolution = (resolution or "").strip()
    if len(resolution) < 5:
        raise ValueError("Informe uma justificativa de regularização com pelo menos 5 caracteres.")

    before = divergence_snapshot(divergence)
    now = utc_now()
    _validate_resolution_action(
        divergence,
        action,
        occurrence_id,
        transfer_id,
        resolution,
        now,
    )
    divergence.acao_regularizacao = action
    divergence.resolucao = resolution
    divergence.regularizada_por_id = _actor_id()
    divergence.regularizada_em = now

    if action in ACTIONS_THAT_KEEP_STATUS_JUSTIFIED:
        divergence.status = InventoryDivergenceStatus.JUSTIFICADA.value
    elif action in ACTIONS_THAT_CANCEL:
        divergence.status = InventoryDivergenceStatus.CANCELADA.value
    else:
        divergence.status = InventoryDivergenceStatus.REGULARIZADA.value

    if divergence.item and divergence.item.status in DIVERGENCE_ITEM_STATUSES:
        divergence.item.status = InventoryItemStatus.REGULARIZADO.value
        divergence.item.observacao = resolution
        divergence.item.conferido_por_id = _actor_id()
        divergence.item.conferido_em = now

    if divergence.tool:
        _create_inventory_event(
            tool=divergence.tool,
            event_type=ToolTimelineEventType.INVENTARIO_DIVERGENCIA_REGULARIZADA.value,
            title="Divergência de inventário regularizada",
            description=f"{inventory.codigo}: {resolution}",
            after=divergence_snapshot(divergence),
            occurred_at=now,
            correlation_id=str(uuid4()),
        )

    db.session.flush()
    _refresh_inventory_status_after_divergences(inventory)
    record_internal_signature(
        action=SignatureAction.INVENTORY_DIVERGENCE_RESOLVE.value,
        entity="inventory_divergence",
        entity_id=divergence.id_inventory_divergence,
        result=SignatureResult.REGULARIZADO.value,
        reason=resolution,
        context={"before": before, "after": divergence_snapshot(divergence)},
        inventory_id=inventory.id_inventory,
        inventory_divergence_id=divergence.id_inventory_divergence,
    )
    record_audit_log(
        action="inventories.divergence.resolve",
        entity="inventory_divergence",
        entity_id=divergence.id_inventory_divergence,
        before=before,
        after=divergence_snapshot(divergence),
        reason=resolution,
    )
    db.session.commit()
    return divergence


def finish_inventory(inventory: InventoryModel, reason: str | None = None) -> InventoryModel:
    if inventory.status not in {
        InventoryStatus.EM_ANDAMENTO.value,
        InventoryStatus.COM_DIVERGENCIA.value,
    }:
        raise ValueError("Apenas inventários em andamento podem ser enviados para assinatura.")
    if has_pending_inventory_items(inventory.id_inventory):
        raise ValueError("Inventário possui itens pendentes de conferência.")
    open_count = count_open_inventory_divergences(inventory.id_inventory)
    if open_count:
        raise ValueError(
            f"Inventário possui {open_count} divergência(s) aberta(s). "
            "Regularize antes de finalizar."
        )

    before = inventory_snapshot(inventory)
    inventory.status = InventoryStatus.AGUARDANDO_ASSINATURA.value
    now = utc_now()
    for item in inventory.itens:
        _create_inventory_event(
            tool=item.tool,
            event_type=ToolTimelineEventType.INVENTARIO_AGUARDANDO_ASSINATURA.value,
            title="Inventário aguardando assinatura",
            description=f"{inventory.codigo}: conferência concluída e pronta para assinatura.",
            after=inventory_snapshot(inventory),
            occurred_at=now,
            correlation_id=str(uuid4()),
        )
    record_audit_log(
        action="inventories.finish.request",
        entity="inventory",
        entity_id=inventory.id_inventory,
        before=before,
        after=inventory_snapshot(inventory),
        reason=(reason or "Conferência concluída sem divergências abertas.").strip(),
    )
    db.session.commit()
    return inventory


def sign_inventory(inventory: InventoryModel, reason: str) -> InventoryModel:
    if inventory.status != InventoryStatus.AGUARDANDO_ASSINATURA.value:
        raise ValueError("Apenas inventários aguardando assinatura podem ser assinados.")
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise ValueError("Informe uma justificativa de assinatura com pelo menos 5 caracteres.")

    before = inventory_snapshot(inventory)
    now = utc_now()
    inventory.status = InventoryStatus.FINALIZADO.value
    inventory.finalizado_em = now
    inventory.finalizado_por_id = _actor_id()
    inventory.motivo_finalizacao = reason
    _restore_inventory_tools(inventory)

    correlation_id = str(uuid4())
    for item in inventory.itens:
        _create_inventory_event(
            tool=item.tool,
            event_type=ToolTimelineEventType.INVENTARIO_FINALIZADO.value,
            title="Inventário assinado e finalizado",
            description=f"{inventory.codigo}: {reason}",
            after=inventory_snapshot(inventory),
            occurred_at=now,
            correlation_id=correlation_id,
        )

    record_internal_signature(
        action=SignatureAction.INVENTORY_SIGN.value,
        entity="inventory",
        entity_id=inventory.id_inventory,
        result=SignatureResult.CONFIRMADO.value,
        reason=reason,
        context={"before": before, "after": inventory_snapshot(inventory)},
        correlation_id=correlation_id,
        inventory_id=inventory.id_inventory,
        require_authenticated=True,
    )
    record_audit_log(
        action="inventories.sign",
        entity="inventory",
        entity_id=inventory.id_inventory,
        before=before,
        after=inventory_snapshot(inventory),
        reason=reason,
    )
    db.session.commit()
    return inventory


def cancel_inventory(inventory: InventoryModel, reason: str) -> InventoryModel:
    if inventory.status not in OPEN_INVENTORY_STATUSES:
        raise ValueError("Apenas inventários abertos podem ser cancelados.")
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise ValueError("Informe um motivo de cancelamento com pelo menos 5 caracteres.")
    before = inventory_snapshot(inventory)
    inventory.status = InventoryStatus.CANCELADO.value
    inventory.cancelado_em = utc_now()
    inventory.cancelado_por_id = _actor_id()
    inventory.motivo_cancelamento = reason
    _restore_inventory_tools(inventory)
    for item in inventory.itens:
        _create_inventory_event(
            tool=item.tool,
            event_type=ToolTimelineEventType.INVENTARIO_CANCELADO.value,
            title="Inventário cancelado",
            description=f"{inventory.codigo}: {reason}",
            after={"inventory": inventory.codigo, "reason": reason},
            occurred_at=inventory.cancelado_em,
            correlation_id=str(uuid4()),
        )
    record_internal_signature(
        action=SignatureAction.INVENTORY_CANCEL.value,
        entity="inventory",
        entity_id=inventory.id_inventory,
        result=SignatureResult.CANCELADO.value,
        reason=reason,
        context={"before": before, "after": inventory_snapshot(inventory)},
        inventory_id=inventory.id_inventory,
    )
    record_audit_log(
        action="inventories.cancel",
        entity="inventory",
        entity_id=inventory.id_inventory,
        before=before,
        after=inventory_snapshot(inventory),
        reason=reason,
    )
    db.session.commit()
    return inventory



def get_inventory_evidence_path(evidence: InventoryItemEvidenceModel) -> Path:
    path = safe_upload_path(evidence.storage_path)
    if path is None:
        raise ValueError("Caminho de evidência inválido.")
    return path


def register_inventory_excess(
    inventory: InventoryModel,
    identifier: str,
    observation: str | None = None,
) -> InventoryItemModel:
    if inventory.status not in {
        InventoryStatus.EM_ANDAMENTO.value,
        InventoryStatus.COM_DIVERGENCIA.value,
    }:
        raise ValueError("Excedente só pode ser registrado com inventário em andamento.")
    note = (observation or "").strip()
    if len(note) < 5:
        raise ValueError("Informe uma observação para registrar ferramenta excedente.")

    tool = get_tool_by_any_identifier(identifier)
    if not tool:
        raise ValueError("Ferramenta excedente não encontrada pelo código, ativo ou série.")

    already_expected = db.session.execute(
        select(InventoryItemModel.id_inventory_item).where(
            InventoryItemModel.id_inventory == inventory.id_inventory,
            InventoryItemModel.id_tool == tool.id_tool,
            InventoryItemModel.is_deleted == false(),
        )
    ).first()
    if already_expected:
        raise ValueError(
            "Ferramenta encontrada já pertence ao inventário. Atualize o item esperado."
        )

    before = inventory_snapshot(inventory)
    item = _build_excess_item(inventory, tool, note)
    divergence_type = _divergence_type_for_excess_tool(inventory, tool)
    divergence = InventoryDivergenceModel(
        id_inventory=inventory.id_inventory,
        id_inventory_item=item.id_inventory_item,
        id_tool=tool.id_tool,
        tipo_divergencia=divergence_type,
        status=InventoryDivergenceStatus.ABERTA.value,
        severidade=DIVERGENCE_SEVERITY.get(divergence_type, "media"),
        descricao=(
            f"Ferramenta excedente encontrada no inventário: {tool.codigo_interno}. "
            f"{note}"
        ),
        aberta_por_id=_actor_id(),
        aberta_em=utc_now(),
    )
    db.session.add(divergence)
    db.session.flush()
    inventory.status = InventoryStatus.COM_DIVERGENCIA.value

    _create_inventory_event(
        tool=tool,
        event_type=ToolTimelineEventType.INVENTARIO_DIVERGENCIA_ABERTA.value,
        title="Ferramenta excedente encontrada",
        description=divergence.descricao,
        after={"item": item_snapshot(item), "divergence": divergence_snapshot(divergence)},
        occurred_at=divergence.aberta_em,
        correlation_id=str(uuid4()),
    )
    record_audit_log(
        action="inventories.excess.register",
        entity="inventory",
        entity_id=inventory.id_inventory,
        before=before,
        after={"item": item_snapshot(item), "divergence": divergence_snapshot(divergence)},
        reason=note,
    )
    db.session.commit()
    return item


def scan_inventory_item(
    inventory: InventoryModel,
    identifier: str,
    observation: str | None = None,
) -> InventoryItemModel:
    if inventory.status not in {
        InventoryStatus.EM_ANDAMENTO.value,
        InventoryStatus.COM_DIVERGENCIA.value,
    }:
        raise ValueError("Leitura de campo permitida apenas em inventário em andamento.")

    item = find_inventory_item_by_identifier(inventory, identifier)
    if not item:
        return register_inventory_excess(
            inventory,
            identifier,
            observation
            or f"Ferramenta excedente encontrada por leitura: {identifier.strip()}.",
        )

    note = (
        observation
        or f"Item marcado como encontrado por leitura de código: {identifier.strip()}."
    )
    update_inventory_item_status(inventory, item, InventoryItemStatus.ENCONTRADO.value, note)

    _create_inventory_event(
        tool=item.tool,
        event_type=ToolTimelineEventType.INVENTARIO_ITEM_LIDO_POR_CODIGO.value,
        title="Item lido por código",
        description=note,
        after=item_snapshot(item),
        occurred_at=utc_now(),
        correlation_id=inventory.codigo,
    )
    db.session.commit()
    return item


def save_inventory_item_evidence(
    inventory: InventoryModel,
    item: InventoryItemModel,
    file: FileStorage | None,
    observation: str | None = None,
) -> InventoryItemEvidenceModel:
    if item.id_inventory != inventory.id_inventory:
        raise ValueError("Item não pertence ao inventário informado.")
    if inventory.status not in {
        InventoryStatus.EM_ANDAMENTO.value,
        InventoryStatus.COM_DIVERGENCIA.value,
        InventoryStatus.AGUARDANDO_ASSINATURA.value,
    }:
        raise ValueError("Não é possível anexar evidência neste status do inventário.")

    stored = store_upload(
        file,
        allowed_extensions=current_app.config["ALLOWED_EVIDENCE_EXTENSIONS"],
        max_mb=int(current_app.config["INVENTORY_EVIDENCE_MAX_MB"]),
        directory_parts=(
            "inventories",
            str(inventory.id_inventory),
            "items",
            str(item.id_inventory_item),
        ),
        default_filename="evidencia.pdf",
    )

    try:
        evidence = InventoryItemEvidenceModel(
            id_inventory_item=item.id_inventory_item,
            id_inventory=inventory.id_inventory,
            id_tool=item.id_tool,
            storage_path=stored.relative_path,
            filename=stored.storage_filename,
            original_filename=stored.original_filename,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            observacao=(observation or "").strip() or None,
            uploaded_by_id=_actor_id(),
            uploaded_at=utc_now(),
        )
        db.session.add(evidence)
        db.session.flush()

        _create_inventory_event(
            tool=item.tool,
            event_type=ToolTimelineEventType.INVENTARIO_EVIDENCIA_ADICIONADA.value,
            title="Evidência de inventário adicionada",
            description=observation or "Evidência anexada ao item de inventário.",
            after={
                "id_inventory_item_evidence": evidence.id_inventory_item_evidence,
                "id_inventory_item": item.id_inventory_item,
                "filename": evidence.original_filename,
                "content_type": evidence.content_type,
                "size_bytes": evidence.size_bytes,
            },
            occurred_at=utc_now(),
            correlation_id=inventory.codigo,
        )
        record_audit_log(
            action="inventories.evidence.upload",
            entity="inventory_item",
            entity_id=item.id_inventory_item,
            after={
                "id_inventory_item_evidence": evidence.id_inventory_item_evidence,
                "id_inventory": inventory.id_inventory,
                "id_tool": item.id_tool,
                "filename": evidence.original_filename,
                "content_type": evidence.content_type,
                "size_bytes": evidence.size_bytes,
            },
            reason=observation or "Evidência anexada ao item de inventário.",
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        remove_upload_file(stored.absolute_path)
        raise
    return evidence
