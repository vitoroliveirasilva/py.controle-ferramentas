from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import current_app
from flask_login import current_user
from werkzeug.datastructures import FileStorage

from app.audit.services import record_audit_log
from app.core.uploads import remove_upload_file, safe_upload_path, store_upload
from app.custody.models import ToolTimelineEventModel
from app.custody.repositories import get_current_custody
from app.custody.services import close_current_custody
from app.extensions import db
from app.models.enums import (
    OccurrenceStatus,
    OccurrenceType,
    SignatureAction,
    SignatureResult,
    ToolStatus,
    ToolTimelineEventType,
)
from app.occurrences.models import OccurrenceAttachmentModel, OccurrenceModel
from app.permissions.scope_filters import ScopeAccessDenied, assert_can_access_tool
from app.signatures.services import record_internal_signature
from app.tools.models import ToolModel
from app.tools.repositories import get_tool_by_codigo_interno

PATRIMONIAL_TYPES = {
    OccurrenceType.BAIXA.value,
    OccurrenceType.PERDA.value,
    OccurrenceType.EXTRAVIO.value,
    OccurrenceType.SUBSTITUICAO.value,
    OccurrenceType.REINTEGRACAO.value,
}
APPROVAL_REQUIRED_TYPES = {
    OccurrenceType.BAIXA.value,
    OccurrenceType.SUBSTITUICAO.value,
    OccurrenceType.REINTEGRACAO.value,
}
CUSTODY_CLOSING_TYPES = {
    OccurrenceType.PERDA.value,
    OccurrenceType.EXTRAVIO.value,
    OccurrenceType.BAIXA.value,
    OccurrenceType.SUBSTITUICAO.value,
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


def _generate_occurrence_code(now: datetime) -> str:
    return f"OCO-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6].upper()}"


def occurrence_snapshot(occurrence: OccurrenceModel) -> dict[str, Any]:
    return {
        "id_occurrence": occurrence.id_occurrence,
        "codigo": occurrence.codigo,
        "id_tool": occurrence.id_tool,
        "tipo_ocorrencia": occurrence.tipo_ocorrencia,
        "status": occurrence.status,
        "motivo": occurrence.motivo,
        "impacto_patrimonial": occurrence.impacto_patrimonial,
        "ativo_imobilizado_snapshot": occurrence.ativo_imobilizado_snapshot,
        "decisao": occurrence.decisao,
        "decisao_motivo": occurrence.decisao_motivo,
    }


def _custody_snapshot_for_tool(tool: ToolModel) -> tuple[str | None, str | None]:
    custody = get_current_custody(tool.id_tool)
    if not custody:
        return None, None
    responsible = custody.responsavel_snapshot or custody.local_snapshot
    payload = {
        "id_custody": custody.id_custody,
        "tipo_custodia": custody.tipo_custodia,
        "id_responsavel_usuario": custody.id_responsavel_usuario,
        "id_location": custody.id_location,
        "responsavel_snapshot": custody.responsavel_snapshot,
        "local_snapshot": custody.local_snapshot,
        "inicio_em": custody.inicio_em,
    }
    return responsible, _json_dumps(payload)


def _assert_tool_can_receive_occurrence(tool: ToolModel) -> None:
    if tool.is_deleted:
        raise ValueError("Ferramenta removida logicamente não aceita ocorrência.")


def _validate_occurrence_payload(
    data: dict[str, Any],
) -> tuple[ToolModel, str, str, str]:
    tool_code = (data.get("codigo_ferramenta") or "").strip()
    occurrence_type = (data.get("tipo_ocorrencia") or "").strip()
    reason = (data.get("motivo") or "").strip()
    description = (data.get("descricao") or "").strip()

    tool = get_tool_by_codigo_interno(tool_code)
    if not tool:
        raise ValueError("Ferramenta não encontrada pelo código interno informado.")
    _assert_tool_can_receive_occurrence(tool)
    if getattr(current_user, "is_authenticated", False):
        try:
            assert_can_access_tool(current_user, tool)
        except ScopeAccessDenied as exc:
            message = "Você não possui escopo para registrar ocorrência nesta ferramenta."
            raise ValueError(message) from exc

    if occurrence_type not in {item.value for item in OccurrenceType}:
        raise ValueError("Tipo de ocorrência inválido.")
    if len(reason) < 5:
        raise ValueError("Informe um motivo com pelo menos 5 caracteres.")
    if len(description) < 10:
        raise ValueError("Informe uma descrição com pelo menos 10 caracteres.")
    return tool, occurrence_type, reason, description


def _initial_status_for(tool: ToolModel, occurrence_type: str) -> str:
    if occurrence_type in APPROVAL_REQUIRED_TYPES:
        return OccurrenceStatus.AGUARDANDO_APROVACAO.value
    if tool.ativo_imobilizado and occurrence_type in PATRIMONIAL_TYPES:
        return OccurrenceStatus.AGUARDANDO_APROVACAO.value
    return OccurrenceStatus.ABERTA.value


def _apply_approved_tool_effect(occurrence: OccurrenceModel) -> dict[str, Any]:
    tool = occurrence.tool
    before = {
        "status": tool.status,
        "ativo": tool.ativo,
        "observacoes": tool.observacoes,
    }
    if occurrence.tipo_ocorrencia in CUSTODY_CLOSING_TYPES:
        tool.status = ToolStatus.BAIXADA.value
        tool.ativo = False
    elif occurrence.tipo_ocorrencia == OccurrenceType.DANO.value:
        tool.status = ToolStatus.DANIFICADA.value
    elif occurrence.tipo_ocorrencia == OccurrenceType.MANUTENCAO.value:
        tool.status = ToolStatus.MANUTENCAO.value
    elif occurrence.tipo_ocorrencia == OccurrenceType.CALIBRACAO.value:
        tool.status = ToolStatus.CALIBRACAO.value
    elif occurrence.tipo_ocorrencia == OccurrenceType.REINTEGRACAO.value:
        if not get_current_custody(tool.id_tool):
            raise ValueError(
                "Reintegração exige custódia atual ou fluxo administrativo de "
                "reentrada antes da aprovação."
            )
        tool.status = ToolStatus.DISPONIVEL.value
        tool.ativo = True

    after = {
        "status": tool.status,
        "ativo": tool.ativo,
        "observacoes": tool.observacoes,
    }
    return {"before": before, "after": after}


def _timeline_event(
    *,
    occurrence: OccurrenceModel,
    event_type: str,
    title: str,
    description: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    db.session.add(
        ToolTimelineEventModel(
            id_tool=occurrence.id_tool,
            event_type=event_type,
            titulo=title,
            descricao=description,
            before_payload=_json_dumps(before),
            after_payload=_json_dumps(after),
            actor_user_id=_actor_id(),
            actor_email=_actor_email(),
            occurred_at=utc_now(),
            correlation_id=occurrence.codigo,
        )
    )


def create_occurrence(data: dict[str, Any]) -> OccurrenceModel:
    tool, occurrence_type, reason, description = _validate_occurrence_payload(data)
    now = utc_now()
    responsible, custody_snapshot = _custody_snapshot_for_tool(tool)
    occurrence = OccurrenceModel(
        codigo=_generate_occurrence_code(now),
        id_tool=tool.id_tool,
        tipo_ocorrencia=occurrence_type,
        status=_initial_status_for(tool, occurrence_type),
        motivo=reason,
        descricao=description,
        responsavel_atual_snapshot=responsible,
        custodia_snapshot=custody_snapshot,
        ativo_imobilizado_snapshot=tool.ativo_imobilizado,
        impacto_patrimonial=bool(tool.ativo_imobilizado)
        or occurrence_type in PATRIMONIAL_TYPES,
        fato_em=data.get("fato_em"),
        registrado_em=now,
        registrante_id=_actor_id(),
        registrante_email=_actor_email(),
    )
    db.session.add(occurrence)
    db.session.flush()

    after = occurrence_snapshot(occurrence)
    _timeline_event(
        occurrence=occurrence,
        event_type=ToolTimelineEventType.OCORRENCIA_ABERTA.value,
        title="Ocorrência registrada",
        description=f"Ocorrência {occurrence.codigo} registrada: {reason}.",
        after=after,
    )
    record_audit_log(
        action="occurrence.create",
        entity="occurrence",
        entity_id=occurrence.id_occurrence,
        after=after,
        reason=reason,
    )
    db.session.commit()
    return occurrence


def send_to_analysis(occurrence: OccurrenceModel, reason: str) -> OccurrenceModel:
    if occurrence.status not in {
        OccurrenceStatus.ABERTA.value,
        OccurrenceStatus.AGUARDANDO_APROVACAO.value,
    }:
        raise ValueError(
            "Somente ocorrência aberta ou aguardando aprovação pode entrar em análise."
        )
    if len((reason or "").strip()) < 5:
        raise ValueError("Informe um motivo com pelo menos 5 caracteres.")
    before = occurrence_snapshot(occurrence)
    occurrence.status = OccurrenceStatus.EM_ANALISE.value
    occurrence.decisao_motivo = reason.strip()
    after = occurrence_snapshot(occurrence)
    _timeline_event(
        occurrence=occurrence,
        event_type=ToolTimelineEventType.OCORRENCIA_ABERTA.value,
        title="Ocorrência em análise",
        description=reason.strip(),
        before=before,
        after=after,
    )
    record_audit_log(
        action="occurrence.analyze",
        entity="occurrence",
        entity_id=occurrence.id_occurrence,
        before=before,
        after=after,
        reason=reason.strip(),
    )
    db.session.commit()
    return occurrence


def approve_occurrence(occurrence: OccurrenceModel, reason: str) -> OccurrenceModel:
    if occurrence.status not in {
        OccurrenceStatus.ABERTA.value,
        OccurrenceStatus.EM_ANALISE.value,
        OccurrenceStatus.AGUARDANDO_APROVACAO.value,
    }:
        raise ValueError("Ocorrência não está em status aprovável.")
    if len((reason or "").strip()) < 5:
        raise ValueError("Informe o motivo da aprovação.")
    before = occurrence_snapshot(occurrence)
    tool_change = _apply_approved_tool_effect(occurrence)
    custody_closed = None
    now = utc_now()
    if occurrence.tipo_ocorrencia in CUSTODY_CLOSING_TYPES:
        custody_closed = close_current_custody(
            occurrence.tool,
            f"Ocorrência {occurrence.codigo}: {reason.strip()}",
            action="custody.close_by_occurrence",
            title="Custódia encerrada por ocorrência patrimonial",
            occurred_at=now,
            correlation_id=occurrence.codigo,
            commit=False,
        )

    occurrence.status = OccurrenceStatus.APROVADA.value
    occurrence.decisao = "aprovada"
    occurrence.decisao_motivo = reason.strip()
    occurrence.aprovado_por_id = _actor_id()
    occurrence.aprovado_em = now
    after = occurrence_snapshot(occurrence)
    tool_change["custody_closed_id"] = (
        custody_closed.id_custody if custody_closed is not None else None
    )

    _timeline_event(
        occurrence=occurrence,
        event_type=ToolTimelineEventType.OCORRENCIA_APROVADA.value,
        title="Ocorrência aprovada",
        description=reason.strip(),
        before={"occurrence": before, "tool": tool_change["before"]},
        after={"occurrence": after, "tool": tool_change["after"]},
    )
    record_internal_signature(
        action=SignatureAction.OCCURRENCE_APPROVE.value,
        entity="occurrence",
        entity_id=occurrence.id_occurrence,
        result=SignatureResult.APROVADO.value,
        reason=reason.strip(),
        context={
            "occurrence_before": before,
            "occurrence_after": after,
            "tool": tool_change,
        },
        occurrence_id=occurrence.id_occurrence,
    )
    record_audit_log(
        action="occurrence.approve",
        entity="occurrence",
        entity_id=occurrence.id_occurrence,
        before={"occurrence": before, "tool": tool_change["before"]},
        after={"occurrence": after, "tool": tool_change["after"]},
        reason=reason.strip(),
    )
    db.session.commit()
    return occurrence


def reject_occurrence(occurrence: OccurrenceModel, reason: str) -> OccurrenceModel:
    if occurrence.status not in {
        OccurrenceStatus.ABERTA.value,
        OccurrenceStatus.EM_ANALISE.value,
        OccurrenceStatus.AGUARDANDO_APROVACAO.value,
    }:
        raise ValueError("Ocorrência não está em status recusável.")
    if len((reason or "").strip()) < 5:
        raise ValueError("Informe o motivo da recusa.")
    before = occurrence_snapshot(occurrence)
    occurrence.status = OccurrenceStatus.RECUSADA.value
    occurrence.decisao = "recusada"
    occurrence.decisao_motivo = reason.strip()
    occurrence.aprovado_por_id = _actor_id()
    occurrence.aprovado_em = utc_now()
    after = occurrence_snapshot(occurrence)
    _timeline_event(
        occurrence=occurrence,
        event_type=ToolTimelineEventType.OCORRENCIA_RECUSADA.value,
        title="Ocorrência recusada",
        description=reason.strip(),
        before=before,
        after=after,
    )
    record_internal_signature(
        action=SignatureAction.OCCURRENCE_REJECT.value,
        entity="occurrence",
        entity_id=occurrence.id_occurrence,
        result=SignatureResult.RECUSADO.value,
        reason=reason.strip(),
        context={"before": before, "after": after},
        occurrence_id=occurrence.id_occurrence,
    )
    record_audit_log(
        action="occurrence.reject",
        entity="occurrence",
        entity_id=occurrence.id_occurrence,
        before=before,
        after=after,
        reason=reason.strip(),
    )
    db.session.commit()
    return occurrence


def resolve_occurrence(occurrence: OccurrenceModel, resolution: str) -> OccurrenceModel:
    if occurrence.status not in {
        OccurrenceStatus.ABERTA.value,
        OccurrenceStatus.EM_ANALISE.value,
        OccurrenceStatus.APROVADA.value,
    }:
        raise ValueError("Ocorrência não está em status resolvível.")
    if len((resolution or "").strip()) < 5:
        raise ValueError("Informe a resolução da ocorrência.")
    before = occurrence_snapshot(occurrence)
    occurrence.status = OccurrenceStatus.RESOLVIDA.value
    occurrence.decisao = occurrence.decisao or "resolvida"
    occurrence.resolvido_por_id = _actor_id()
    occurrence.resolvido_em = utc_now()
    occurrence.observacoes_resolucao = resolution.strip()
    after = occurrence_snapshot(occurrence)
    _timeline_event(
        occurrence=occurrence,
        event_type=ToolTimelineEventType.OCORRENCIA_RESOLVIDA.value,
        title="Ocorrência resolvida",
        description=resolution.strip(),
        before=before,
        after=after,
    )
    record_internal_signature(
        action=SignatureAction.OCCURRENCE_RESOLVE.value,
        entity="occurrence",
        entity_id=occurrence.id_occurrence,
        result=SignatureResult.RESOLVIDO.value,
        reason=resolution.strip(),
        context={"before": before, "after": after},
        occurrence_id=occurrence.id_occurrence,
    )
    record_audit_log(
        action="occurrence.resolve",
        entity="occurrence",
        entity_id=occurrence.id_occurrence,
        before=before,
        after=after,
        reason=resolution.strip(),
    )
    db.session.commit()
    return occurrence


def cancel_occurrence(occurrence: OccurrenceModel, reason: str) -> OccurrenceModel:
    if occurrence.status in {
        OccurrenceStatus.RESOLVIDA.value,
        OccurrenceStatus.CANCELADA.value,
    }:
        raise ValueError("Ocorrência já está encerrada.")
    if len((reason or "").strip()) < 5:
        raise ValueError("Informe o motivo do cancelamento.")
    before = occurrence_snapshot(occurrence)
    occurrence.status = OccurrenceStatus.CANCELADA.value
    occurrence.decisao = "cancelada"
    occurrence.decisao_motivo = reason.strip()
    after = occurrence_snapshot(occurrence)
    record_internal_signature(
        action=SignatureAction.OCCURRENCE_CANCEL.value,
        entity="occurrence",
        entity_id=occurrence.id_occurrence,
        result=SignatureResult.CANCELADO.value,
        reason=reason.strip(),
        context={"before": before, "after": after},
        occurrence_id=occurrence.id_occurrence,
    )
    record_audit_log(
        action="occurrence.cancel",
        entity="occurrence",
        entity_id=occurrence.id_occurrence,
        before=before,
        after=after,
        reason=reason.strip(),
    )
    db.session.commit()
    return occurrence


def get_occurrence_attachment_path(attachment: OccurrenceAttachmentModel) -> Path:
    path = safe_upload_path(attachment.filename_storage)
    if path is None:
        raise ValueError("Caminho do anexo inválido.")
    if path.exists() or not attachment.filename_storage.startswith("uploads/"):
        return path

    # Compatibilidade com anexos salvos antes da centralização de uploads
    legacy_root = Path(current_app.instance_path).resolve()
    legacy_path = (legacy_root / attachment.filename_storage).resolve()
    if legacy_root not in legacy_path.parents and legacy_path != legacy_root:
        raise ValueError("Caminho legado do anexo inválido.")
    return legacy_path


def add_occurrence_attachment(
    occurrence: OccurrenceModel,
    file: FileStorage | None,
    description: str | None = None,
) -> OccurrenceAttachmentModel:
    stored = store_upload(
        file,
        allowed_extensions=current_app.config["ALLOWED_OCCURRENCE_ATTACHMENT_EXTENSIONS"],
        max_mb=int(current_app.config["OCCURRENCE_ATTACHMENT_MAX_MB"]),
        directory_parts=("occurrences", str(occurrence.id_occurrence)),
        default_filename="anexo.pdf",
    )

    try:
        attachment = OccurrenceAttachmentModel(
            id_occurrence=occurrence.id_occurrence,
            filename_original=stored.original_filename,
            filename_storage=stored.relative_path,
            content_type=stored.content_type,
            tamanho_bytes=stored.size_bytes,
            uploaded_by_id=_actor_id(),
            uploaded_at=utc_now(),
            descricao=(description or "").strip() or None,
        )
        db.session.add(attachment)
        db.session.flush()
        record_audit_log(
            action="occurrence.attachment.add",
            entity="occurrence_attachment",
            entity_id=attachment.id_attachment,
            after={
                "id_occurrence": occurrence.id_occurrence,
                "filename_original": stored.original_filename,
                "content_type": stored.content_type,
                "tamanho_bytes": stored.size_bytes,
            },
            reason=description,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        remove_upload_file(stored.absolute_path)
        raise
    return attachment
