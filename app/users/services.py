from __future__ import annotations

from app.extensions import db
from app.users.models import UserModel
from app.users.repositories import create_user, get_user_by_email, normalize_email


def create_local_user(
    *,
    email: str,
    nome: str,
    microsoft_oid: str | None = None,
    ativo: bool = True,
    bloqueado: bool = False,
    bloqueio_motivo: str | None = None,
    observacoes: str | None = None,
    motivo: str | None = None,
) -> UserModel:
    existing = get_user_by_email(email)
    if existing:
        raise ValueError(
            f"Já existe usuário local para o e-mail {normalize_email(email)}."
        )

    if bloqueado and not (bloqueio_motivo or "").strip():
        raise ValueError("Informe o motivo do bloqueio.")

    user = create_user(
        email=email,
        nome=nome,
        microsoft_oid=microsoft_oid,
        ativo=ativo,
        bloqueado=bloqueado,
        observacoes=observacoes,
    )
    user.bloqueio_motivo = (bloqueio_motivo or "").strip() or None

    from app.audit.services import record_audit_log

    db.session.flush()
    record_audit_log(
        action="users.create",
        entity="user",
        entity_id=user.id_usuario,
        after=user.to_dict(),
        reason=motivo or "Criação de usuário local.",
    )
    db.session.commit()
    return user


def set_user_status(
    *,
    email: str,
    ativo: bool | None = None,
    bloqueado: bool | None = None,
    bloqueio_motivo: str | None = None,
) -> UserModel:
    user = get_user_by_email(email)
    if not user:
        raise ValueError(f"Usuário {normalize_email(email)} não encontrado.")

    if ativo is not None:
        user.ativo = ativo
    if bloqueado is not None:
        user.bloqueado = bloqueado
        user.bloqueio_motivo = bloqueio_motivo if bloqueado else None

    db.session.commit()
    return user


def update_local_user(user: UserModel, data: dict) -> UserModel:
    from app.audit.services import record_audit_log

    email_lower = normalize_email(data["email"])
    existing = get_user_by_email(email_lower)
    if existing and existing.id_usuario != user.id_usuario:
        raise ValueError(f"Já existe usuário local para o e-mail {email_lower}.")

    if data.get("bloqueado") and not (data.get("bloqueio_motivo") or "").strip():
        raise ValueError("Informe o motivo do bloqueio.")

    before = user.to_dict()
    user.email = data["email"].strip()
    user.email_lower = email_lower
    user.nome = data["nome"].strip()
    user.microsoft_oid = (data.get("microsoft_oid") or "").strip() or None
    user.ativo = bool(data.get("ativo"))
    user.bloqueado = bool(data.get("bloqueado"))
    user.bloqueio_motivo = (data.get("bloqueio_motivo") or "").strip() or None
    user.observacoes = (data.get("observacoes") or "").strip() or None
    record_audit_log(
        action="users.update",
        entity="user",
        entity_id=user.id_usuario,
        before=before,
        after=user.to_dict(),
        reason=data.get("motivo"),
    )
    db.session.commit()
    return user


def change_user_operational_status(
    user: UserModel,
    *,
    ativo: bool | None = None,
    bloqueado: bool | None = None,
    motivo: str,
) -> UserModel:
    from app.audit.services import record_audit_log

    if not motivo.strip():
        raise ValueError("Informe o motivo da alteração de status.")
    before = user.to_dict()
    if ativo is not None:
        user.ativo = ativo
    if bloqueado is not None:
        user.bloqueado = bloqueado
        user.bloqueio_motivo = motivo if bloqueado else None
    record_audit_log(
        action="users.status_update",
        entity="user",
        entity_id=user.id_usuario,
        before=before,
        after=user.to_dict(),
        reason=motivo,
    )
    db.session.commit()
    return user
