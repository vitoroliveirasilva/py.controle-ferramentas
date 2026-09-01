from __future__ import annotations

from sqlalchemy import false, true

from app.extensions import db
from app.users.models import UserModel


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_id(user_id: int) -> UserModel | None:
    return db.session.get(UserModel, user_id)


def get_user_by_email(email: str) -> UserModel | None:
    email_lower = normalize_email(email)
    return db.session.execute(
        db.select(UserModel).where(UserModel.email_lower == email_lower)
    ).scalar_one_or_none()


def get_user_by_microsoft_oid(microsoft_oid: str) -> UserModel | None:
    return db.session.execute(
        db.select(UserModel).where(UserModel.microsoft_oid == microsoft_oid)
    ).scalar_one_or_none()


def create_user(
    *,
    email: str,
    nome: str,
    microsoft_oid: str | None = None,
    ativo: bool = True,
    bloqueado: bool = False,
    observacoes: str | None = None,
) -> UserModel:
    user = UserModel(
        email=email.strip(),
        email_lower=normalize_email(email),
        nome=nome.strip(),
        microsoft_oid=microsoft_oid.strip() if microsoft_oid else None,
        ativo=ativo,
        bloqueado=bloqueado,
        observacoes=observacoes,
    )
    db.session.add(user)
    return user


def base_user_query(search: str | None = None, status: str | None = None):
    from sqlalchemy import or_

    stmt = db.select(UserModel).where(UserModel.is_deleted == false())
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                UserModel.email_lower.ilike(like),
                UserModel.nome.ilike(like),
                UserModel.microsoft_oid.ilike(like),
            )
        )
    if status == "ativo":
        stmt = stmt.where(UserModel.ativo == true(), UserModel.bloqueado == false())
    elif status == "inativo":
        stmt = stmt.where(UserModel.ativo == false())
    elif status == "bloqueado":
        stmt = stmt.where(UserModel.bloqueado == true())
    return stmt.order_by(UserModel.nome, UserModel.email_lower)


def list_active_users() -> list[UserModel]:
    return (
        db.session.execute(
            db.select(UserModel)
            .where(
                UserModel.ativo == true(),
                UserModel.bloqueado == false(),
                UserModel.is_deleted == false(),
            )
            .order_by(UserModel.nome, UserModel.email_lower)
        )
        .scalars()
        .all()
    )
