from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user

from app.audit.services import record_audit_log
from app.core.pagination import clamp_page, paginate
from app.inventories.forms import (
    InventoryCancelForm,
    InventoryDivergenceResolveForm,
    InventoryEvidenceUploadForm,
    InventoryExcessForm,
    InventoryFinishForm,
    InventoryForm,
    InventoryItemUpdateForm,
    InventoryScanForm,
)
from app.inventories.repositories import (
    base_inventory_query,
    get_inventory_divergence_by_id,
    get_inventory_item_by_id,
    get_inventory_item_evidence_by_id,
    get_inventory_with_items,
    list_inventory_divergences,
)
from app.inventories.services import (
    cancel_inventory,
    create_inventory,
    finish_inventory,
    get_inventory_evidence_path,
    inventory_progress,
    register_inventory_excess,
    resolve_inventory_divergence,
    save_inventory_item_evidence,
    scan_inventory_item,
    sign_inventory,
    start_inventory,
    update_inventory_item_status,
)
from app.locations.repositories import list_active_locations
from app.models.enums import (
    InventoryDivergenceAction,
    InventoryItemStatus,
    InventoryScopeType,
    InventoryStatus,
)
from app.permissions.decorators import permission_required
from app.permissions.scope_filters import ScopeAccessDenied, assert_can_access_inventory
from app.signatures.forms import SignatureConfirmForm
from app.signatures.repositories import list_inventory_signatures
from app.users.repositories import list_active_users

bp = Blueprint("inventories", __name__, url_prefix="/admin/inventories")


def _configure_inventory_choices(form: InventoryForm) -> None:
    form.escopo_usuario_id.choices = [(0, "Selecione")] + [
        (user.id_usuario, f"{user.nome} <{user.email_lower}>") for user in list_active_users()
    ]
    form.escopo_location_id.choices = [(0, "Selecione")] + [
        (location.id_location, f"{location.nome} ({location.codigo})")
        for location in list_active_locations()
    ]


def _inventory_form_data(form: InventoryForm) -> dict:
    return {
        "titulo": form.titulo.data,
        "tipo_inventario": form.tipo_inventario.data,
        "escopo_tipo": form.escopo_tipo.data,
        "escopo_usuario_id": form.escopo_usuario_id.data,
        "escopo_location_id": form.escopo_location_id.data,
        "status_inicial": form.status_inicial.data,
        "descricao": form.descricao.data,
    }


def _ensure_inventory_in_scope(inventory) -> bool:
    try:
        assert_can_access_inventory(current_user, inventory)
    except ScopeAccessDenied:
        flash("Você não possui escopo para acessar este inventário.", "danger")
        return False
    return True


@bp.get("/")
@permission_required("inventories.view")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    result = paginate(
        base_inventory_query(search, status, user=current_user),
        page=page,
        per_page=15,
    )
    return render_template(
        "inventories/index.html",
        page=result,
        search=search,
        status=status,
        statuses=InventoryStatus.choices(),
    )


