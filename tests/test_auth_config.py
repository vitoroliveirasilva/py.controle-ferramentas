from __future__ import annotations

import pytest
from flask import url_for

from app import create_app
from app.auth.msal_client import MicrosoftAuthClient


def test_canonical_microsoft_callback_endpoint_exists(app):
    with app.test_request_context():
        assert url_for("auth.callback") == "/auth/callback"


def test_msal_redirect_uri_uses_canonical_callback_when_uri_not_configured(app):
    app.config["AUTH_MICROSOFT_REDIRECT_URI"] = ""
    app.config["AUTH_MICROSOFT_REDIRECT_PATH"] = "/auth/callback"

    with app.test_request_context(base_url="http://localhost:5000"):
        assert (
            MicrosoftAuthClient().redirect_uri()
            == "http://localhost:5000/auth/callback"
        )


def test_custom_microsoft_callback_path_registers_legacy_alias():
    app = create_app(
        "testing",
        {
            "AUTH_MICROSOFT_REDIRECT_URI": "http://localhost:5000/getAToken",
            "AUTH_MICROSOFT_REDIRECT_PATH": "/getAToken",
        },
    )

    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/auth/callback" in rules
    assert "/getAToken" in rules


def test_runtime_config_rejects_mismatched_microsoft_redirect_path():
    with pytest.raises(RuntimeError, match="mesmo caminho de callback"):
        create_app(
            "testing",
            {
                "AUTH_MICROSOFT_REDIRECT_URI": "http://localhost:5000/getAToken",
                "AUTH_MICROSOFT_REDIRECT_PATH": "/auth/callback",
            },
        )


def test_runtime_config_rejects_partial_microsoft_configuration():
    with pytest.raises(RuntimeError, match="Configuração Microsoft incompleta"):
        create_app(
            "testing",
            {
                "AUTH_MICROSOFT_TENANT_ID": "tenant-only",
                "AUTH_MICROSOFT_CLIENT_ID": "",
                "AUTH_MICROSOFT_CLIENT_SECRET": "",
            },
        )


def test_runtime_config_requires_gateway_key_when_email_is_enabled():
    with pytest.raises(RuntimeError, match="BRASIF_GATEWAY_API_KEY"):
        create_app(
            "testing",
            {
                "NOTIFICATIONS_EMAIL_ENABLED": True,
                "BRASIF_GATEWAY_API_KEY": "",
            },
        )
