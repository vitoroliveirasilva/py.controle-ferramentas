from __future__ import annotations

from flask import Blueprint, current_app, jsonify
from sqlalchemy import func, text

from app.auth.msal_client import MicrosoftAuthClient
from app.extensions import db
from app.permissions.models import PermissionModel, RoleModel

bp = Blueprint("health", __name__)


@bp.get("/healthz")
@bp.get("/health")
def health_check():
    return jsonify(
        {
            "status": "ok",
            "service": current_app.config["PROJECT_NAME"],
            "version": current_app.config["APP_VERSION"],
            "environment": current_app.config["APP_ENV"],
        }
    )


@bp.get("/readyz")
def readiness_check():
    checks = {
        "app_factory": "ok",
        "templates": "ok",
        "database": "unknown",
        "authentication": "unknown",
        "authorization": "unknown",
    }

    status = "ready"

    try:
        db.session.execute(text("SELECT 1")).scalar_one()
        checks["database"] = "ok"
    except Exception as exc:
        current_app.logger.warning("Readiness database check failed: %s", exc)
        checks["database"] = "error"
        status = "degraded"

    msal_client = MicrosoftAuthClient()
    if msal_client.is_configured:
        checks["authentication"] = "microsoft_configured"
    elif current_app.config.get("AUTH_DEV_LOGIN_ENABLED"):
        checks["authentication"] = "dev_login_enabled"
    else:
        checks["authentication"] = "not_configured_yet"
        status = "degraded"

    try:
        roles_count = db.session.execute(
            db.select(func.count(RoleModel.id_role))
        ).scalar_one()
        permissions_count = db.session.execute(
            db.select(func.count(PermissionModel.id_permission))
        ).scalar_one()
        checks["authorization"] = (
            "seeded" if roles_count > 0 and permissions_count > 0 else "not_seeded_yet"
        )
        if checks["authorization"] == "not_seeded_yet":
            status = "degraded"
    except Exception as exc:
        current_app.logger.warning("Readiness authorization check failed: %s", exc)
        checks["authorization"] = "error"
        status = "degraded"

    http_status = 200 if status == "ready" else 503
    return jsonify({"status": status, "checks": checks}), http_status
