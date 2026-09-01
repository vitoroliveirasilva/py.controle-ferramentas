from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.core.pagination import clamp_page, paginate
from app.permissions.decorators import permission_required
from app.signatures.repositories import base_signature_query, get_signature_by_id

bp = Blueprint("signatures", __name__, url_prefix="/admin/signatures")


@bp.get("/")
@permission_required("audit.view")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    action = request.args.get("action", "").strip()
    result = request.args.get("result", "").strip()
    page_result = paginate(
        base_signature_query(search, action, result),
        page=page,
        per_page=20,
    )
    return render_template(
        "signatures/index.html",
        page=page_result,
        search=search,
        action=action,
        result=result,
    )


@bp.get("/<int:signature_id>")
@permission_required("audit.view")
def detail(signature_id: int):
    signature = get_signature_by_id(signature_id)
    if not signature:
        flash("Assinatura não encontrada.", "warning")
        return redirect(url_for("signatures.index"))
    return render_template("signatures/detail.html", signature=signature)
