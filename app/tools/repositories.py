from __future__ import annotations

from sqlalchemy import Select, false, or_, select

from app.extensions import db
from app.permissions.scope_filters import apply_tool_scope
from app.tools.models import ToolModel
from app.users.models import UserModel


def normalize_code(value: str) -> str:
    return value.strip().upper()


def normalize_optional_code(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned.upper() if cleaned else None


def get_tool_by_id(tool_id: int) -> ToolModel | None:
    return db.session.get(ToolModel, tool_id)


def get_tool_by_codigo_interno(code: str) -> ToolModel | None:
    return db.session.execute(
        select(ToolModel).where(ToolModel.codigo_interno == normalize_code(code))
    ).scalar_one_or_none()


def get_tool_by_ativo_imobilizado(value: str | None) -> ToolModel | None:
    normalized = normalize_optional_code(value)
    if not normalized:
        return None
    return db.session.execute(
        select(ToolModel).where(ToolModel.ativo_imobilizado == normalized)
    ).scalar_one_or_none()


def get_tool_by_numero_serie(value: str | None) -> ToolModel | None:
    normalized = normalize_optional_code(value)
    if not normalized:
        return None
    return db.session.execute(
        select(ToolModel).where(ToolModel.numero_serie == normalized)
    ).scalar_one_or_none()


def base_tool_query(
    search: str | None = None,
    status: str | None = None,
    category_id: int | None = None,
    *,
    user: UserModel | None = None,
) -> Select:
    stmt = select(ToolModel).where(ToolModel.is_deleted == false())
    if user is not None:
        stmt = apply_tool_scope(stmt, user, ToolModel.id_tool)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                ToolModel.nome.ilike(like),
                ToolModel.codigo_interno.ilike(like),
                ToolModel.ativo_imobilizado.ilike(like),
                ToolModel.numero_serie.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(ToolModel.status == status)
    if category_id:
        stmt = stmt.where(ToolModel.id_categoria == category_id)
    return stmt.order_by(ToolModel.codigo_interno)


# Busca uma ferramenta por código interno, número de ativo ou número de série
def get_tool_by_any_identifier(
    value: str | None,
    *,
    user: UserModel | None = None,
) -> ToolModel | None:
    normalized = normalize_optional_code(value)
    if not normalized:
        return None
    stmt = select(ToolModel).where(
        ToolModel.is_deleted == false(),
        or_(
            ToolModel.codigo_interno == normalized,
            ToolModel.ativo_imobilizado == normalized,
            ToolModel.numero_serie == normalized,
        ),
    )
    if user is not None:
        stmt = apply_tool_scope(stmt, user, ToolModel.id_tool)
    return db.session.execute(stmt).scalar_one_or_none()