@bp.route("/new", methods=["GET", "POST"])
@permission_required("inventories.create")
def create():
    form = InventoryForm(status_inicial=InventoryStatus.RASCUNHO.value)
    _configure_inventory_choices(form)
    if form.validate_on_submit():
        try:
            inventory = create_inventory(_inventory_form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Inventário criado com sucesso.", "success")
            return redirect(url_for("inventories.detail", inventory_id=inventory.id_inventory))
    return render_template(
        "inventories/form.html",
        form=form,
        scope_types=InventoryScopeType.choices(),
    )


@bp.get("/<int:inventory_id>")
@permission_required("inventories.view")
def detail(inventory_id: int):
    inventory = get_inventory_with_items(inventory_id)
    if not inventory:
        flash("Inventário não encontrado.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    return render_template(
        "inventories/detail.html",
        inventory=inventory,
        progress=inventory_progress(inventory),
        divergences=list_inventory_divergences(inventory.id_inventory),
        item_statuses=InventoryItemStatus.choices(),
        divergence_actions=InventoryDivergenceAction.choices(),
        update_form=InventoryItemUpdateForm(),
        resolve_form=InventoryDivergenceResolveForm(),
        finish_form=InventoryFinishForm(),
        cancel_form=InventoryCancelForm(),
        signature_form=SignatureConfirmForm(),
        scan_form=InventoryScanForm(),
        evidence_form=InventoryEvidenceUploadForm(),
        excess_form=InventoryExcessForm(),
        signatures=list_inventory_signatures(inventory.id_inventory),
    )


@bp.post("/<int:inventory_id>/start")
@permission_required("inventories.update")
def start(inventory_id: int):
    inventory = get_inventory_with_items(inventory_id)
    if not inventory:
        flash("Inventário não encontrado.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    try:
        start_inventory(inventory)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash(
            "Inventário iniciado. As ferramentas esperadas foram marcadas em inventário.",
            "success",
        )
    return redirect(url_for("inventories.detail", inventory_id=inventory.id_inventory))


@bp.post("/<int:inventory_id>/items/<int:item_id>/status")
@permission_required("inventories.perform")
def update_item_status(inventory_id: int, item_id: int):
    inventory = get_inventory_with_items(inventory_id)
    item = get_inventory_item_by_id(item_id)
    if not inventory or not item or item.id_inventory != inventory.id_inventory:
        flash("Item de inventário não encontrado.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    form = InventoryItemUpdateForm()
    if form.validate_on_submit():
        try:
            update_inventory_item_status(
                inventory,
                item,
                form.item_status.data,
                form.observacao.data,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Conferência salva.", "success")
    else:
        flash("Não foi possível salvar a conferência. Revise o status informado.", "danger")
    return redirect(url_for("inventories.detail", inventory_id=inventory.id_inventory))


@bp.post("/<int:inventory_id>/items/<int:item_id>/quick/<status>")
@permission_required("inventories.perform")
def quick_item_status(inventory_id: int, item_id: int, status: str):
    inventory = get_inventory_with_items(inventory_id)
    item = get_inventory_item_by_id(item_id)
    if not inventory or not item or item.id_inventory != inventory.id_inventory:
        flash("Item de inventário não encontrado.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    try:
        update_inventory_item_status(inventory, item, status, request.form.get("observacao"))
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Conferência rápida salva.", "success")
    return redirect(url_for("inventories.detail", inventory_id=inventory.id_inventory))


@bp.post("/<int:inventory_id>/divergences/<int:divergence_id>/resolve")
@permission_required("inventories.resolve_divergence")
def resolve_divergence(inventory_id: int, divergence_id: int):
    inventory = get_inventory_with_items(inventory_id)
    divergence = get_inventory_divergence_by_id(divergence_id)
    if not inventory or not divergence or divergence.id_inventory != inventory.id_inventory:
        flash("Divergência não encontrada.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    form = InventoryDivergenceResolveForm()
    if form.validate_on_submit():
        try:
            resolve_inventory_divergence(
                inventory,
                divergence,
                form.acao_regularizacao.data,
                form.resolucao.data,
                occurrence_id=form.occurrence_id.data,
                transfer_id=form.transfer_id.data,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Divergência regularizada.", "success")
    else:
        flash("Informe ação e justificativa para regularizar a divergência.", "danger")
    return redirect(url_for("inventories.detail", inventory_id=inventory.id_inventory))


@bp.post("/<int:inventory_id>/excess")
@permission_required("inventories.perform")
def register_excess(inventory_id: int):
    inventory = get_inventory_with_items(inventory_id)
    if not inventory:
        flash("Inventário não encontrado.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    form = InventoryExcessForm()
    if form.validate_on_submit():
        try:
            register_inventory_excess(
                inventory,
                form.identificador.data,
                form.observacao.data,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Ferramenta excedente registrada como divergência.", "success")
    else:
        flash("Informe código e observação para registrar o excedente.", "danger")
    return redirect(url_for("inventories.detail", inventory_id=inventory.id_inventory))


@bp.post("/<int:inventory_id>/finish")
@permission_required("inventories.finish")
def finish(inventory_id: int):
    inventory = get_inventory_with_items(inventory_id)
    if not inventory:
        flash("Inventário não encontrado.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    form = InventoryFinishForm()
    if form.validate_on_submit():
        try:
            finish_inventory(inventory, form.motivo.data)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Inventário enviado para assinatura.", "success")
    else:
        flash("Não foi possível enviar o inventário para assinatura.", "danger")
    return redirect(url_for("inventories.detail", inventory_id=inventory.id_inventory))


@bp.post("/<int:inventory_id>/sign")
@permission_required("inventories.sign")
def sign(inventory_id: int):
    inventory = get_inventory_with_items(inventory_id)
    if not inventory:
        flash("Inventário não encontrado.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    form = SignatureConfirmForm()
    if form.validate_on_submit():
        try:
            sign_inventory(inventory, form.motivo.data)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Inventário assinado e finalizado.", "success")
    else:
        flash("Confirme a responsabilidade e informe uma justificativa para assinar.", "danger")
    return redirect(url_for("inventories.detail", inventory_id=inventory.id_inventory))


@bp.post("/<int:inventory_id>/cancel")
@permission_required("inventories.cancel")
def cancel(inventory_id: int):
    inventory = get_inventory_with_items(inventory_id)
    if not inventory:
        flash("Inventário não encontrado.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    form = InventoryCancelForm()
    if form.validate_on_submit():
        try:
            cancel_inventory(inventory, form.motivo.data)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Inventário cancelado.", "success")
    else:
        flash("Informe um motivo de cancelamento com pelo menos 5 caracteres.", "danger")
    return redirect(url_for("inventories.detail", inventory_id=inventory.id_inventory))


@bp.route("/<int:inventory_id>/scan", methods=["GET", "POST"])
@permission_required("inventories.perform")
def scan(inventory_id: int):
    inventory = get_inventory_with_items(inventory_id)
    if not inventory:
        flash("Inventário não encontrado.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    form = InventoryScanForm()
    if form.validate_on_submit():
        try:
            item = scan_inventory_item(inventory, form.codigo.data, form.observacao.data)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash(f"Item {item.codigo_interno_snapshot} marcado como encontrado.", "success")
            return redirect(url_for("inventories.scan", inventory_id=inventory.id_inventory))
    return render_template(
        "inventories/scan.html",
        inventory=inventory,
        form=form,
        progress=inventory_progress(inventory),
    )


@bp.post("/<int:inventory_id>/items/<int:item_id>/evidence")
@permission_required("inventories.perform")
def upload_item_evidence(inventory_id: int, item_id: int):
    inventory = get_inventory_with_items(inventory_id)
    item = get_inventory_item_by_id(item_id)
    if not inventory or not item or item.id_inventory != inventory.id_inventory:
        flash("Item de inventário não encontrado.", "warning")
        return redirect(url_for("inventories.index"))
    if not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    form = InventoryEvidenceUploadForm()
    if form.validate_on_submit():
        try:
            save_inventory_item_evidence(
                inventory,
                item,
                request.files.get("evidencia"),
                form.observacao.data,
            )
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Evidência anexada ao item.", "success")
    else:
        flash("Não foi possível validar a evidência enviada.", "danger")
    return redirect(url_for("inventories.detail", inventory_id=inventory.id_inventory))


@bp.get("/evidence/<int:evidence_id>/download")
@permission_required("inventories.view")
def download_item_evidence(evidence_id: int):
    evidence = get_inventory_item_evidence_by_id(evidence_id)
    if not evidence or evidence.is_deleted:
        flash("Evidência não encontrada.", "warning")
        return redirect(url_for("inventories.index"))
    inventory = get_inventory_with_items(evidence.id_inventory)
    if not inventory or not _ensure_inventory_in_scope(inventory):
        return redirect(url_for("inventories.index"))
    path = get_inventory_evidence_path(evidence)
    if not path.exists():
        flash("Arquivo da evidência não encontrado no armazenamento.", "warning")
        return redirect(url_for("inventories.detail", inventory_id=evidence.id_inventory))
    record_audit_log(
        action="inventories.evidence.download",
        entity="inventory_item_evidence",
        entity_id=evidence.id_inventory_item_evidence,
        after={
            "id_inventory": evidence.id_inventory,
            "id_tool": evidence.id_tool,
            "filename": evidence.original_filename,
        },
        reason="Download de evidência de inventário.",
        commit=True,
    )
    return send_file(
        path,
        mimetype=evidence.content_type or "application/octet-stream",
        as_attachment=True,
        download_name=evidence.original_filename,
    )
