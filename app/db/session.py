from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.extensions import db


@contextmanager
def transactional_session() -> Iterator[Session]:
    try:
        yield db.session
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
