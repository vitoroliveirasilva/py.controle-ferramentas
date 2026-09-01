from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urljoin

import msal
from flask import current_app, request, session, url_for

from app.auth.exceptions import AuthConfigurationError, AuthStateError
from app.auth.redirects import (
    DEFAULT_MICROSOFT_REDIRECT_PATH,
    normalize_microsoft_redirect_path,
)

AUTH_STATE_SESSION_KEY = "auth.microsoft.state"
AUTH_NEXT_SESSION_KEY = "auth.next_url"


# Wrapper pequeno em torno do MSAL para manter detalhes da Microsoft fora das rotas
class MicrosoftAuthClient:

    def __init__(self) -> None:
        self.client_id = current_app.config["AUTH_MICROSOFT_CLIENT_ID"]
        self.client_secret = current_app.config["AUTH_MICROSOFT_CLIENT_SECRET"]
        self.tenant_id = current_app.config["AUTH_MICROSOFT_TENANT_ID"]
        self.scopes = current_app.config["AUTH_MICROSOFT_SCOPES"]

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.tenant_id)

    @property
    def authority(self) -> str:
        if not self.tenant_id:
            raise AuthConfigurationError()
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    def redirect_uri(self) -> str:
        configured_uri = current_app.config.get("AUTH_MICROSOFT_REDIRECT_URI")
        if configured_uri:
            return configured_uri.strip()

        redirect_path = normalize_microsoft_redirect_path(
            current_app.config.get("AUTH_MICROSOFT_REDIRECT_PATH")
        )
        if redirect_path == DEFAULT_MICROSOFT_REDIRECT_PATH:
            return url_for("auth.callback", _external=True)

        return urljoin(request.url_root, redirect_path.lstrip("/"))

    def _client(self) -> msal.ConfidentialClientApplication:
        if not self.is_configured:
            raise AuthConfigurationError()
        return msal.ConfidentialClientApplication(
            client_id=self.client_id,
            authority=self.authority,
            client_credential=self.client_secret,
        )

    def build_authorization_url(self, next_url: str | None = None) -> str:
        state = secrets.token_urlsafe(32)
        session[AUTH_STATE_SESSION_KEY] = state
        session[AUTH_NEXT_SESSION_KEY] = next_url or url_for("main.index")

        return self._client().get_authorization_request_url(
            scopes=self.scopes,
            state=state,
            redirect_uri=self.redirect_uri(),
        )

    def validate_state(self, received_state: str | None) -> None:
        expected_state = session.pop(AUTH_STATE_SESSION_KEY, None)
        if not received_state or not expected_state or received_state != expected_state:
            raise AuthStateError()

    def acquire_token_by_auth_code(self, code: str) -> dict[str, Any]:
        return self._client().acquire_token_by_authorization_code(
            code=code,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri(),
        )

    @staticmethod
    def extract_claims(token_result: dict[str, Any]) -> dict[str, Any]:
        claims = token_result.get("id_token_claims")
        if not claims:
            error_description = token_result.get("error_description") or (
                "Token sem claims de identidade."
            )
            raise AuthAccessTokenError(error_description)
        return claims


def pop_auth_next_url() -> str:
    return session.pop(AUTH_NEXT_SESSION_KEY, url_for("main.index"))


class AuthAccessTokenError(AuthConfigurationError):
    status_code = 401
