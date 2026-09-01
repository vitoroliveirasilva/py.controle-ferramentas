from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import jsonify, request
from flask_login import current_user, login_required

from app.auth.exceptions import AuthAccessDeniedError
from app.permissions.services import current_user_can


def _wants_json_response() -> bool:
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return (
        best == "application/json"
        and request.accept_mimetypes[best] > request.accept_mimetypes["text/html"]
    )


# Permissão granular decorador para rotas que exigem validação de acesso no backend
def permission_required(permission_code: str) -> Callable:

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        @login_required
        def wrapped(*args: Any, **kwargs: Any):
            if not current_user.is_active:
                raise AuthAccessDeniedError(
                    "Seu usuário local não está ativo para operar o sistema."
                )

            if not current_user_can(permission_code):
                message = f"Permissão necessária: {permission_code}."
                if _wants_json_response():
                    return jsonify({"error": {"code": 403, "message": message}}), 403
                raise AuthAccessDeniedError(message)

            return view(*args, **kwargs)

        return wrapped

    return decorator
