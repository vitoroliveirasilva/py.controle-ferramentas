from __future__ import annotations

import pytest
from flask_login import login_user

from app.extensions import db
from app.signatures.services import record_internal_signature
from app.users.repositories import create_user


def test_record_internal_signature_requires_active_user(app):
    with app.app_context():
        user = create_user(email="signer@brasif.com.br", nome="Signer User")
        db.session.commit()

        with app.test_request_context(
            "/admin/fake", headers={"User-Agent": "pytest-agent"}
        ):
            login_user(user)
            signature = record_internal_signature(
                action="test.sign",
                entity="test_entity",
                entity_id=123,
                result="confirmado",
                reason="Assinatura de teste",
                context={"ok": True},
                require_authenticated=True,
            )
            db.session.commit()

        assert signature is not None
        assert signature.id_signature is not None
        assert signature.usuario_email == "signer@brasif.com.br"
        assert signature.user_agent == "pytest-agent"
        assert signature.contexto_json is not None


def test_blocked_user_cannot_sign(app):
    with app.app_context():
        user = create_user(email="blocked-signer@brasif.com.br", nome="Blocked Signer")
        db.session.commit()

        with app.test_request_context("/admin/fake"):
            login_user(user)
            user.bloqueado = True
            db.session.flush()
            with pytest.raises(ValueError, match="não pode assinar"):
                record_internal_signature(
                    action="test.sign",
                    entity="test_entity",
                    entity_id=123,
                    reason="Tentativa bloqueada",
                    require_authenticated=True,
                )
