from __future__ import annotations

from sqlalchemy import Select, false, or_, select, true

from app.extensions import db
from app.models.enums import NotificationStatus
from app.notifications.models import NotificationDeliveryModel, NotificationModel
from app.permissions.models import (
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    UserRoleModel,
)
from app.users.models import UserModel


def get_notification_by_id(notification_id: int) -> NotificationModel | None:
    return db.session.get(NotificationModel, notification_id)


def get_notification_by_dedupe_key(dedupe_key: str | None) -> NotificationModel | None:
    if not dedupe_key:
        return None
    return db.session.execute(
        select(NotificationModel).where(
            NotificationModel.dedupe_key == dedupe_key,
            NotificationModel.is_deleted == false(),
        )
    ).scalar_one_or_none()


def base_notification_query(
    search: str | None = None,
    status: str | None = None,
    only_user_id: int | None = None,
) -> Select:
    stmt = select(NotificationModel).where(NotificationModel.is_deleted == false())
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                NotificationModel.codigo.ilike(like),
                NotificationModel.titulo.ilike(like),
                NotificationModel.mensagem.ilike(like),
                NotificationModel.entidade.ilike(like),
            )
        )
    if status:
        stmt = stmt.where(NotificationModel.status == status)
    if only_user_id is not None:
        stmt = stmt.where(NotificationModel.id_usuario_destino == only_user_id)
    return stmt.order_by(
        NotificationModel.created_at.desc(),
        NotificationModel.id_notification.desc(),
    )


def count_unread_notifications(user_id: int) -> int:
    stmt = select(NotificationModel).where(
        NotificationModel.id_usuario_destino == user_id,
        NotificationModel.status == NotificationStatus.PENDENTE.value,
        NotificationModel.is_deleted == false(),
    )
    return len(db.session.execute(stmt).scalars().all())


def list_users_with_permission(permission_code: str) -> list[UserModel]:
    rows = db.session.execute(
        select(UserModel)
        .join(UserRoleModel, UserRoleModel.id_usuario == UserModel.id_usuario)
        .join(RoleModel, RoleModel.id_role == UserRoleModel.id_role)
        .join(RolePermissionModel, RolePermissionModel.id_role == RoleModel.id_role)
        .join(
            PermissionModel,
            PermissionModel.id_permission == RolePermissionModel.id_permission,
        )
        .where(
            PermissionModel.codigo == permission_code,
            PermissionModel.ativo == true(),
            PermissionModel.is_deleted == false(),
            RoleModel.ativo == true(),
            RoleModel.is_deleted == false(),
            UserRoleModel.ativo == true(),
            UserModel.ativo == true(),
            UserModel.bloqueado == false(),
            UserModel.is_deleted == false(),
        )
        .distinct()
        .order_by(UserModel.nome)
    ).scalars()
    return list(rows.all())


def list_pending_email_notifications(limit: int = 50) -> list[NotificationModel]:
    return list(
        db.session.execute(
            select(NotificationModel)
            .where(
                NotificationModel.status == NotificationStatus.PENDENTE.value,
                NotificationModel.destinatario_email.is_not(None),
                NotificationModel.enviada_em.is_(None),
                NotificationModel.is_deleted == false(),
            )
            .order_by(NotificationModel.created_at)
            .limit(limit)
        )
        .scalars()
        .all()
    )


def add_delivery(delivery: NotificationDeliveryModel) -> NotificationDeliveryModel:
    db.session.add(delivery)
    return delivery
