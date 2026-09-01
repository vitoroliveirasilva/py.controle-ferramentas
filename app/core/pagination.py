from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select

from app.extensions import db


@dataclass(frozen=True)
class Page:
    items: list[Any]
    page: int
    per_page: int
    total: int

    @property
    def pages(self) -> int:
        if self.per_page <= 0:
            return 1
        return max(1, (self.total + self.per_page - 1) // self.per_page)

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def prev_num(self) -> int:
        return max(1, self.page - 1)

    @property
    def next_num(self) -> int:
        return min(self.pages, self.page + 1)


def clamp_page(value: int | str | None) -> int:
    try:
        page = int(value or 1)
    except (TypeError, ValueError):
        return 1
    return max(1, page)


def clamp_per_page(
    value: int | str | None, default: int = 15, maximum: int = 100
) -> int:
    try:
        per_page = int(value or default)
    except (TypeError, ValueError):
        return default
    return min(max(1, per_page), maximum)


def paginate(statement: Select, *, page: int = 1, per_page: int = 15) -> Page:
    page = clamp_page(page)
    per_page = clamp_per_page(per_page)
    count_stmt = select(func.count()).select_from(statement.order_by(None).subquery())
    total = int(db.session.execute(count_stmt).scalar_one() or 0)
    items = (
        db.session.execute(statement.limit(per_page).offset((page - 1) * per_page))
        .scalars()
        .all()
    )
    return Page(items=items, page=page, per_page=per_page, total=total)
