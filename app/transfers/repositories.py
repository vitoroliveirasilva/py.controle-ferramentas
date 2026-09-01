from __future__ import annotations

from sqlalchemy import Select, false, or_, select

from app.extensions import db
from app.permissions.scope_filters import apply_transfer_scope
from app.tools.models import ToolModel
from app.transfers.models import TransferItemModel, TransferModel
from app.users.models import UserModel


def get_transfer_by_id(transfer_id: int) -> TransferModel | None:
    return db.session.get(TransferModel, transfer_id)


def get_transfer_by_codigo(codigo: str) -> TransferModel | None:
    return db.session.execute(
        select(TransferModel).where(TransferModel.codigo == codigo.strip().upper())
    ).scalar_one_or_none()


def base_transfer_query(
    search: str | None = None,
    status: str | None = None,
    *,
    user: UserModel | None = None,
) -> Select:
    stmt = select(TransferModel).where(TransferModel.is_deleted == false())
    if user is not None:
        stmt = apply_transfer_scope(stmt, user, TransferModel.id_transfer)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                TransferModel.codigo.ilike(like),
                TransferModel.destino_responsavel_snapshot.ilike(like),
                TransferModel.destino_local_snapshot.ilike(like),
                TransferModel.motivo.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(TransferModel.status == status)
    return stmt.order_by(
        TransferModel.solicitado_em.desc(), TransferModel.id_transfer.desc()
    )


def list_transfer_items(transfer_id: int) -> list[TransferItemModel]:
    return (
        db.session.execute(
            select(TransferItemModel)
            .join(ToolModel, ToolModel.id_tool == TransferItemModel.id_tool)
            .where(
                TransferItemModel.id_transfer == transfer_id,
                TransferItemModel.is_deleted == false(),
            )
            .order_by(ToolModel.codigo_interno)
        )
        .scalars()
        .all()
    )
