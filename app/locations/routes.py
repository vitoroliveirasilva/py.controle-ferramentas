from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.core.pagination import clamp_page, paginate
from app.locations.forms import LocationForm
from app.locations.repositories import base_location_query, get_location_by_id
from app.locations.services import create_location, set_location_active, update_location
from app.models.enums import LocationType
from app.permissions.decorators import permission_required

bp = Blueprint("locations", __name__, url_prefix="/admin/locations")


def _form_data(form: LocationForm) -> dict:
    return {
        "codigo": form.codigo.data,
        "nome": form.nome.data,
        "tipo_local": form.tipo_local.data,
        "filial": form.filial.data,
        "departamento": form.departamento.data,
        "responsavel_nome": form.responsavel_nome.data,
        "endereco": form.endereco.data,
        "observacoes": form.observacoes.data,
        "ativo": form.ativo.data,
        "motivo": form.motivo.data,
    }


@bp.get("/")
@permission_required("locations.manage")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    location_type = request.args.get("tipo", "").strip()
    result = paginate(
        base_location_query(search, status, location_type), page=page, per_page=15
    )
    return render_template(
        "locations/index.html",
        page=result,
        search=search,
        status=status,
        location_type=location_type,
        location_types=LocationType.choices(),
    )


@bp.route("/new", methods=["GET", "POST"])
@permission_required("locations.manage")
def create():
    form = LocationForm(ativo=True)
    if form.validate_on_submit():
        try:
            location = create_location(_form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Local criado com sucesso.", "success")
            return redirect(url_for("locations.edit", location_id=location.id_location))
    return render_template("locations/form.html", form=form, location=None)


@bp.route("/<int:location_id>/edit", methods=["GET", "POST"])
@permission_required("locations.manage")
def edit(location_id: int):
    location = get_location_by_id(location_id)
    if not location or location.is_deleted:
        flash("Local não encontrado.", "warning")
        return redirect(url_for("locations.index"))
    form = LocationForm(obj=location)
    if form.validate_on_submit():
        try:
            update_location(location, _form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Local atualizado com sucesso.", "success")
            return redirect(url_for("locations.edit", location_id=location.id_location))
    return render_template("locations/form.html", form=form, location=location)


@bp.post("/<int:location_id>/deactivate")
@permission_required("locations.manage")
def deactivate(location_id: int):
    location = get_location_by_id(location_id)
    reason = request.form.get("motivo", "").strip()
    if location:
        try:
            set_location_active(location, False, reason)
            flash("Local inativado.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("locations.index"))


@bp.post("/<int:location_id>/activate")
@permission_required("locations.manage")
def activate(location_id: int):
    location = get_location_by_id(location_id)
    reason = request.form.get("motivo", "Reativação administrativa.").strip()
    if location:
        try:
            set_location_active(location, True, reason)
            flash("Local ativado.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("locations.index"))
