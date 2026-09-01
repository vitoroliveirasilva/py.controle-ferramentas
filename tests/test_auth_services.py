from __future__ import annotations

import pytest

from app.auth.exceptions import AuthAccessDeniedError
from app.auth.services import resolve_authorized_user_from_claims
from app.extensions import db
from app.users.repositories import create_user


def test_resolve_authorized_user_binds_microsoft_oid(app):
    with app.app_context():
        user = create_user(email="vitor@brasif.com.br", nome="Vitor")
        db.session.commit()

        resolved = resolve_authorized_user_from_claims(
            {"oid": "oid-123", "preferred_username": "vitor@brasif.com.br"}
        )

        assert resolved.id_usuario == user.id_usuario
        assert resolved.microsoft_oid == "oid-123"


def test_resolve_authorized_user_rejects_missing_local_user(app):
    with app.app_context(), pytest.raises(AuthAccessDeniedError):
        resolve_authorized_user_from_claims(
            {"oid": "oid-404", "preferred_username": "unknown@brasif.com.br"}
        )


def test_resolve_authorized_user_rejects_blocked_user(app):
    with app.app_context():
        create_user(email="blocked@brasif.com.br", nome="Blocked", bloqueado=True)
        db.session.commit()

        with pytest.raises(AuthAccessDeniedError):
            resolve_authorized_user_from_claims(
                {"oid": "oid-blocked", "preferred_username": "blocked@brasif.com.br"}
            )
