from __future__ import annotations

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from app.core.exceptions import AppError


def _wants_json_response() -> bool:
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    return (
        best == "application/json"
        and request.accept_mimetypes[best] > request.accept_mimetypes["text/html"]
    )


def _render_error(status_code: int, message: str):
    if _wants_json_response():
        return (
            jsonify({"error": {"code": status_code, "message": message}}),
            status_code,
        )

    template_name = f"errors/{status_code}.html"
    return (
        render_template(template_name, status_code=status_code, message=message),
        status_code,
    )


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        app.logger.warning("Erro controlado: %s", error.message)
        return _render_error(error.status_code, error.message)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        message = error.description or "Erro HTTP."
        app.logger.info("Erro HTTP %s: %s", error.code, message)
        return _render_error(error.code or 500, message)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Erro inesperado: %s", error)
        message = "Ocorreu um erro inesperado. Tente novamente ou acione o suporte."
        return _render_error(500, message)
