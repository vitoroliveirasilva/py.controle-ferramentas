from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db
from app.permissions.services import seed_permissions_and_roles


@pytest.fixture()
def app():
    app = create_app(
        "testing",
        {
            "SECRET_KEY": "test-secret",
            "BOOTSTRAP_CSS_URL": "https://example.test/bootstrap.css",
            "BOOTSTRAP_JS_URL": "https://example.test/bootstrap.js",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
            "AUTH_DEV_LOGIN_ENABLED": True,
            "AUTH_ALLOWED_EMAIL_DOMAINS": [],
        },
    )

    with app.app_context():
        db.create_all()
        seed_permissions_and_roles()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
