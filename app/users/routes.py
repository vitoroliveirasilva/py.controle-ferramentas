from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.core.pagination import clamp_page, paginate
from app.permissions.decorators import permission_required
from app.users.forms import StatusReasonForm, UserAdminForm
from app.users.repositories import base_user_query, get_user_by_id
from app.users.services import (
    change_user_operational_status,
    create_local_user,
    update_local_user,
)

bp = Blueprint("users", __name__, url_prefix="/admin/users")


def _form_data(form: UserAdminForm) -> dict:
    return {
        "email": form.email.data,
        "nome": form.nome.data,
        "microsoft_oid": form.microsoft_oid.data,
        "ativo": form.ativo.data,
        "bloqueado": form.bloqueado.data,
        "bloqueio_motivo": form.bloqueio_motivo.data,
        "observacoes": form.observacoes.data,
        "motivo": form.motivo.data,
    }


@bp.get("/")
@permission_required("users.view")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    result = paginate(base_user_query(search, status), page=page, per_page=15)
    return render_template(
        "users/index.html", page=result, search=search, status=status
    )


@bp.route("/new", methods=["GET", "POST"])
@permission_required("users.create")
def create():
    form = UserAdminForm(ativo=True)
    if form.validate_on_submit():
        try:
            user = create_local_user(**_form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Usuário criado com sucesso.", "success")
            return redirect(url_for("users.edit", user_id=user.id_usuario))
    return render_template("users/form.html", form=form, user=None)


@bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@permission_required("users.update")
def edit(user_id: int):
    user = get_user_by_id(user_id)
    if not user or user.is_deleted:
        flash("Usuário não encontrado.", "warning")
        return redirect(url_for("users.index"))
    form = UserAdminForm(obj=user)
    if form.validate_on_submit():
        try:
            update_local_user(user, _form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Usuário atualizado com sucesso.", "success")
            return redirect(url_for("users.edit", user_id=user.id_usuario))
    return render_template("users/form.html", form=form, user=user)


@bp.route("/<int:user_id>/<action>", methods=["GET", "POST"])
@permission_required("users.disable")
def status(user_id: int, action: str):
    user = get_user_by_id(user_id)
    if not user or user.is_deleted:
        flash("Usuário não encontrado.", "warning")
        return redirect(url_for("users.index"))
    if action not in {"activate", "deactivate", "block", "unblock"}:
        flash("Ação inválida.", "danger")
        return redirect(url_for("users.index"))

    form = StatusReasonForm()
    if form.validate_on_submit():
        try:
            change_user_operational_status(
                user,
                ativo=(
                    True
                    if action == "activate"
                    else False if action == "deactivate" else None
                ),
                bloqueado=(
                    True
                    if action == "block"
                    else False if action == "unblock" else None
                ),
                motivo=form.motivo.data,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Status do usuário atualizado.", "success")
            return redirect(url_for("users.index"))
    return render_template("users/status.html", form=form, user=user, action=action)
