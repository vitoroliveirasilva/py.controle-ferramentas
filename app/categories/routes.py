from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.categories.forms import CategoryForm
from app.categories.repositories import base_category_query, get_category_by_id
from app.categories.services import create_category, set_category_active, update_category
from app.core.pagination import clamp_page, paginate
from app.permissions.decorators import permission_required

bp = Blueprint("categories", __name__, url_prefix="/admin/categories")


def _form_data(form: CategoryForm) -> dict:
    return {
        "codigo": form.codigo.data,
        "nome": form.nome.data,
        "descricao": form.descricao.data,
        "ativo": form.ativo.data,
        "controle_individual_padrao": form.controle_individual_padrao.data,
        "requer_numero_serie": form.requer_numero_serie.data,
        "requer_calibracao": form.requer_calibracao.data,
        "motivo": form.motivo.data,
    }


@bp.get("/")
@permission_required("categories.manage")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    result = paginate(base_category_query(search, status), page=page, per_page=15)
    return render_template("categories/index.html", page=result, search=search, status=status)


@bp.route("/new", methods=["GET", "POST"])
@permission_required("categories.manage")
def create():
    form = CategoryForm(ativo=True, controle_individual_padrao=True)
    if form.validate_on_submit():
        try:
            category = create_category(_form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Categoria criada com sucesso.", "success")
            return redirect(url_for("categories.edit", category_id=category.id_categoria))
    return render_template("categories/form.html", form=form, category=None)


@bp.route("/<int:category_id>/edit", methods=["GET", "POST"])
@permission_required("categories.manage")
def edit(category_id: int):
    category = get_category_by_id(category_id)
    if not category or category.is_deleted:
        flash("Categoria não encontrada.", "warning")
        return redirect(url_for("categories.index"))

    form = CategoryForm(obj=category)
    if form.validate_on_submit():
        try:
            update_category(category, _form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Categoria atualizada com sucesso.", "success")
            return redirect(url_for("categories.edit", category_id=category.id_categoria))
    return render_template("categories/form.html", form=form, category=category)


@bp.post("/<int:category_id>/deactivate")
@permission_required("categories.manage")
def deactivate(category_id: int):
    category = get_category_by_id(category_id)
    reason = request.form.get("motivo", "").strip()
    if category:
        try:
            set_category_active(category, False, reason)
            flash("Categoria inativada.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("categories.index"))


@bp.post("/<int:category_id>/activate")
@permission_required("categories.manage")
def activate(category_id: int):
    category = get_category_by_id(category_id)
    reason = request.form.get("motivo", "Reativação administrativa.").strip()
    if category:
        try:
            set_category_active(category, True, reason)
            flash("Categoria ativada.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("categories.index"))
