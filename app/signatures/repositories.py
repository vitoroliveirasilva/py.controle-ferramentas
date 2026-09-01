from __future__ import annotations

from sqlalchemy import Select, desc, or_, select

from app.extensions import db
from app.signatures.models import InternalSignatureModel


def get_signature_by_id(signature_id: int) -> InternalSignatureModel | None:
    return db.session.get(InternalSignatureModel, signature_id)


def base_signature_query(
    search: str | None = None,
    action: str | None = None,
    result: str | None = None,
) -> Select:
    stmt = select(InternalSignatureModel)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                InternalSignatureModel.codigo.ilike(like),
                InternalSignatureModel.usuario_email.ilike(like),
                InternalSignatureModel.entidade.ilike(like),
                InternalSignatureModel.entidade_id.ilike(like),
            )
        )
    if action:
        stmt = stmt.where(InternalSignatureModel.acao == action)
    if result:
        stmt = stmt.where(InternalSignatureModel.resultado == result)
    return stmt.order_by(
        desc(InternalSignatureModel.signed_at),
        desc(InternalSignatureModel.id_signature),
    )


def list_entity_signatures(
    entity: str, entity_id: int | str
) -> list[InternalSignatureModel]:
    stmt = (
        select(InternalSignatureModel)
        .where(
            InternalSignatureModel.entidade == entity,
            InternalSignatureModel.entidade_id == str(entity_id),
        )
        .order_by(
            desc(InternalSignatureModel.signed_at),
            desc(InternalSignatureModel.id_signature),
        )
    )
    return list(db.session.execute(stmt).scalars())


def list_inventory_signatures(inventory_id: int) -> list[InternalSignatureModel]:
    stmt = (
        select(InternalSignatureModel)
        .where(InternalSignatureModel.id_inventory == inventory_id)
        .order_by(
            desc(InternalSignatureModel.signed_at),
            desc(InternalSignatureModel.id_signature),
        )
    )
    return list(db.session.execute(stmt).scalars())


def list_transfer_signatures(transfer_id: int) -> list[InternalSignatureModel]:
    stmt = (
        select(InternalSignatureModel)
        .where(InternalSignatureModel.id_transfer == transfer_id)
        .order_by(
            desc(InternalSignatureModel.signed_at),
            desc(InternalSignatureModel.id_signature),
        )
    )
    return list(db.session.execute(stmt).scalars())


def list_occurrence_signatures(occurrence_id: int) -> list[InternalSignatureModel]:
    stmt = (
        select(InternalSignatureModel)
        .where(InternalSignatureModel.id_occurrence == occurrence_id)
        .order_by(
            desc(InternalSignatureModel.signed_at),
            desc(InternalSignatureModel.id_signature),
        )
    )
    return list(db.session.execute(stmt).scalars())
