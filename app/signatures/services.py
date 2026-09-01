from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from flask import has_request_context, request
from flask_login import current_user

from app.audit.services import record_audit_log
from app.extensions import db
from app.models.enums import SignatureMethod, SignatureResult
from app.signatures.models import InternalSignatureModel
from app.users.models import UserModel


def utc_now() -> datetime:
    return datetime.now(UTC)


def _json_dumps(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)


def _request_ip() -> str | None:
    if not has_request_context():
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()[:80]
    return request.remote_addr[:80] if request.remote_addr else None


def _request_user_agent() -> str | None:
    if not has_request_context():
        return None
    user_agent = request.headers.get("User-Agent")
    return user_agent[:255] if user_agent else None


def _generate_signature_code(now: datetime) -> str:
    return f"SIG-{now:%Y%m%d%H%M%S}-{uuid4().hex[:6].upper()}"


def _current_active_user(*, required: bool) -> UserModel | None:
    user = current_user._get_current_object()
    if getattr(user, "id_usuario", None) is not None and not getattr(
        user, "is_active", False
    ):
        raise ValueError(
            "Usuário inativo, bloqueado ou removido não pode assinar ações críticas."
        )

    if not getattr(user, "is_authenticated", False):
        if required:
            raise ValueError(
                "Usuário autenticado é obrigatório para assinar ações críticas."
            )
        return None

    if not getattr(user, "is_active", False):
        raise ValueError(
            "Usuário inativo, bloqueado ou removido não pode assinar ações críticas."
        )
    return user


def signature_snapshot(signature: InternalSignatureModel) -> dict[str, Any]:
    return {
        "id_signature": signature.id_signature,
        "codigo": signature.codigo,
        "acao": signature.acao,
        "entidade": signature.entidade,
        "entidade_id": signature.entidade_id,
        "resultado": signature.resultado,
        "metodo": signature.metodo,
        "usuario_email": signature.usuario_email,
        "signed_at": signature.signed_at,
        "ip": signature.ip,
        "correlation_id": signature.correlation_id,
    }


def record_internal_signature(
    *,
    action: str,
    entity: str,
    entity_id: int | str,
    result: str = SignatureResult.CONFIRMADO.value,
    method: str = SignatureMethod.SESSAO_AUTENTICADA.value,
    reason: str | None = None,
    context: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    inventory_id: int | None = None,
    transfer_id: int | None = None,
    occurrence_id: int | None = None,
    inventory_divergence_id: int | None = None,
    require_authenticated: bool = False,
) -> InternalSignatureModel | None:
    """Record an internal signature/evidence entry for a critical operation.

    In route/UI flows, a logged active user is expected and the signature is persisted.
    In low-level service tests or maintenance scripts without a logged user, callers can keep
    require_authenticated=False to avoid fabricating a signature.
    """
    user = _current_active_user(required=require_authenticated)
    if user is None:
        return None

    now = utc_now()
    signature = InternalSignatureModel(
        codigo=_generate_signature_code(now),
        acao=action,
        entidade=entity,
        entidade_id=str(entity_id),
        resultado=result,
        metodo=method,
        motivo=(reason or "").strip() or None,
        contexto_json=_json_dumps(context),
        correlation_id=correlation_id or str(uuid4()),
        id_usuario=user.id_usuario,
        usuario_email=user.email_lower,
        usuario_nome=user.nome,
        signed_at=now,
        ip=_request_ip(),
        user_agent=_request_user_agent(),
        id_inventory=inventory_id,
        id_transfer=transfer_id,
        id_occurrence=occurrence_id,
        id_inventory_divergence=inventory_divergence_id,
    )
    db.session.add(signature)
    db.session.flush()
    record_audit_log(
        action="signatures.create",
        entity="internal_signature",
        entity_id=signature.id_signature,
        after=signature_snapshot(signature),
        reason=reason,
    )
    return signature
