from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from flask import current_app
from flask_login import current_user
from sqlalchemy import false, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.audit.services import record_audit_log
from app.custody.models import ToolCustodyModel, ToolTimelineEventModel
from app.custody.repositories import get_current_custody
from app.custody.services import custody_snapshot
from app.extensions import db
from app.locations.repositories import get_location_by_id
from app.models.enums import (
    CustodyType,
    SignatureAction,
    SignatureResult,
    ToolStatus,
    ToolTimelineEventType,
    TransferItemStatus,
    TransferStatus,
    TransferType,
)
from app.permissions.scope_filters import (
    ScopeAccessDenied,
    assert_can_access_tool,
    can_access_location,
    can_access_user_scope_target,
)
from app.permissions.services import has_permission
from app.signatures.services import record_internal_signature
from app.tools.models import ToolModel
from app.tools.repositories import get_tool_by_codigo_interno
from app.transfers.models import TransferItemModel, TransferModel
from app.users.models import UserModel
from app.users.repositories import get_user_by_id

LOCATION_CUSTODY_TYPES = {
    CustodyType.OFICINA.value,
    CustodyType.SITE_CLIENTE.value,
    CustodyType.ALMOXARIFADO.value,
    CustodyType.DEPARTAMENTO.value,
    CustodyType.MANUTENCAO_CALIBRACAO.value,
}
BLOCKED_TOOL_STATUSES = {
    ToolStatus.BAIXADA.value,
    ToolStatus.INATIVA.value,
    ToolStatus.TRANSFERENCIA.value,
    ToolStatus.INVENTARIO.value,
}
PENDING_TRANSFER_STATUSES = {
    TransferStatus.AGUARDANDO_ORIGEM.value,
    TransferStatus.AGUARDANDO_DESTINO.value,
}
CLOSED_TRANSFER_STATUSES = {
    TransferStatus.CONCLUIDA.value,
    TransferStatus.RECUSADA.value,
    TransferStatus.CANCELADA.value,
    TransferStatus.EXPIRADA.value,
}
MIN_DECISION_REASON_LENGTH = 5
DEFAULT_TRANSFER_EXPIRATION_DAYS = 7


def utc_now() -> datetime:
    return datetime.now(UTC)


