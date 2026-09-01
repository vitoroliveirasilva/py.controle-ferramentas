from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.audit.services import audit_log_statement, get_audit_log_by_id
from app.core.pagination import clamp_page, paginate
from app.permissions.decorators import permission_required

bp = Blueprint("audit", __name__, url_prefix="/admin/audit")


@bp.get("/")
@permission_required("audit.view")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    action = request.args.get("action", "").strip()
    entity = request.args.get("entity", "").strip()
    result = request.args.get("result", "").strip()
    user_email = request.args.get("user_email", "").strip()
    page_result = paginate(
        audit_log_statement(
            search=search,
            action=action,
            entity=entity,
            result=result,
            user_email=user_email,
        ),
        page=page,
        per_page=25,
    )
    return render_template(
        "audit/index.html",
        page=page_result,
        search=search,
        action=action,
        entity=entity,
        result=result,
        user_email=user_email,
    )


@bp.get("/<int:audit_log_id>")
@permission_required("audit.view")
def detail(audit_log_id: int):
    audit_log = get_audit_log_by_id(audit_log_id)
    if not audit_log:
        flash("Registro de auditoria não encontrado.", "warning")
        return redirect(url_for("audit.index"))
    return render_template("audit/detail.html", audit_log=audit_log)
