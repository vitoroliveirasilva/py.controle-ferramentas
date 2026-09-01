from __future__ import annotations

from urllib.parse import urljoin, urlparse

from flask import Flask, request


# Validação de URLs de redirecionamento para evitar vulnerabilidades de redirecionamento aberto
def is_safe_next_url(target: str | None) -> bool:
    if not target:
        return False

    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))

    return test_url.scheme in {"http", "https"} and ref_url.netloc == test_url.netloc


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def apply_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )

        if app.config.get("FORCE_HTTPS_HEADERS"):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response
