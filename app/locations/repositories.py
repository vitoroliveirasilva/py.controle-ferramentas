from __future__ import annotations

from sqlalchemy import Select, false, or_, select, true

from app.extensions import db
from app.locations.models import LocationModel


def normalize_code(value: str) -> str:
    return value.strip().lower()


def get_location_by_id(location_id: int) -> LocationModel | None:
    return db.session.get(LocationModel, location_id)


def get_location_by_code(code: str) -> LocationModel | None:
    return db.session.execute(
        select(LocationModel).where(LocationModel.codigo == normalize_code(code))
    ).scalar_one_or_none()


def base_location_query(
    search: str | None = None,
    status: str | None = None,
    location_type: str | None = None,
) -> Select:
    stmt = select(LocationModel).where(LocationModel.is_deleted == false())
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                LocationModel.nome.ilike(like),
                LocationModel.codigo.ilike(like),
                LocationModel.filial.ilike(like),
                LocationModel.departamento.ilike(like),
            )
        )
    if status == "ativo":
        stmt = stmt.where(LocationModel.ativo == true())
    elif status == "inativo":
        stmt = stmt.where(LocationModel.ativo == false())
    if location_type:
        stmt = stmt.where(LocationModel.tipo_local == location_type)
    return stmt.order_by(LocationModel.nome)


def list_active_locations() -> list[LocationModel]:
    return (
        db.session.execute(
            select(LocationModel)
            .where(LocationModel.ativo == true(), LocationModel.is_deleted == false())
            .order_by(LocationModel.nome)
        )
        .scalars()
        .all()
    )
