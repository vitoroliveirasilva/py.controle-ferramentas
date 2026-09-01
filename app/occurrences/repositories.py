from __future__ import annotations

from sqlalchemy import Select, false, or_, select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.occurrences.models import OccurrenceAttachmentModel, OccurrenceModel
from app.permissions.scope_filters import apply_occurrence_scope
from app.tools.models import ToolModel
from app.users.models import UserModel


def get_occurrence_by_id(occurrence_id: int) -> OccurrenceModel | None:
    return (
        db.session.execute(
            select(OccurrenceModel)
            .options(
                joinedload(OccurrenceModel.tool), joinedload(OccurrenceModel.anexos)
            )
            .where(OccurrenceModel.id_occurrence == occurrence_id)
        )
        .unique()
        .scalar_one_or_none()
    )


def get_occurrence_by_code(code: str) -> OccurrenceModel | None:
    return db.session.execute(
        select(OccurrenceModel).where(OccurrenceModel.codigo == code.strip().upper())
    ).scalar_one_or_none()


def base_occurrence_query(
    search: str | None = None,
    status: str | None = None,
    *,
    user: UserModel | None = None,
) -> Select:
    stmt = (
        select(OccurrenceModel)
        .options(joinedload(OccurrenceModel.tool))
        .join(ToolModel, ToolModel.id_tool == OccurrenceModel.id_tool)
        .where(OccurrenceModel.is_deleted == false())
    )
    if user is not None:
        stmt = apply_occurrence_scope(stmt, user)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                OccurrenceModel.codigo.ilike(like),
                OccurrenceModel.motivo.ilike(like),
                OccurrenceModel.descricao.ilike(like),
                ToolModel.codigo_interno.ilike(like),
                ToolModel.nome.ilike(like),
                ToolModel.ativo_imobilizado.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(OccurrenceModel.status == status)
    return stmt.order_by(
        OccurrenceModel.created_at.desc(), OccurrenceModel.id_occurrence.desc()
    )


def list_occurrence_attachments(occurrence_id: int) -> list[OccurrenceAttachmentModel]:
    return list(
        db.session.execute(
            select(OccurrenceAttachmentModel)
            .where(
                OccurrenceAttachmentModel.id_occurrence == occurrence_id,
                OccurrenceAttachmentModel.is_deleted == false(),
            )
            .order_by(OccurrenceAttachmentModel.uploaded_at.desc())
        ).scalars()
    )


def get_occurrence_attachment_by_id(attachment_id: int) -> OccurrenceAttachmentModel | None:
    return db.session.execute(
        select(OccurrenceAttachmentModel)
        .options(joinedload(OccurrenceAttachmentModel.occurrence).joinedload(OccurrenceModel.tool))
        .where(
            OccurrenceAttachmentModel.id_attachment == attachment_id,
            OccurrenceAttachmentModel.is_deleted == false(),
        )
    ).unique().scalar_one_or_none()