def _json_dumps(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _active_actor() -> UserModel | None:
    if not getattr(current_user, "is_authenticated", False):
        return None
    if not getattr(current_user, "is_active", False):
        return None
    return current_user  # type: ignore[return-value]


def _actor_id() -> int | None:
    actor = _active_actor()
    return getattr(actor, "id_usuario", None) if actor else None


def _actor_email() -> str | None:
    actor = _active_actor()
    return getattr(actor, "email_lower", None) if actor else None


def _actor_has_override(actor: UserModel | None) -> bool:
    return bool(actor and has_permission(actor, "transfers.override"))


def transfer_snapshot(transfer: TransferModel) -> dict[str, Any]:
    return {
        "id_transfer": transfer.id_transfer,
        "codigo": transfer.codigo,
        "tipo_transferencia": transfer.tipo_transferencia,
        "status": transfer.status,
        "destino_tipo_custodia": transfer.destino_tipo_custodia,
        "destino_usuario_id": transfer.destino_usuario_id,
        "destino_location_id": transfer.destino_location_id,
        "destino_responsavel_snapshot": transfer.destino_responsavel_snapshot,
        "destino_local_snapshot": transfer.destino_local_snapshot,
        "motivo": transfer.motivo,
        "item_count": len(transfer.itens or []),
    }


def parse_tool_codes(raw_value: str) -> list[str]:
    codes = [part.strip().upper() for part in re.split(r"[\n,;]+", raw_value or "")]
    unique: list[str] = []
    for code in codes:
        if code and code not in unique:
            unique.append(code)
    if not unique:
        raise ValueError("Informe ao menos uma ferramenta para transferir.")
    return unique


def _build_destination(data: dict[str, Any]) -> dict[str, Any]:
    destination_type = (data.get("destino_tipo_custodia") or "").strip()
    if destination_type not in {item.value for item in CustodyType}:
        raise ValueError("Tipo de destino inválido.")

    if destination_type == CustodyType.TECNICO.value:
        user_id = int(data.get("destino_usuario_id") or 0)
        user = get_user_by_id(user_id) if user_id else None
        if not user or not user.is_active:
            raise ValueError("Selecione um usuário destino ativo.")
        return {
            "tipo_custodia": destination_type,
            "id_responsavel_usuario": user.id_usuario,
            "id_location": None,
            "responsavel_snapshot": f"{user.nome} <{user.email_lower}>",
            "local_snapshot": None,
        }

    if destination_type in LOCATION_CUSTODY_TYPES:
        location_id = int(data.get("destino_location_id") or 0)
        location = get_location_by_id(location_id) if location_id else None
        if not location or location.is_deleted or not location.ativo:
            raise ValueError("Selecione um local destino ativo.")
        return {
            "tipo_custodia": destination_type,
            "id_responsavel_usuario": None,
            "id_location": location.id_location,
            "responsavel_snapshot": location.responsavel_nome or location.nome,
            "local_snapshot": f"{location.nome} ({location.codigo})",
        }

    raise ValueError("Tipo de destino não suportado.")


def _generate_transfer_code(now: datetime) -> str:
    return f"TRF-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6].upper()}"


def _locked_transfer(transfer: TransferModel) -> TransferModel:
    locked = db.session.execute(
        select(TransferModel)
        .options(selectinload(TransferModel.itens).selectinload(TransferItemModel.tool))
        .options(selectinload(TransferModel.itens).selectinload(TransferItemModel.custody_origem))
        .where(
            TransferModel.id_transfer == transfer.id_transfer,
            TransferModel.is_deleted == false(),
        )
        .with_for_update()
    ).scalar_one_or_none()
    if locked is None:
        raise ValueError("Transferência não encontrada ou removida.")
    return locked


def _assert_tool_can_transfer(tool: ToolModel) -> None:
    if tool.is_deleted:
        raise ValueError(f"Ferramenta {tool.codigo_interno} foi removida logicamente.")
    if not tool.ativo or tool.status in BLOCKED_TOOL_STATUSES:
        raise ValueError(
            f"Ferramenta {tool.codigo_interno} não está disponível para transferência."
        )
    if not get_current_custody(tool.id_tool):
        raise ValueError(f"Ferramenta {tool.codigo_interno} não possui custódia atual.")


def _assert_tool_has_no_open_transfer(tool: ToolModel) -> None:
    open_transfer = db.session.execute(
        select(TransferModel.codigo)
        .join(TransferItemModel, TransferItemModel.id_transfer == TransferModel.id_transfer)
        .where(
            TransferItemModel.id_tool == tool.id_tool,
            TransferItemModel.is_deleted == false(),
            TransferModel.is_deleted == false(),
            TransferModel.status.in_(PENDING_TRANSFER_STATUSES),
        )
        .limit(1)
    ).scalar_one_or_none()
    if open_transfer:
        raise ValueError(
            f"Ferramenta {tool.codigo_interno} já está na transferência pendente "
            f"{open_transfer}."
        )


def _load_transfer_tools(raw_codes: str) -> list[ToolModel]:
    tools: list[ToolModel] = []
    for code in parse_tool_codes(raw_codes):
        tool = get_tool_by_codigo_interno(code)
        if not tool:
            raise ValueError(f"Ferramenta não encontrada: {code}")
        _assert_tool_has_no_open_transfer(tool)
        _assert_tool_can_transfer(tool)
        actor = _active_actor()
        if actor:
            try:
                assert_can_access_tool(actor, tool)
            except ScopeAccessDenied as exc:
                raise ValueError(
                    "Você não possui escopo para transferir a ferramenta "
                    f"{tool.codigo_interno}."
                ) from exc
        tools.append(tool)
    return tools


def _tool_target_status(destination_type: str) -> str:
    if destination_type == CustodyType.TECNICO.value:
        return ToolStatus.EM_USO.value
    if destination_type == CustodyType.MANUTENCAO_CALIBRACAO.value:
        return ToolStatus.MANUTENCAO.value
    return ToolStatus.DISPONIVEL.value


def _create_transfer_event(
    *,
    tool: ToolModel,
    event_type: str,
    title: str,
    description: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    occurred_at: datetime,
    correlation_id: str,
) -> ToolTimelineEventModel:
    event = ToolTimelineEventModel(
        id_tool=tool.id_tool,
        event_type=event_type,
        titulo=title,
        descricao=description,
        before_payload=_json_dumps(before),
        after_payload=_json_dumps(after),
        actor_user_id=_actor_id(),
        actor_email=_actor_email(),
        occurred_at=occurred_at,
        correlation_id=correlation_id,
    )
    db.session.add(event)
    return event


def create_transfer(data: dict[str, Any]) -> TransferModel:
    transfer_type = (data.get("tipo_transferencia") or "").strip()
    if transfer_type not in {item.value for item in TransferType}:
        raise ValueError("Tipo de transferência inválido.")

    reason = (data.get("motivo") or "").strip()
    if len(reason) < 5:
        raise ValueError("Informe um motivo com pelo menos 5 caracteres.")

    destination = _build_destination(data)
    tools = _load_transfer_tools(data.get("codigos_ferramentas") or "")
    now = utc_now()
    correlation_id = str(uuid4())
    actor_id = _actor_id()

    transfer = TransferModel(
        codigo=_generate_transfer_code(now),
        tipo_transferencia=transfer_type,
        status=TransferStatus.AGUARDANDO_ORIGEM.value,
        destino_tipo_custodia=destination["tipo_custodia"],
        destino_usuario_id=destination["id_responsavel_usuario"],
        destino_location_id=destination["id_location"],
        destino_responsavel_snapshot=destination["responsavel_snapshot"],
        destino_local_snapshot=destination["local_snapshot"],
        motivo=reason,
        observacoes=(data.get("observacoes") or "").strip() or None,
        solicitado_por_id=actor_id,
        solicitado_em=now,
        assinatura_unica_prevista=True,
    )
    db.session.add(transfer)
    db.session.flush()

    for tool in tools:
        current = get_current_custody(tool.id_tool)
        if current is None:
            raise ValueError(f"Ferramenta {tool.codigo_interno} não possui custódia atual.")
        item = TransferItemModel(
            id_transfer=transfer.id_transfer,
            id_tool=tool.id_tool,
            id_custody_origem=current.id_custody,
            status=TransferItemStatus.PENDENTE.value,
            status_ferramenta_anterior=tool.status,
            origem_tipo_custodia=current.tipo_custodia,
            origem_responsavel_snapshot=current.responsavel_snapshot,
            origem_local_snapshot=current.local_snapshot,
        )
        db.session.add(item)
        before_tool = tool.to_dict()
        tool.status = ToolStatus.TRANSFERENCIA.value
        _create_transfer_event(
            tool=tool,
            event_type=ToolTimelineEventType.TRANSFERENCIA_SOLICITADA.value,
            title="Transferência solicitada",
            description=f"{transfer.codigo}: {reason}",
            before=before_tool,
            after={**before_tool, "status": tool.status},
            occurred_at=now,
            correlation_id=correlation_id,
        )

    db.session.flush()
    record_audit_log(
        action="transfers.create",
        entity="transfer",
        entity_id=transfer.id_transfer,
        after=transfer_snapshot(transfer),
        reason=reason,
    )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ValueError("Não foi possível criar a transferência com segurança.") from exc
    return transfer


def _assert_status(transfer: TransferModel, expected: str) -> None:
    if transfer.status != expected:
        raise ValueError(
            f"Transferência {transfer.codigo} está em status {transfer.status}; "
            f"esperado {expected}."
        )


def _validate_decision_reason(reason: str | None, action: str) -> str:
    clean_reason = (reason or "").strip()
    if len(clean_reason) < MIN_DECISION_REASON_LENGTH:
        raise ValueError(f"Informe um motivo de {action} com pelo menos 5 caracteres.")
    return clean_reason


def _ensure_items_have_status(
    transfer: TransferModel,
    expected: str,
    message: str,
) -> None:
    if any(item.status != expected for item in transfer.itens):
        raise ValueError(message)


def _actor_can_cover_custody(actor: UserModel, custody: ToolCustodyModel | None) -> bool:
    if custody is None:
        return False
    if custody.tipo_custodia == CustodyType.TECNICO.value:
        if custody.id_responsavel_usuario == actor.id_usuario:
            return True
        return can_access_user_scope_target(actor, custody.id_responsavel_usuario)
    if custody.id_location:
        return can_access_location(actor, custody.id_location)
    return False


def _actor_can_cover_destination(actor: UserModel, transfer: TransferModel) -> bool:
    if transfer.destino_tipo_custodia == CustodyType.TECNICO.value:
        if transfer.destino_usuario_id == actor.id_usuario:
            return True
        return can_access_user_scope_target(actor, transfer.destino_usuario_id)
    if transfer.destino_location_id:
        return can_access_location(actor, transfer.destino_location_id)
    return False


def _require_origin_actor(transfer: TransferModel) -> bool:
    actor = _active_actor()
    if actor is None:
        return True
    if _actor_has_override(actor):
        return True
    if not transfer.itens:
        return False
    return all(_actor_can_cover_custody(actor, item.custody_origem) for item in transfer.itens)


def _require_destination_actor(transfer: TransferModel) -> bool:
    actor = _active_actor()
    if actor is None:
        return True
    if _actor_has_override(actor):
        return True
    return _actor_can_cover_destination(actor, transfer)


def _require_cancel_actor(transfer: TransferModel, *, force: bool) -> None:
    actor = _active_actor()
    if actor is None:
        return
    if force:
        if not _actor_has_override(actor):
            raise ValueError("Cancelamento forçado exige permissão transfers.override.")
        return
    if transfer.solicitado_por_id and transfer.solicitado_por_id == actor.id_usuario:
        return
    if (
        transfer.status == TransferStatus.AGUARDANDO_ORIGEM.value
        and _require_origin_actor(transfer)
    ):
        return
    if (
        transfer.status == TransferStatus.AGUARDANDO_DESTINO.value
        and (_require_origin_actor(transfer) or _require_destination_actor(transfer))
    ):
        return
    raise ValueError("Você não possui relação com esta transferência para cancelá-la.")


def confirm_origin(transfer: TransferModel, reason: str | None = None) -> TransferModel:
    transfer = _locked_transfer(transfer)
    _assert_status(transfer, TransferStatus.AGUARDANDO_ORIGEM.value)
    _ensure_items_have_status(
        transfer,
        TransferItemStatus.PENDENTE.value,
        "A transferência possui itens em estado incompatível com confirmação de origem.",
    )
    if not _require_origin_actor(transfer):
        raise ValueError(
            "A origem só pode ser confirmada por responsável da custódia de origem "
            "ou por usuário com permissão transfers.override."
        )

    before = transfer_snapshot(transfer)
    now = utc_now()
    actor = _active_actor()
    transfer.origem_confirmada_por_id = _actor_id()
    transfer.origem_confirmada_em = now
    transfer.status = TransferStatus.AGUARDANDO_DESTINO.value
    for item in transfer.itens:
        item.status = TransferItemStatus.AGUARDANDO_DESTINO.value
    record_internal_signature(
        action=SignatureAction.TRANSFER_CONFIRM_ORIGIN.value,
        entity="transfer",
        entity_id=transfer.id_transfer,
        result=SignatureResult.CONFIRMADO.value,
        reason=reason or "Origem confirmou a saída.",
        context={
            "before": before,
            "after": transfer_snapshot(transfer),
            "override": _actor_has_override(actor),
        },
        transfer_id=transfer.id_transfer,
    )
    record_audit_log(
        action=(
            "transfers.override.confirm_origin"
            if _actor_has_override(actor)
            else "transfers.confirm_origin"
        ),
        entity="transfer",
        entity_id=transfer.id_transfer,
        before=before,
        after=transfer_snapshot(transfer),
        reason=reason or "Origem confirmou a saída.",
    )
    db.session.commit()
    return transfer


def _apply_transfer_item(
    *,
    transfer: TransferModel,
    item: TransferItemModel,
    destination: dict[str, Any],
    occurred_at: datetime,
    correlation_id: str,
) -> None:
    tool = item.tool
    current = get_current_custody(tool.id_tool)
    if current is None or current.id_custody != item.id_custody_origem:
        raise ValueError(
            f"Custódia atual da ferramenta {tool.codigo_interno} mudou durante "
            "a transferência."
        )

    before_custody = custody_snapshot(current)
    actor_id = _actor_id()
    current.atual = False
    current.fim_em = occurred_at
    current.motivo_fim = f"Transferência {transfer.codigo} concluída."
    current.encerrado_por_id = actor_id
    db.session.flush()

    new_custody = ToolCustodyModel(
        id_tool=tool.id_tool,
        tipo_custodia=destination["tipo_custodia"],
        id_responsavel_usuario=destination["id_responsavel_usuario"],
        id_location=destination["id_location"],
        responsavel_snapshot=destination["responsavel_snapshot"],
        local_snapshot=destination["local_snapshot"],
        inicio_em=occurred_at,
        atual=True,
        motivo_inicio=f"Transferência {transfer.codigo}: {transfer.motivo}",
        criado_por_id=actor_id,
    )
    db.session.add(new_custody)
    db.session.flush()

    before_tool = tool.to_dict()
    tool.status = _tool_target_status(destination["tipo_custodia"])
    item.status = TransferItemStatus.CONCLUIDO.value
    item.concluido_em = occurred_at
    after_custody = custody_snapshot(new_custody)

    _create_transfer_event(
        tool=tool,
        event_type=ToolTimelineEventType.TRANSFERENCIA_CONCLUIDA.value,
        title="Transferência concluída",
        description=f"{transfer.codigo}: {transfer.motivo}",
        before=before_custody,
        after=after_custody,
        occurred_at=occurred_at,
        correlation_id=correlation_id,
    )
    record_audit_log(
        action="transfers.item.complete",
        entity="transfer_item",
        entity_id=item.id_transfer_item,
        before={"custody": before_custody, "tool": before_tool},
        after={"custody": after_custody, "tool": tool.to_dict()},
        reason=transfer.motivo,
    )


def confirm_destination(
    transfer: TransferModel,
    reason: str | None = None,
) -> TransferModel:
    transfer = _locked_transfer(transfer)
    _assert_status(transfer, TransferStatus.AGUARDANDO_DESTINO.value)
    _ensure_items_have_status(
        transfer,
        TransferItemStatus.AGUARDANDO_DESTINO.value,
        "A transferência possui itens em estado incompatível com confirmação de destino.",
    )
    if not _require_destination_actor(transfer):
        raise ValueError(
            "O destino só pode ser confirmado pelo responsável destino, por usuário "
            "com escopo do destino ou por permissão transfers.override."
        )

    before = transfer_snapshot(transfer)
    now = utc_now()
    actor = _active_actor()
    correlation_id = str(uuid4())
    destination = {
        "tipo_custodia": transfer.destino_tipo_custodia,
        "id_responsavel_usuario": transfer.destino_usuario_id,
        "id_location": transfer.destino_location_id,
        "responsavel_snapshot": transfer.destino_responsavel_snapshot,
        "local_snapshot": transfer.destino_local_snapshot,
    }
    try:
        for item in transfer.itens:
            _apply_transfer_item(
                transfer=transfer,
                item=item,
                destination=destination,
                occurred_at=now,
                correlation_id=correlation_id,
            )
        transfer.destino_confirmado_por_id = _actor_id()
        transfer.destino_confirmado_em = now
        transfer.status = TransferStatus.CONCLUIDA.value
        record_internal_signature(
            action=SignatureAction.TRANSFER_CONFIRM_DESTINATION.value,
            entity="transfer",
            entity_id=transfer.id_transfer,
            result=SignatureResult.CONFIRMADO.value,
            reason=reason or "Destino confirmou o recebimento.",
            context={
                "before": before,
                "after": transfer_snapshot(transfer),
                "override": _actor_has_override(actor),
            },
            transfer_id=transfer.id_transfer,
        )
        record_audit_log(
            action=(
                "transfers.override.confirm_destination"
                if _actor_has_override(actor)
                else "transfers.confirm_destination"
            ),
            entity="transfer",
            entity_id=transfer.id_transfer,
            before=before,
            after=transfer_snapshot(transfer),
            reason=reason or "Destino confirmou o recebimento.",
        )
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ValueError("Não foi possível concluir a transferência com segurança.") from exc
    return transfer


def _restore_tool_status_for_open_transfer_item(item: TransferItemModel) -> None:
    tool = item.tool
    if tool.status == ToolStatus.TRANSFERENCIA.value:
        tool.status = item.status_ferramenta_anterior


def _close_pending_transfer_items(
    *,
    transfer: TransferModel,
    item_status: str,
    event_type: str,
    title: str,
    reason: str,
    occurred_at: datetime,
    correlation_id: str,
) -> None:
    for item in transfer.itens:
        if item.status == TransferItemStatus.CONCLUIDO.value:
            continue
        _restore_tool_status_for_open_transfer_item(item)
        item.status = item_status
        _create_transfer_event(
            tool=item.tool,
            event_type=event_type,
            title=title,
            description=f"{transfer.codigo}: {reason}",
            before=None,
            after={"status": item.tool.status, "reason": reason},
            occurred_at=occurred_at,
            correlation_id=correlation_id,
        )


def refuse_transfer(transfer: TransferModel, reason: str) -> TransferModel:
    transfer = _locked_transfer(transfer)
    if transfer.status not in PENDING_TRANSFER_STATUSES:
        raise ValueError("Apenas transferências pendentes podem ser recusadas.")
    reason = _validate_decision_reason(reason, "recusa")
    if not (_require_origin_actor(transfer) or _require_destination_actor(transfer)):
        raise ValueError(
            "A transferência só pode ser recusada por origem, destino ou override."
        )

    before = transfer_snapshot(transfer)
    now = utc_now()
    correlation_id = str(uuid4())
    _close_pending_transfer_items(
        transfer=transfer,
        item_status=TransferItemStatus.RECUSADO.value,
        event_type=ToolTimelineEventType.TRANSFERENCIA_RECUSADA.value,
        title="Transferência recusada",
        reason=reason,
        occurred_at=now,
        correlation_id=correlation_id,
    )
    transfer.status = TransferStatus.RECUSADA.value
    transfer.recusado_por_id = _actor_id()
    transfer.recusado_em = now
    transfer.motivo_recusa = reason
    record_internal_signature(
        action=SignatureAction.TRANSFER_REFUSE.value,
        entity="transfer",
        entity_id=transfer.id_transfer,
        result=SignatureResult.RECUSADO.value,
        reason=reason,
        context={"before": before, "after": transfer_snapshot(transfer)},
        transfer_id=transfer.id_transfer,
    )
    record_audit_log(
        action="transfers.refuse",
        entity="transfer",
        entity_id=transfer.id_transfer,
        before=before,
        after=transfer_snapshot(transfer),
        reason=reason,
    )
    db.session.commit()
    return transfer


def cancel_transfer(
    transfer: TransferModel,
    reason: str,
    *,
    force: bool = False,
) -> TransferModel:
    transfer = _locked_transfer(transfer)
    if transfer.status == TransferStatus.CONCLUIDA.value:
        raise ValueError(
            "Transferência concluída não pode ser cancelada. Abra uma transferência "
            "reversa ou ocorrência administrativa."
        )
    if transfer.status in CLOSED_TRANSFER_STATUSES:
        raise ValueError("Transferência já está encerrada.")
    reason = _validate_decision_reason(reason, "cancelamento")
    _require_cancel_actor(transfer, force=force)

    before = transfer_snapshot(transfer)
    now = utc_now()
    correlation_id = str(uuid4())
    _close_pending_transfer_items(
        transfer=transfer,
        item_status=TransferItemStatus.CANCELADO.value,
        event_type=ToolTimelineEventType.TRANSFERENCIA_CANCELADA.value,
        title="Transferência cancelada",
        reason=reason,
        occurred_at=now,
        correlation_id=correlation_id,
    )
    transfer.status = TransferStatus.CANCELADA.value
    transfer.cancelado_por_id = _actor_id()
    transfer.cancelado_em = now
    transfer.motivo_cancelamento = reason
    record_internal_signature(
        action=SignatureAction.TRANSFER_CANCEL.value,
        entity="transfer",
        entity_id=transfer.id_transfer,
        result=SignatureResult.CANCELADO.value,
        reason=reason,
        context={"before": before, "after": transfer_snapshot(transfer), "force": force},
        transfer_id=transfer.id_transfer,
    )
    record_audit_log(
        action="transfers.force_cancel" if force else "transfers.cancel",
        entity="transfer",
        entity_id=transfer.id_transfer,
        before=before,
        after=transfer_snapshot(transfer),
        reason=reason,
    )
    db.session.commit()
    return transfer


def expire_transfer(
    transfer: TransferModel,
    reason: str | None = None,
    *,
    commit: bool = True,
) -> TransferModel:
    transfer = _locked_transfer(transfer)
    if transfer.status not in PENDING_TRANSFER_STATUSES:
        raise ValueError("Apenas transferências pendentes podem expirar.")
    reason = (reason or "Prazo de confirmação da transferência expirado.").strip()

    before = transfer_snapshot(transfer)
    now = utc_now()
    correlation_id = str(uuid4())
    _close_pending_transfer_items(
        transfer=transfer,
        item_status=TransferItemStatus.EXPIRADO.value,
        event_type=ToolTimelineEventType.TRANSFERENCIA_CANCELADA.value,
        title="Transferência expirada",
        reason=reason,
        occurred_at=now,
        correlation_id=correlation_id,
    )
    transfer.status = TransferStatus.EXPIRADA.value
    transfer.cancelado_em = now
    transfer.motivo_cancelamento = reason
    record_audit_log(
        action="transfers.expire",
        entity="transfer",
        entity_id=transfer.id_transfer,
        before=before,
        after=transfer_snapshot(transfer),
        reason=reason,
    )
    if commit:
        db.session.commit()
    return transfer


def _transfer_expiration_cutoff(overdue_days: int | None = None) -> datetime:
    configured_days = current_app.config.get(
        "TRANSFER_EXPIRATION_DAYS",
        DEFAULT_TRANSFER_EXPIRATION_DAYS,
    )
    days = overdue_days if overdue_days is not None else int(configured_days or 0)
    if days <= 0:
        raise ValueError("Prazo de expiração de transferências deve ser maior que zero.")
    return utc_now() - timedelta(days=days)


def expire_overdue_transfers(overdue_days: int | None = None) -> dict[str, int]:
    cutoff = _transfer_expiration_cutoff(overdue_days)
    transfers = (
        db.session.execute(
            select(TransferModel)
            .where(
                TransferModel.is_deleted == false(),
                TransferModel.status.in_(PENDING_TRANSFER_STATUSES),
                TransferModel.solicitado_em < cutoff,
            )
            .order_by(TransferModel.solicitado_em.asc(), TransferModel.id_transfer.asc())
        )
        .scalars()
        .all()
    )
    expired = 0
    skipped = 0
    for transfer in transfers:
        try:
            expire_transfer(transfer, commit=False)
            expired += 1
        except ValueError:
            skipped += 1
    db.session.commit()
    return {"checked": len(transfers), "expired": expired, "skipped": skipped}
