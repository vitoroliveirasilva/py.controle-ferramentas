from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import jsonify, redirect, request, url_for
from flask_login import current_user, login_required, logout_user

from app.auth.services import load_active_user_for_session


def _wants_json_response() -> bool:
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return (
        best == "application/json"
        and request.accept_mimetypes[best] > request.accept_mimetypes["text/html"]
    )


def _reject_invalid_session():
    logout_user()
    message = "Sessão inválida ou usuário inativo. Faça login novamente."
    if _wants_json_response():
        return jsonify({"error": {"code": 401, "message": message}}), 401
    return redirect(url_for("auth.login", next=request.full_path or request.path))


# Requer um usuário autenticado, ativo e não bloqueado
def active_user_required(view: Callable) -> Callable:

    @wraps(view)
    @login_required
    def wrapped(*args: Any, **kwargs: Any):
        raw_user_id = current_user.get_id()
        if not raw_user_id or not raw_user_id.isdigit():
            return _reject_invalid_session()

        fresh_user = load_active_user_for_session(int(raw_user_id))
        if not fresh_user:
            return _reject_invalid_session()

        return view(*args, **kwargs)

    return wrapped
