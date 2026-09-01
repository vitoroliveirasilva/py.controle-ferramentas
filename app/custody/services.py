from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from app.audit.services import record_audit_log
from app.custody.models import ToolCustodyModel, ToolTimelineEventModel
from app.custody.repositories import get_current_custody
from app.extensions import db
from app.locations.repositories import get_location_by_id
from app.models.enums import CustodyType, ToolStatus, ToolTimelineEventType
from app.tools.models import ToolModel
from app.users.repositories import get_user_by_id

WITHOUT_CUSTODY_ALLOWED_STATUSES = {
    ToolStatus.BAIXADA.value,
    ToolStatus.INATIVA.value,
}

LOCATION_CUSTODY_TYPES = {
    CustodyType.OFICINA.value,
    CustodyType.SITE_CLIENTE.value,
    CustodyType.ALMOXARIFADO.value,
    CustodyType.DEPARTAMENTO.value,
    CustodyType.MANUTENCAO_CALIBRACAO.value,
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def _json_dumps(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _actor_identity() -> tuple[int | None, str | None]:
    if not getattr(current_user, "is_authenticated", False):
        return None, None
    return getattr(current_user, "id_usuario", None), getattr(
        current_user, "email_lower", None
    )


def custody_snapshot(custody: ToolCustodyModel | None) -> dict[str, Any] | None:
    if not custody:
        return None
    return {
        "id_custody": custody.id_custody,
        "id_tool": custody.id_tool,
        "tipo_custodia": custody.tipo_custodia,
        "id_responsavel_usuario": custody.id_responsavel_usuario,
        "id_location": custody.id_location,
        "responsavel_snapshot": custody.responsavel_snapshot,
        "local_snapshot": custody.local_snapshot,
        "inicio_em": custody.inicio_em,
        "fim_em": custody.fim_em,
        "atual": custody.atual,
        "motivo_inicio": custody.motivo_inicio,
        "motivo_fim": custody.motivo_fim,
    }


def _assert_tool_can_have_custody(tool: ToolModel) -> None:
    if tool.is_deleted:
        raise ValueError("Ferramenta removida logicamente não pode receber custódia.")
    if not tool.ativo or tool.status in WITHOUT_CUSTODY_ALLOWED_STATUSES:
        raise ValueError(
            "Ferramenta inativa ou baixada não pode receber nova custódia."
        )


def _build_target(data: dict[str, Any]) -> dict[str, Any]:
    custody_type = (data.get("tipo_custodia") or "").strip()
    reason = (data.get("motivo") or "").strip()
    if custody_type not in {item.value for item in CustodyType}:
        raise ValueError("Tipo de custódia inválido.")
    if len(reason) < 5:
        raise ValueError("Informe um motivo com pelo menos 5 caracteres.")

    if custody_type == CustodyType.TECNICO.value:
        user_id = int(data.get("id_responsavel_usuario") or 0)
        user = get_user_by_id(user_id) if user_id else None
        if not user or not user.is_active:
            raise ValueError("Selecione um técnico/usuário ativo para esta custódia.")
        return {
            "tipo_custodia": custody_type,
            "id_responsavel_usuario": user.id_usuario,
            "id_location": None,
            "responsavel_snapshot": f"{user.nome} <{user.email_lower}>",
            "local_snapshot": None,
            "motivo": reason,
        }

    if custody_type in LOCATION_CUSTODY_TYPES:
        location_id = int(data.get("id_location") or 0)
        location = get_location_by_id(location_id) if location_id else None
        if not location or location.is_deleted or not location.ativo:
            raise ValueError("Selecione um local ativo para esta custódia.")
        return {
            "tipo_custodia": custody_type,
            "id_responsavel_usuario": None,
            "id_location": location.id_location,
            "responsavel_snapshot": location.responsavel_nome or location.nome,
            "local_snapshot": f"{location.nome} ({location.codigo})",
            "motivo": reason,
        }

    raise ValueError("Tipo de custódia não suportado.")


def _assert_target_differs_from_current(
    current: ToolCustodyModel,
    target: dict[str, Any],
) -> None:
    same_target = (
        current.tipo_custodia == target["tipo_custodia"]
        and current.id_responsavel_usuario == target["id_responsavel_usuario"]
        and current.id_location == target["id_location"]
    )
    if same_target:
        raise ValueError("A nova custódia precisa ser diferente da custódia atual.")


def _create_custody(
    tool: ToolModel, target: dict[str, Any], started_at: datetime
) -> ToolCustodyModel:
    actor_id, _actor_email = _actor_identity()
    custody = ToolCustodyModel(
        id_tool=tool.id_tool,
        tipo_custodia=target["tipo_custodia"],
        id_responsavel_usuario=target["id_responsavel_usuario"],
        id_location=target["id_location"],
        responsavel_snapshot=target["responsavel_snapshot"],
        local_snapshot=target["local_snapshot"],
        inicio_em=started_at,
        atual=True,
        motivo_inicio=target["motivo"],
        criado_por_id=actor_id,
    )
    db.session.add(custody)
    return custody


def _create_timeline_event(
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
    actor_id, actor_email = _actor_identity()
    event = ToolTimelineEventModel(
        id_tool=tool.id_tool,
        event_type=event_type,
        titulo=title,
        descricao=description,
        before_payload=_json_dumps(before),
        after_payload=_json_dumps(after),
        actor_user_id=actor_id,
        actor_email=actor_email,
        occurred_at=occurred_at,
        correlation_id=correlation_id,
    )
    db.session.add(event)
    return event


def assign_initial_custody(tool: ToolModel, data: dict[str, Any]) -> ToolCustodyModel:
    _assert_tool_can_have_custody(tool)
    if get_current_custody(tool.id_tool):
        raise ValueError("Esta ferramenta já possui custódia atual.")

    target = _build_target(data)
    now = utc_now()
    correlation_id = str(uuid4())
    try:
        custody = _create_custody(tool, target, now)
        db.session.flush()
        after = custody_snapshot(custody)
        _create_timeline_event(
            tool=tool,
            event_type=ToolTimelineEventType.CUSTODIA_INICIAL.value,
            title="Custódia inicial definida",
            description=target["motivo"],
            before=None,
            after=after,
            occurred_at=now,
            correlation_id=correlation_id,
        )
        record_audit_log(
            action="custody.assign_initial",
            entity="tool_custody",
            entity_id=custody.id_custody,
            before=None,
            after=after,
            reason=target["motivo"],
        )
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ValueError(
            "Não foi possível criar custódia: já existe custódia atual."
        ) from exc
    return custody


def _replace_current_custody(
    *,
    tool: ToolModel,
    current: ToolCustodyModel,
    target: dict[str, Any],
    action: str,
    timeline_title: str,
    timeline_event_type: str = ToolTimelineEventType.CUSTODIA_TRANSFERIDA.value,
) -> ToolCustodyModel:
    _assert_target_differs_from_current(current, target)
    now = utc_now()
    actor_id, _actor_email = _actor_identity()
    before = custody_snapshot(current)
    correlation_id = str(uuid4())

    try:
        current.atual = False
        current.fim_em = now
        current.motivo_fim = target["motivo"]
        current.encerrado_por_id = actor_id
        db.session.flush()

        new_custody = _create_custody(tool, target, now)
        db.session.flush()
        after = custody_snapshot(new_custody)
        _create_timeline_event(
            tool=tool,
            event_type=timeline_event_type,
            title=timeline_title,
            description=target["motivo"],
            before=before,
            after=after,
            occurred_at=now,
            correlation_id=correlation_id,
        )
        record_audit_log(
            action=action,
            entity="tool_custody",
            entity_id=new_custody.id_custody,
            before=before,
            after=after,
            reason=target["motivo"],
        )
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise ValueError("Não foi possível alterar custódia com segurança.") from exc
    return new_custody


# Troca administrativa de custódia, usada apenas com custody.force_change
def force_change_custody(tool: ToolModel, data: dict[str, Any]) -> ToolCustodyModel:
    _assert_tool_can_have_custody(tool)
    current = get_current_custody(tool.id_tool)
    if not current:
        raise ValueError("Esta ferramenta ainda não possui custódia atual.")

    target = _build_target(data)
    if len(target["motivo"]) < 15:
        raise ValueError(
            "Informe uma justificativa administrativa com pelo menos 15 caracteres."
        )
    return _replace_current_custody(
        tool=tool,
        current=current,
        target=target,
        action="custody.force_change",
        timeline_title="Custódia alterada administrativamente",
    )


# Compatibilidade para chamadas antigas, sem exigir custody.force_change
# Rotas novas devem exigir custody.force_change e chamar force_change_custody
def change_custody(tool: ToolModel, data: dict[str, Any]) -> ToolCustodyModel:
    return force_change_custody(tool, data)


def close_current_custody(
    tool: ToolModel,
    reason: str,
    *,
    action: str = "custody.close",
    event_type: str = ToolTimelineEventType.CUSTODIA_ENCERRADA.value,
    title: str = "Custódia encerrada",
    occurred_at: datetime | None = None,
    correlation_id: str | None = None,
    commit: bool = True,
    require_current: bool = False,
) -> ToolCustodyModel | None:
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise ValueError("Informe o motivo do encerramento da custódia.")

    current = get_current_custody(tool.id_tool)
    if not current:
        if require_current:
            raise ValueError("Esta ferramenta não possui custódia atual para encerrar.")
        return None

    now = occurred_at or utc_now()
    actor_id, _actor_email = _actor_identity()
    before = custody_snapshot(current)
    current.atual = False
    current.fim_em = now
    current.motivo_fim = reason
    current.encerrado_por_id = actor_id
    db.session.flush()
    after = custody_snapshot(current)

    _create_timeline_event(
        tool=tool,
        event_type=event_type,
        title=title,
        description=reason,
        before=before,
        after=after,
        occurred_at=now,
        correlation_id=correlation_id or str(uuid4()),
    )
    record_audit_log(
        action=action,
        entity="tool_custody",
        entity_id=current.id_custody,
        before=before,
        after=after,
        reason=reason,
    )
    if commit:
        db.session.commit()
    return current


def assert_active_tool_has_custody_when_required(tool: ToolModel) -> None:
    if (
        tool.ativo
        and not tool.is_deleted
        and tool.status not in WITHOUT_CUSTODY_ALLOWED_STATUSES
        and not get_current_custody(tool.id_tool)
    ):
        raise ValueError("Ferramenta ativa precisa possuir custódia atual.")
