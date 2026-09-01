from __future__ import annotations

from sqlalchemy import Select, false, or_, select, true

from app.custody.models import ToolCustodyModel, ToolTimelineEventModel
from app.extensions import db
from app.locations.models import LocationModel
from app.permissions.scope_filters import apply_tool_scope, is_global_scope
from app.tools.models import ToolModel
from app.users.models import UserModel


def get_current_custody(tool_id: int) -> ToolCustodyModel | None:
    return db.session.execute(
        select(ToolCustodyModel).where(
            ToolCustodyModel.id_tool == tool_id,
            ToolCustodyModel.atual == true(),
            ToolCustodyModel.is_deleted == false(),
        )
    ).scalar_one_or_none()


def list_custody_history(tool_id: int) -> list[ToolCustodyModel]:
    return (
        db.session.execute(
            select(ToolCustodyModel)
            .where(
                ToolCustodyModel.id_tool == tool_id,
                ToolCustodyModel.is_deleted == false(),
            )
            .order_by(ToolCustodyModel.inicio_em.desc())
        )
        .scalars()
        .all()
    )


def list_timeline_events(tool_id: int) -> list[ToolTimelineEventModel]:
    return (
        db.session.execute(
            select(ToolTimelineEventModel)
            .where(ToolTimelineEventModel.id_tool == tool_id)
            .order_by(ToolTimelineEventModel.occurred_at.desc())
        )
        .scalars()
        .all()
    )


def base_current_custody_query(
    search: str | None = None,
    custody_type: str | None = None,
    *,
    user: UserModel | None = None,
) -> Select:
    stmt = (
        select(ToolCustodyModel)
        .join(ToolModel, ToolModel.id_tool == ToolCustodyModel.id_tool)
        .outerjoin(
            UserModel, UserModel.id_usuario == ToolCustodyModel.id_responsavel_usuario
        )
        .outerjoin(
            LocationModel, LocationModel.id_location == ToolCustodyModel.id_location
        )
        .where(
            ToolCustodyModel.atual == true(),
            ToolCustodyModel.is_deleted == false(),
            ToolModel.is_deleted == false(),
        )
    )
    if user is not None:
        stmt = apply_tool_scope(stmt, user, ToolCustodyModel.id_tool)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                ToolModel.codigo_interno.ilike(like),
                ToolModel.nome.ilike(like),
                ToolModel.ativo_imobilizado.ilike(like),
                ToolCustodyModel.responsavel_snapshot.ilike(like),
                ToolCustodyModel.local_snapshot.ilike(like),
                UserModel.email_lower.ilike(like),
                LocationModel.codigo.ilike(like),
                LocationModel.nome.ilike(like),
            )
        )
    if custody_type:
        stmt = stmt.where(ToolCustodyModel.tipo_custodia == custody_type)
    return stmt.order_by(ToolModel.codigo_interno)


def active_tools_without_custody_query(*, user: UserModel | None = None) -> Select:
    current_subquery = (
        select(ToolCustodyModel.id_tool)
        .where(
            ToolCustodyModel.atual == true(),
            ToolCustodyModel.is_deleted == false(),
        )
        .subquery()
    )
    stmt = (
        select(ToolModel)
        .outerjoin(current_subquery, current_subquery.c.id_tool == ToolModel.id_tool)
        .where(
            ToolModel.is_deleted == false(),
            ToolModel.ativo == true(),
            ToolModel.status.notin_(("baixada", "inativa")),
            current_subquery.c.id_tool.is_(None),
        )
        .order_by(ToolModel.codigo_interno)
    )
    if user is not None and not is_global_scope(user):
        # Ferramenta sem custódia não possui filial/local/técnico seguro para ABAC
        # Não-global não pode listar pendências sem dono sem permissão global explícita
        stmt = stmt.where(false())
    return stmt
