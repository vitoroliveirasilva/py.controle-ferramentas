from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from flask import Flask, current_app, jsonify, redirect, request, url_for
from flask_login import login_user
from sqlalchemy import false, true

from app.audit.services import record_audit_log
from app.auth.exceptions import AuthAccessDeniedError
from app.extensions import db, login_manager
from app.users.models import UserModel
from app.users.repositories import (
    get_user_by_email,
    get_user_by_microsoft_oid,
)


def _wants_json_response() -> bool:
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return (
        best == "application/json"
        and request.accept_mimetypes[best] > request.accept_mimetypes["text/html"]
    )


# Função de carregamento de usuário para o Flask-Login, com verificação de status ativo
def load_active_user_for_session(user_id: int) -> UserModel | None:
    stmt = (
        db.select(UserModel)
        .where(
            UserModel.id_usuario == user_id,
            UserModel.ativo == true(),
            UserModel.bloqueado == false(),
            UserModel.is_deleted == false(),
        )
        .execution_options(populate_existing=True)
    )
    return db.session.execute(stmt).scalar_one_or_none()


def configure_login_manager(app: Flask) -> None:
    login_manager.login_view = "auth.login"
    login_manager.login_message = (
        "Faça login com sua conta Microsoft corporativa para continuar."
    )
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id: str) -> UserModel | None:
        if not user_id.isdigit():
            return None
        return load_active_user_for_session(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        if _wants_json_response():
            return (
                jsonify(
                    {"error": {"code": 401, "message": "Autenticação necessária."}}
                ),
                401,
            )
        return redirect(url_for("auth.login", next=request.full_path or request.path))


def normalize_claim_email(claims: dict[str, Any]) -> str | None:
    email = claims.get("preferred_username") or claims.get("email") or claims.get("upn")
    return email.strip().lower() if isinstance(email, str) and email.strip() else None


def validate_allowed_domain(email: str) -> None:
    allowed_domains = current_app.config.get("AUTH_ALLOWED_EMAIL_DOMAINS", [])
    if not allowed_domains:
        return

    domain = email.rsplit("@", maxsplit=1)[-1].lower()
    if domain not in allowed_domains:
        raise AuthAccessDeniedError(
            "Seu domínio de e-mail não está autorizado neste sistema."
        )


def _claims_audit_summary(claims: dict[str, Any]) -> dict[str, Any]:
    return {
        "email": normalize_claim_email(claims),
        "has_oid": bool(claims.get("oid") or claims.get("sub")),
        "name": claims.get("name"),
    }


def record_login_failure(claims: dict[str, Any] | None, reason: str) -> None:
    record_audit_log(
        action="auth.login_failure",
        entity="auth",
        entity_id=normalize_claim_email(claims or {}) or "unknown",
        after={"claims": _claims_audit_summary(claims or {})},
        reason=reason,
        result="failure",
        commit=True,
    )


def record_login_success(user: UserModel, claims: dict[str, Any]) -> None:
    record_audit_log(
        action="auth.login_success",
        entity="user",
        entity_id=user.id_usuario,
        after={"email": user.email_lower, "claims": _claims_audit_summary(claims)},
        reason="Login Microsoft/dev autorizado pelo cadastro.",
        result="success",
        commit=True,
    )


def resolve_authorized_user_from_claims(claims: dict[str, Any]) -> UserModel:
    microsoft_oid = claims.get("oid") or claims.get("sub")
    email = normalize_claim_email(claims)

    if not microsoft_oid:
        raise AuthAccessDeniedError(
            "A Microsoft não retornou o identificador OID do usuário."
        )
    if not email:
        raise AuthAccessDeniedError(
            "A Microsoft não retornou um e-mail identificável para o usuário."
        )

    validate_allowed_domain(email)

    user = get_user_by_microsoft_oid(str(microsoft_oid))
    if not user:
        user = get_user_by_email(email)

    if not user:
        raise AuthAccessDeniedError(
            "Usuário autenticado na Microsoft, mas não cadastrado."
        )

    if user.microsoft_oid and user.microsoft_oid != str(microsoft_oid):
        raise AuthAccessDeniedError(
            "O e-mail está vinculado a outro identificador Microsoft. Acione o suporte."
        )

    if not user.microsoft_oid:
        user.microsoft_oid = str(microsoft_oid)

    if user.email_lower != email:
        raise AuthAccessDeniedError(
            "E-mail autenticado não corresponde ao cadastro."
        )

    if not user.ativo:
        raise AuthAccessDeniedError(
            "Usuário inativo. Acione o administrador do sistema."
        )

    if user.bloqueado:
        reason = f" Motivo: {user.bloqueio_motivo}." if user.bloqueio_motivo else ""
        raise AuthAccessDeniedError(f"Usuário bloqueado.{reason}")

    if user.is_deleted:
        raise AuthAccessDeniedError(
            "Usuário removido logicamente. Acione o administrador."
        )

    return user


def login_authorized_user_from_claims(claims: dict[str, Any]) -> UserModel:
    user = resolve_authorized_user_from_claims(claims)
    user.ultimo_login_em = datetime.now(UTC)
    db.session.commit()
    login_user(user)
    record_login_success(user, claims)
    current_app.logger.info("Usuário autenticado com sucesso: %s", user.email_lower)
    return user
