from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.core.pagination import clamp_page, paginate
from app.locations.repositories import list_active_locations
from app.models.enums import CustodyType, TransferStatus
from app.permissions.decorators import permission_required
from app.permissions.scope_filters import ScopeAccessDenied, assert_can_access_transfer
from app.signatures.repositories import list_transfer_signatures
from app.transfers.forms import TransferCreateForm, TransferDecisionForm
from app.transfers.repositories import (
    base_transfer_query,
    get_transfer_by_id,
    list_transfer_items,
)
from app.transfers.services import (
    cancel_transfer,
    confirm_destination,
    confirm_origin,
    create_transfer,
    expire_transfer,
    refuse_transfer,
)
from app.users.repositories import list_active_users

bp = Blueprint("transfers", __name__, url_prefix="/admin/transfers")


def _configure_create_choices(form: TransferCreateForm) -> None:
    form.destino_usuario_id.choices = [(0, "Selecione")] + [
        (user.id_usuario, f"{user.nome} <{user.email_lower}>")
        for user in list_active_users()
    ]
    form.destino_location_id.choices = [(0, "Selecione")] + [
        (location.id_location, f"{location.nome} ({location.codigo})")
        for location in list_active_locations()
    ]


def _form_data(form: TransferCreateForm) -> dict:
    return {
        "tipo_transferencia": form.tipo_transferencia.data,
        "destino_tipo_custodia": form.destino_tipo_custodia.data,
        "destino_usuario_id": form.destino_usuario_id.data,
        "destino_location_id": form.destino_location_id.data,
        "codigos_ferramentas": form.codigos_ferramentas.data,
        "motivo": form.motivo.data,
        "observacoes": form.observacoes.data,
    }


def _ensure_transfer_in_scope(transfer) -> bool:
    try:
        assert_can_access_transfer(current_user, transfer)
    except ScopeAccessDenied:
        flash("Você não possui escopo para acessar esta transferência.", "danger")
        return False
    return True


@bp.get("/")
@permission_required("transfers.view")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    result = paginate(
        base_transfer_query(search, status, user=current_user),
        page=page,
        per_page=15,
    )
    return render_template(
        "transfers/index.html",
        page=result,
        search=search,
        status=status,
        statuses=TransferStatus.choices(),
    )


@bp.route("/create", methods=["GET", "POST"])
@permission_required("transfers.create")
def create():
    form = TransferCreateForm(destino_tipo_custodia=CustodyType.TECNICO.value)
    _configure_create_choices(form)
    if form.validate_on_submit():
        try:
            transfer = create_transfer(_form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Transferência solicitada com sucesso.", "success")
            return redirect(
                url_for("transfers.detail", transfer_id=transfer.id_transfer)
            )
    return render_template("transfers/form.html", form=form)


@bp.get("/<int:transfer_id>")
@permission_required("transfers.view")
def detail(transfer_id: int):
    transfer = get_transfer_by_id(transfer_id)
    if not transfer or transfer.is_deleted:
        flash("Transferência não encontrada.", "warning")
        return redirect(url_for("transfers.index"))
    if not _ensure_transfer_in_scope(transfer):
        return redirect(url_for("transfers.index"))
    return render_template(
        "transfers/detail.html",
        transfer=transfer,
        items=list_transfer_items(transfer.id_transfer),
        decision_form=TransferDecisionForm(),
        signatures=list_transfer_signatures(transfer.id_transfer),
    )


@bp.post("/<int:transfer_id>/confirm-origin")
@permission_required("transfers.confirm_origin")
def confirm_origin_route(transfer_id: int):
    transfer = get_transfer_by_id(transfer_id)
    if transfer and not _ensure_transfer_in_scope(transfer):
        return redirect(url_for("transfers.index"))
    form = TransferDecisionForm()
    if transfer and form.validate_on_submit():
        try:
            confirm_origin(transfer, form.motivo.data)
            flash("Origem confirmada com sucesso.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("transfers.detail", transfer_id=transfer_id))


@bp.post("/<int:transfer_id>/confirm-destination")
@permission_required("transfers.confirm_destination")
def confirm_destination_route(transfer_id: int):
    transfer = get_transfer_by_id(transfer_id)
    if transfer and not _ensure_transfer_in_scope(transfer):
        return redirect(url_for("transfers.index"))
    form = TransferDecisionForm()
    if transfer and form.validate_on_submit():
        try:
            confirm_destination(transfer, form.motivo.data)
            flash("Destino confirmado e custódia atualizada.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("transfers.detail", transfer_id=transfer_id))


@bp.post("/<int:transfer_id>/refuse")
@permission_required("transfers.refuse")
def refuse_route(transfer_id: int):
    transfer = get_transfer_by_id(transfer_id)
    if transfer and not _ensure_transfer_in_scope(transfer):
        return redirect(url_for("transfers.index"))
    form = TransferDecisionForm()
    if transfer and form.validate_on_submit():
        try:
            refuse_transfer(transfer, form.motivo.data or "")
            flash("Transferência recusada.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("transfers.detail", transfer_id=transfer_id))


@bp.post("/<int:transfer_id>/cancel")
@permission_required("transfers.cancel")
def cancel_route(transfer_id: int):
    transfer = get_transfer_by_id(transfer_id)
    if transfer and not _ensure_transfer_in_scope(transfer):
        return redirect(url_for("transfers.index"))
    form = TransferDecisionForm()
    if transfer and form.validate_on_submit():
        try:
            cancel_transfer(transfer, form.motivo.data or "")
            flash("Transferência cancelada.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("transfers.detail", transfer_id=transfer_id))


@bp.post("/<int:transfer_id>/force-cancel")
@permission_required("transfers.force_cancel")
def force_cancel_route(transfer_id: int):
    transfer = get_transfer_by_id(transfer_id)
    if transfer and not _ensure_transfer_in_scope(transfer):
        return redirect(url_for("transfers.index"))
    form = TransferDecisionForm()
    if transfer and form.validate_on_submit():
        try:
            cancel_transfer(transfer, form.motivo.data or "", force=True)
            flash("Transferência cancelada com permissão especial.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("transfers.detail", transfer_id=transfer_id))


@bp.post("/<int:transfer_id>/expire")
@permission_required("transfers.override")
def expire_route(transfer_id: int):
    transfer = get_transfer_by_id(transfer_id)
    if transfer and not _ensure_transfer_in_scope(transfer):
        return redirect(url_for("transfers.index"))
    form = TransferDecisionForm()
    if transfer and form.validate_on_submit():
        try:
            expire_transfer(transfer, form.motivo.data or None)
            flash("Transferência expirada com segurança.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("transfers.detail", transfer_id=transfer_id))
