from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import current_app
from flask_login import current_user
from werkzeug.datastructures import FileStorage

from app.audit.services import record_audit_log
from app.categories.repositories import get_category_by_id
from app.core.uploads import remove_upload_file, safe_upload_path, store_upload
from app.custody.models import ToolTimelineEventModel
from app.custody.repositories import get_current_custody
from app.custody.services import (
    WITHOUT_CUSTODY_ALLOWED_STATUSES,
    close_current_custody,
)
from app.extensions import db
from app.models.enums import ToolStatus, ToolTimelineEventType
from app.tools.models import ToolModel
from app.tools.repositories import (
    get_tool_by_ativo_imobilizado,
    get_tool_by_codigo_interno,
    get_tool_by_numero_serie,
    normalize_code,
    normalize_optional_code,
)

CRITICAL_FIELDS = {
    "codigo_interno",
    "ativo_imobilizado",
    "numero_serie",
    "status",
    "id_categoria",
    "criticidade",
    "controle_individual",
    "requer_calibracao",
    "ativo",
}


def _snapshot(tool: ToolModel) -> dict[str, Any]:
    return tool.to_dict()


def _clean(value: str | None) -> str | None:
    return (value or "").strip() or None


def _assert_unique_identifiers(
    data: dict[str, Any], current_id: int | None = None
) -> None:
    existing = get_tool_by_codigo_interno(data["codigo_interno"])
    if existing and existing.id_tool != current_id:
        raise ValueError("Já existe ferramenta com este código interno.")

    existing_asset = get_tool_by_ativo_imobilizado(data.get("ativo_imobilizado"))
    if existing_asset and existing_asset.id_tool != current_id:
        raise ValueError("Já existe ferramenta com este ativo imobilizado.")

    existing_serial = get_tool_by_numero_serie(data.get("numero_serie"))
    if existing_serial and existing_serial.id_tool != current_id:
        raise ValueError("Já existe ferramenta com este número de série.")


def _validate_business_rules(data: dict[str, Any]) -> None:
    category = get_category_by_id(int(data["id_categoria"]))
    if not category or category.is_deleted or not category.ativo:
        raise ValueError("Categoria inválida ou inativa.")

    if category.requer_numero_serie and not (data.get("numero_serie") or "").strip():
        raise ValueError("Esta categoria exige número de série.")

    if data.get("status") == ToolStatus.BAIXADA.value and bool(data.get("ativo")):
        raise ValueError("Ferramenta baixada deve ficar inativa operacionalmente.")


def _apply(tool: ToolModel, data: dict[str, Any]) -> None:
    tool.codigo_interno = normalize_code(data["codigo_interno"])
    tool.nome = data["nome"].strip()
    tool.descricao = _clean(data.get("descricao"))
    tool.id_categoria = int(data["id_categoria"])
    tool.status = data["status"]
    tool.criticidade = data["criticidade"]
    tool.ativo_imobilizado = normalize_optional_code(data.get("ativo_imobilizado"))
    tool.numero_serie = normalize_optional_code(data.get("numero_serie"))
    tool.marca = _clean(data.get("marca"))
    tool.modelo = _clean(data.get("modelo"))
    tool.controle_individual = bool(data.get("controle_individual"))
    tool.requer_calibracao = bool(data.get("requer_calibracao"))
    tool.ativo = bool(data.get("ativo"))
    tool.observacoes = _clean(data.get("observacoes"))


def create_tool(data: dict[str, Any]) -> ToolModel:
    _assert_unique_identifiers(data)
    _validate_business_rules(data)
    tool = ToolModel(
        codigo_interno=normalize_code(data["codigo_interno"]),
        nome="",
        id_categoria=int(data["id_categoria"]),
    )
    _apply(tool, data)
    db.session.add(tool)
    db.session.flush()
    record_audit_log(
        action="tools.create",
        entity="tool",
        entity_id=tool.id_tool,
        after=_snapshot(tool),
        reason=data.get("motivo") or "Criação de ferramenta.",
    )
    db.session.commit()
    return tool


def update_tool(
    tool: ToolModel, data: dict[str, Any], *, can_critical_update: bool
) -> ToolModel:
    _assert_unique_identifiers(data, current_id=tool.id_tool)
    _validate_business_rules(data)
    before = _snapshot(tool)
    proposed = {
        **before,
        "codigo_interno": normalize_code(data["codigo_interno"]),
        "ativo_imobilizado": normalize_optional_code(data.get("ativo_imobilizado")),
        "numero_serie": normalize_optional_code(data.get("numero_serie")),
        "status": data["status"],
        "id_categoria": int(data["id_categoria"]),
        "criticidade": data["criticidade"],
        "controle_individual": bool(data.get("controle_individual")),
        "requer_calibracao": bool(data.get("requer_calibracao")),
        "ativo": bool(data.get("ativo")),
    }
    changed_critical = [
        field for field in CRITICAL_FIELDS if before.get(field) != proposed.get(field)
    ]
    if changed_critical:
        if not can_critical_update:
            raise PermissionError(
                "Permissão tools.critical_update necessária para alterar campos críticos."
            )
        if not (data.get("motivo") or "").strip():
            raise ValueError(
                "Informe o motivo para alterar campos críticos da ferramenta."
            )

    _apply(tool, data)

    is_reactivation = (
        (not before.get("ativo") or before.get("status") in WITHOUT_CUSTODY_ALLOWED_STATUSES)
        and tool.ativo
        and tool.status not in WITHOUT_CUSTODY_ALLOWED_STATUSES
    )
    if is_reactivation and not get_current_custody(tool.id_tool):
        raise ValueError(
            "Defina uma custódia atual antes de reativar a ferramenta para operação."
        )

    if tool.status == ToolStatus.BAIXADA.value and before.get("status") != ToolStatus.BAIXADA.value:
        close_current_custody(
            tool,
            data.get("motivo") or "Baixa administrativa da ferramenta.",
            action="custody.close_by_tool_status",
            title="Custódia encerrada por baixa administrativa",
            commit=False,
        )

    db.session.flush()
    record_audit_log(
        action="tools.update",
        entity="tool",
        entity_id=tool.id_tool,
        before=before,
        after=_snapshot(tool),
        reason=data.get("motivo"),
    )
    db.session.commit()
    return tool


