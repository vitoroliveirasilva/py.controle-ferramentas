from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def utc_now() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    # Campos de timestamp para registros com data de criação e atualização

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class SoftDeleteMixin:
    # Campos de exclusão suave para registros que não devem ser removidos fisicamente

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def mark_deleted(self) -> None:
        self.is_deleted = True
        self.deleted_at = utc_now()

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None


class BaseModel(db.Model):
    # Modelo abstrato com funções auxiliares compartilhadas por entidades mapeadas

    __abstract__ = True

    def to_dict(self, exclude: set[str] | None = None) -> dict[str, Any]:
        excluded = exclude or set()
        result = {}
        for column in self.__table__.columns:
            if column.name in excluded:
                continue
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
