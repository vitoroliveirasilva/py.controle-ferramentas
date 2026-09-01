from __future__ import annotations

from typing import Any

from sqlalchemy import Select, false, or_, select, true

from app.categories.models import ToolCategoryModel
from app.extensions import db
from app.permissions.scope_filters import apply_tool_scope, is_global_scope
from app.tools.models import ToolModel


def normalize_code(value: str) -> str:
    return value.strip().lower()


def get_category_by_id(category_id: int) -> ToolCategoryModel | None:
    return db.session.get(ToolCategoryModel, category_id)


def get_category_by_code(code: str) -> ToolCategoryModel | None:
    return db.session.execute(
        select(ToolCategoryModel).where(
            ToolCategoryModel.codigo == normalize_code(code)
        )
    ).scalar_one_or_none()


def base_category_query(search: str | None = None, status: str | None = None) -> Select:
    stmt = select(ToolCategoryModel).where(ToolCategoryModel.is_deleted == false())
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                ToolCategoryModel.nome.ilike(like), ToolCategoryModel.codigo.ilike(like)
            )
        )
    if status == "ativo":
        stmt = stmt.where(ToolCategoryModel.ativo == true())
    elif status == "inativo":
        stmt = stmt.where(ToolCategoryModel.ativo == false())
    return stmt.order_by(ToolCategoryModel.nome)


def list_active_categories() -> list[ToolCategoryModel]:
    return (
        db.session.execute(
            select(ToolCategoryModel)
            .where(
                ToolCategoryModel.ativo == true(),
                ToolCategoryModel.is_deleted == false(),
            )
            .order_by(ToolCategoryModel.nome)
        )
        .scalars()
        .all()
    )


# Lista categorias ativas visíveis no filtro de ferramentas


# Os itens refletem ao escopo do usuário
# Ou seja, categorias sem ferramentas acessíveis pelo ABAC não são listadas para usuários escopados
def list_active_categories_for_tool_scope(
    user: Any | None = None,
) -> list[ToolCategoryModel]:
    stmt = select(ToolCategoryModel).where(
        ToolCategoryModel.ativo == true(),
        ToolCategoryModel.is_deleted == false(),
    )

    if user is not None and not is_global_scope(user):
        scoped_category_ids = (
            select(ToolModel.id_categoria)
            .distinct()
            .where(
                ToolModel.is_deleted == false(),
            )
        )
        scoped_category_ids = apply_tool_scope(
            scoped_category_ids, user, ToolModel.id_tool
        )
        stmt = stmt.where(ToolCategoryModel.id_categoria.in_(scoped_category_ids))

    return db.session.execute(stmt.order_by(ToolCategoryModel.nome)).scalars().all()