def set_tool_active(tool: ToolModel, active: bool, reason: str) -> None:
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Informe o motivo da alteração de status.")
    if active and not get_current_custody(tool.id_tool):
        raise ValueError(
            "Defina uma custódia atual antes de reativar a ferramenta para operação."
        )

    before = _snapshot(tool)
    tool.ativo = active
    if active and tool.status in WITHOUT_CUSTODY_ALLOWED_STATUSES:
        tool.status = ToolStatus.DISPONIVEL.value
    if not active and tool.status != ToolStatus.BAIXADA.value:
        tool.status = ToolStatus.INATIVA.value
    record_audit_log(
        action="tools.activate" if active else "tools.deactivate",
        entity="tool",
        entity_id=tool.id_tool,
        before=before,
        after=_snapshot(tool),
        reason=reason,
    )
    db.session.commit()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _actor_id() -> int | None:
    if not getattr(current_user, "is_authenticated", False):
        return None
    return getattr(current_user, "id_usuario", None)


def _actor_email() -> str | None:
    if not getattr(current_user, "is_authenticated", False):
        return None
    return getattr(current_user, "email_lower", None)


def _json_dumps(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def get_reference_photo_path(tool: ToolModel) -> Path | None:
    path = safe_upload_path(tool.referencia_foto_path)
    if not path or not path.exists():
        return None
    return path


def _record_photo_timeline(
    tool: ToolModel,
    *,
    event_type: str,
    title: str,
    description: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> None:
    db.session.add(
        ToolTimelineEventModel(
            id_tool=tool.id_tool,
            event_type=event_type,
            titulo=title,
            descricao=description,
            before_payload=_json_dumps(before),
            after_payload=_json_dumps(after),
            actor_user_id=_actor_id(),
            actor_email=_actor_email(),
            occurred_at=_utc_now(),
            correlation_id=f"tool-photo-{tool.id_tool}",
        )
    )


def save_reference_photo(
    tool: ToolModel,
    file: FileStorage | None,
    reason: str | None = None,
) -> ToolModel:
    before = _snapshot(tool)
    old_path = safe_upload_path(tool.referencia_foto_path)
    stored = store_upload(
        file,
        allowed_extensions=current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
        max_mb=int(current_app.config["TOOL_REFERENCE_PHOTO_MAX_MB"]),
        directory_parts=("tools", str(tool.id_tool), "reference"),
        default_filename="referencia.jpg",
    )

    try:
        tool.referencia_foto_path = stored.relative_path
        tool.referencia_foto_filename = stored.original_filename
        tool.referencia_foto_content_type = stored.content_type
        tool.referencia_foto_size_bytes = stored.size_bytes
        tool.referencia_foto_uploaded_at = _utc_now()
        tool.referencia_foto_uploaded_by_id = _actor_id()

        after = _snapshot(tool)
        _record_photo_timeline(
            tool,
            event_type=ToolTimelineEventType.REFERENCIA_FOTO_ATUALIZADA.value,
            title="Foto de referência atualizada",
            description=reason or "Foto de referência da ferramenta atualizada.",
            before=before,
            after=after,
        )
        record_audit_log(
            action="tools.reference_photo.upload",
            entity="tool",
            entity_id=tool.id_tool,
            before=before,
            after={
                **after,
                "arquivo": {
                    "filename": stored.original_filename,
                    "content_type": stored.content_type,
                    "size_bytes": stored.size_bytes,
                },
            },
            reason=reason or "Atualização de foto de referência.",
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        remove_upload_file(stored.absolute_path)
        raise

    if old_path and old_path.exists() and old_path != stored.absolute_path:
        remove_upload_file(old_path)
    return tool


def delete_reference_photo(tool: ToolModel, reason: str | None = None) -> ToolModel:
    if not tool.referencia_foto_path:
        raise ValueError("Ferramenta não possui foto de referência cadastrada.")
    if not (reason or "").strip():
        raise ValueError("Informe o motivo para remover a foto de referência.")

    before = _snapshot(tool)
    old_path = safe_upload_path(tool.referencia_foto_path)
    tool.referencia_foto_path = None
    tool.referencia_foto_filename = None
    tool.referencia_foto_content_type = None
    tool.referencia_foto_size_bytes = None
    tool.referencia_foto_uploaded_at = None
    tool.referencia_foto_uploaded_by_id = None

    after = _snapshot(tool)
    _record_photo_timeline(
        tool,
        event_type=ToolTimelineEventType.REFERENCIA_FOTO_REMOVIDA.value,
        title="Foto de referência removida",
        description=reason.strip(),
        before=before,
        after=after,
    )
    record_audit_log(
        action="tools.reference_photo.delete",
        entity="tool",
        entity_id=tool.id_tool,
        before=before,
        after=after,
        reason=reason,
    )
    db.session.commit()

    if old_path and old_path.exists():
        remove_upload_file(old_path)
    return tool
