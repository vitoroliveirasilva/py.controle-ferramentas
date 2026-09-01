from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from flask import current_app, has_request_context, request
from flask_login import current_user
from sqlalchemy import Select, select

from app.audit.models import AuditLogModel
from app.extensions import db

SENSITIVE_KEYWORDS = {
    "api_key",
    "apikey",
    "authorization",
    "body",
    "conteudo",
    "cookie",
    "file",
    "headers",
    "password",
    "payload",
    "secret",
    "senha",
    "token",
    "x-api-key",
}
SAFE_AUDIT_METADATA_KEYS = {
    "content_type",
    "filename",
    "original_filename",
    "size_bytes",
}
MAX_AUDIT_STRING_LENGTH = 600
MAX_AUDIT_LIST_ITEMS = 25
MAX_USER_AGENT_LENGTH = 255


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    if normalized in SAFE_AUDIT_METADATA_KEYS:
        return False
    return any(keyword in normalized for keyword in SENSITIVE_KEYWORDS)


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _is_sensitive_key(str(key)) else _redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple | set):
        items = list(value)
        redacted = [_redact_value(item) for item in items[:MAX_AUDIT_LIST_ITEMS]]
        if len(items) > MAX_AUDIT_LIST_ITEMS:
            redacted.append(f"... mais {len(items) - MAX_AUDIT_LIST_ITEMS} item(ns)")
        return redacted
    if isinstance(value, str):
        cleaned = value.strip()
        if len(cleaned) > MAX_AUDIT_STRING_LENGTH:
            return cleaned[:MAX_AUDIT_STRING_LENGTH] + "...[truncated]"
        return cleaned
    return value


def _json_dumps(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(_redact_value(value), ensure_ascii=False, default=str, sort_keys=True)


def _current_user_identity() -> tuple[int | None, str | None]:
    if not getattr(current_user, "is_authenticated", False):
        return None, None
    return getattr(current_user, "id_usuario", None), getattr(
        current_user, "email_lower", None
    )


def _safe_client_ip() -> str | None:
    if not has_request_context():
        return None
    if current_app.config.get("APP_TRUST_PROXY_HEADERS") and request.access_route:
        return request.access_route[0][:80]
    return request.remote_addr[:80] if request.remote_addr else None


def record_audit_log(
    *,
    action: str,
    entity: str,
    entity_id: str | int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    result: str = "success",
    commit: bool = False,
) -> AuditLogModel:
    user_id, user_email = _current_user_identity()
    user_agent = request.headers.get("User-Agent") if has_request_context() else None

    log = AuditLogModel(
        id_usuario=user_id,
        usuario_email=user_email,
        acao=action,
        entidade=entity,
        entidade_id=str(entity_id) if entity_id is not None else None,
        antes=_json_dumps(before),
        depois=_json_dumps(after),
        motivo=reason,
        ip=_safe_client_ip(),
        user_agent=user_agent[:MAX_USER_AGENT_LENGTH] if user_agent else None,
        correlation_id=str(uuid4()),
        resultado=result,
        occurred_at=datetime.now(UTC),
    )
    db.session.add(log)
    if commit:
        db.session.commit()
    return log


def audit_log_statement(
    *,
    search: str | None = None,
    action: str | None = None,
    entity: str | None = None,
    result: str | None = None,
    user_email: str | None = None,
) -> Select:
    stmt = select(AuditLogModel)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            AuditLogModel.acao.ilike(like)
            | AuditLogModel.entidade.ilike(like)
            | AuditLogModel.entidade_id.ilike(like)
            | AuditLogModel.usuario_email.ilike(like)
            | AuditLogModel.motivo.ilike(like)
        )
    if action:
        stmt = stmt.where(AuditLogModel.acao == action)
    if entity:
        stmt = stmt.where(AuditLogModel.entidade == entity)
    if result:
        stmt = stmt.where(AuditLogModel.resultado == result)
    if user_email:
        stmt = stmt.where(AuditLogModel.usuario_email.ilike(f"%{user_email.strip()}%"))
    return stmt.order_by(AuditLogModel.occurred_at.desc(), AuditLogModel.id_audit_log.desc())


def get_audit_log_by_id(audit_log_id: int) -> AuditLogModel | None:
    return db.session.get(AuditLogModel, audit_log_id)
