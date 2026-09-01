from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.core.pagination import clamp_page, paginate
from app.custody.forms import CustodyAssignmentForm
from app.custody.repositories import (
    active_tools_without_custody_query,
    base_current_custody_query,
    get_current_custody,
    list_custody_history,
    list_timeline_events,
)
from app.custody.services import assign_initial_custody, force_change_custody
from app.locations.repositories import list_active_locations
from app.models.enums import CustodyType
from app.permissions.decorators import permission_required
from app.permissions.scope_filters import ScopeAccessDenied, assert_can_access_tool
from app.tools.repositories import get_tool_by_id
from app.users.repositories import list_active_users

bp = Blueprint("custody", __name__, url_prefix="/admin/custody")


def _configure_choices(form: CustodyAssignmentForm) -> None:
    form.id_responsavel_usuario.choices = [(0, "Selecione")] + [
        (user.id_usuario, f"{user.nome} <{user.email_lower}>")
        for user in list_active_users()
    ]
    form.id_location.choices = [(0, "Selecione")] + [
        (location.id_location, f"{location.nome} ({location.codigo})")
        for location in list_active_locations()
    ]


def _form_data(form: CustodyAssignmentForm) -> dict:
    return {
        "tipo_custodia": form.tipo_custodia.data,
        "id_responsavel_usuario": form.id_responsavel_usuario.data,
        "id_location": form.id_location.data,
        "motivo": form.motivo.data,
    }


def _ensure_tool_in_scope(tool) -> bool:
    try:
        assert_can_access_tool(current_user, tool)
    except ScopeAccessDenied:
        flash("Você não possui escopo para acessar esta ferramenta.", "danger")
        return False
    return True


@bp.get("/")
@permission_required("custody.view")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    custody_type = request.args.get("tipo", "").strip()
    result = paginate(
        base_current_custody_query(search, custody_type, user=current_user),
        page=page,
        per_page=15,
    )
    return render_template(
        "custody/index.html",
        page=result,
        search=search,
        custody_type=custody_type,
        custody_types=CustodyType.choices(),
    )


@bp.get("/missing")
@permission_required("custody.view")
def missing():
    page = clamp_page(request.args.get("page"))
    result = paginate(
        active_tools_without_custody_query(user=current_user),
        page=page,
        per_page=15,
    )
    return render_template("custody/missing.html", page=result)


@bp.get("/tools/<int:tool_id>")
@permission_required("custody.view")
def detail(tool_id: int):
    tool = get_tool_by_id(tool_id)
    if not tool or tool.is_deleted:
        flash("Ferramenta não encontrada.", "warning")
        return redirect(url_for("tools.index"))
    if not _ensure_tool_in_scope(tool):
        return redirect(url_for("custody.index"))
    return render_template(
        "custody/detail.html",
        tool=tool,
        current_custody=get_current_custody(tool.id_tool),
        history=list_custody_history(tool.id_tool),
        timeline=list_timeline_events(tool.id_tool),
    )


@bp.route("/tools/<int:tool_id>/initial", methods=["GET", "POST"])
@permission_required("custody.assign_initial")
def initial(tool_id: int):
    tool = get_tool_by_id(tool_id)
    if not tool or tool.is_deleted:
        flash("Ferramenta não encontrada.", "warning")
        return redirect(url_for("tools.index"))
    if not _ensure_tool_in_scope(tool):
        return redirect(url_for("custody.index"))
    form = CustodyAssignmentForm(tipo_custodia=CustodyType.ALMOXARIFADO.value)
    _configure_choices(form)
    if get_current_custody(tool.id_tool):
        flash("Esta ferramenta já possui custódia atual.", "warning")
        return redirect(url_for("custody.detail", tool_id=tool.id_tool))
    if form.validate_on_submit():
        try:
            assign_initial_custody(tool, _form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Custódia inicial definida com sucesso.", "success")
            return redirect(url_for("custody.detail", tool_id=tool.id_tool))
    return render_template("custody/form.html", form=form, tool=tool, mode="initial")


@bp.route("/tools/<int:tool_id>/change", methods=["GET", "POST"])
@permission_required("custody.force_change")
def change(tool_id: int):
    tool = get_tool_by_id(tool_id)
    if not tool or tool.is_deleted:
        flash("Ferramenta não encontrada.", "warning")
        return redirect(url_for("tools.index"))
    if not _ensure_tool_in_scope(tool):
        return redirect(url_for("custody.index"))
    form = CustodyAssignmentForm()
    _configure_choices(form)
    if not get_current_custody(tool.id_tool):
        flash("Defina a custódia inicial antes de transferir.", "warning")
        return redirect(url_for("custody.initial", tool_id=tool.id_tool))
    if form.validate_on_submit():
        try:
            force_change_custody(tool, _form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Custódia administrativa alterada com sucesso.", "success")
            return redirect(url_for("custody.detail", tool_id=tool.id_tool))
    return render_template("custody/form.html", form=form, tool=tool, mode="change")
