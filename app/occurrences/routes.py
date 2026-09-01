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
from app.models.enums import OccurrenceStatus, OccurrenceType
from app.occurrences.forms import (
    OccurrenceAttachmentForm,
    OccurrenceDecisionForm,
    OccurrenceForm,
    OccurrenceResolveForm,
)
from app.occurrences.repositories import (
    base_occurrence_query,
    get_occurrence_attachment_by_id,
    get_occurrence_by_id,
    list_occurrence_attachments,
)
from app.occurrences.services import (
    add_occurrence_attachment,
    approve_occurrence,
    cancel_occurrence,
    create_occurrence,
    get_occurrence_attachment_path,
    reject_occurrence,
    resolve_occurrence,
    send_to_analysis,
)
from app.permissions.decorators import permission_required
from app.permissions.scope_filters import (
    ScopeAccessDenied,
    assert_can_access_occurrence,
)
from app.signatures.repositories import list_occurrence_signatures

bp = Blueprint("occurrences", __name__, url_prefix="/admin/occurrences")


def _form_data(form: OccurrenceForm) -> dict:
    return {
        "codigo_ferramenta": form.codigo_ferramenta.data,
        "tipo_ocorrencia": form.tipo_ocorrencia.data,
        "motivo": form.motivo.data,
        "descricao": form.descricao.data,
        "fato_em": form.fato_em.data,
    }


def _ensure_occurrence_in_scope(occurrence) -> bool:
    try:
        assert_can_access_occurrence(current_user, occurrence)
    except ScopeAccessDenied:
        flash("Você não possui escopo para acessar esta ocorrência.", "danger")
        return False
    return True


@bp.get("/")
@permission_required("occurrences.view")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    result = paginate(
        base_occurrence_query(search, status, user=current_user),
        page=page,
        per_page=15,
    )
    return render_template(
        "occurrences/index.html",
        page=result,
        search=search,
        status=status,
        statuses=OccurrenceStatus.choices(),
    )


@bp.route("/create", methods=["GET", "POST"])
@permission_required("occurrences.create")
def create():
    form = OccurrenceForm(tipo_ocorrencia=OccurrenceType.DANO.value)
    if form.validate_on_submit():
        try:
            occurrence = create_occurrence(_form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Ocorrência registrada com sucesso.", "success")
            return redirect(
                url_for("occurrences.detail", occurrence_id=occurrence.id_occurrence)
            )
    return render_template("occurrences/form.html", form=form)


@bp.get("/<int:occurrence_id>")
@permission_required("occurrences.view")
def detail(occurrence_id: int):
    occurrence = get_occurrence_by_id(occurrence_id)
    if not occurrence or occurrence.is_deleted:
        flash("Ocorrência não encontrada.", "warning")
        return redirect(url_for("occurrences.index"))
    if not _ensure_occurrence_in_scope(occurrence):
        return redirect(url_for("occurrences.index"))
    return render_template(
        "occurrences/detail.html",
        occurrence=occurrence,
        attachments=list_occurrence_attachments(occurrence.id_occurrence),
        decision_form=OccurrenceDecisionForm(),
        resolve_form=OccurrenceResolveForm(),
        attachment_form=OccurrenceAttachmentForm(),
        signatures=list_occurrence_signatures(occurrence.id_occurrence),
    )


@bp.post("/<int:occurrence_id>/analyze")
@permission_required("occurrences.resolve")
def analyze(occurrence_id: int):
    occurrence = get_occurrence_by_id(occurrence_id)
    if occurrence and not _ensure_occurrence_in_scope(occurrence):
        return redirect(url_for("occurrences.index"))
    form = OccurrenceDecisionForm()
    if occurrence and form.validate_on_submit():
        try:
            send_to_analysis(occurrence, form.motivo.data)
            flash("Ocorrência colocada em análise.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    else:
        flash("Informe um motivo para colocar em análise.", "danger")
    return redirect(url_for("occurrences.detail", occurrence_id=occurrence_id))


@bp.post("/<int:occurrence_id>/approve")
@permission_required("occurrences.approve")
def approve(occurrence_id: int):
    occurrence = get_occurrence_by_id(occurrence_id)
    if occurrence and not _ensure_occurrence_in_scope(occurrence):
        return redirect(url_for("occurrences.index"))
    form = OccurrenceDecisionForm()
    if occurrence and form.validate_on_submit():
        try:
            approve_occurrence(occurrence, form.motivo.data)
            flash("Ocorrência aprovada.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    else:
        flash("Informe o motivo da aprovação.", "danger")
    return redirect(url_for("occurrences.detail", occurrence_id=occurrence_id))


@bp.post("/<int:occurrence_id>/reject")
@permission_required("occurrences.reject")
def reject(occurrence_id: int):
    occurrence = get_occurrence_by_id(occurrence_id)
    if occurrence and not _ensure_occurrence_in_scope(occurrence):
        return redirect(url_for("occurrences.index"))
    form = OccurrenceDecisionForm()
    if occurrence and form.validate_on_submit():
        try:
            reject_occurrence(occurrence, form.motivo.data)
            flash("Ocorrência recusada.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    else:
        flash("Informe o motivo da recusa.", "danger")
    return redirect(url_for("occurrences.detail", occurrence_id=occurrence_id))


@bp.post("/<int:occurrence_id>/resolve")
@permission_required("occurrences.resolve")
def resolve(occurrence_id: int):
    occurrence = get_occurrence_by_id(occurrence_id)
    if occurrence and not _ensure_occurrence_in_scope(occurrence):
        return redirect(url_for("occurrences.index"))
    form = OccurrenceResolveForm()
    if occurrence and form.validate_on_submit():
        try:
            resolve_occurrence(occurrence, form.observacoes_resolucao.data)
            flash("Ocorrência resolvida.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    else:
        flash("Informe a resolução da ocorrência.", "danger")
    return redirect(url_for("occurrences.detail", occurrence_id=occurrence_id))


@bp.post("/<int:occurrence_id>/cancel")
@permission_required("occurrences.resolve")
def cancel(occurrence_id: int):
    occurrence = get_occurrence_by_id(occurrence_id)
    if occurrence and not _ensure_occurrence_in_scope(occurrence):
        return redirect(url_for("occurrences.index"))
    form = OccurrenceDecisionForm()
    if occurrence and form.validate_on_submit():
        try:
            cancel_occurrence(occurrence, form.motivo.data)
            flash("Ocorrência cancelada.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    else:
        flash("Informe o motivo do cancelamento.", "danger")
    return redirect(url_for("occurrences.detail", occurrence_id=occurrence_id))


@bp.post("/<int:occurrence_id>/attachments")
@permission_required("occurrences.create")
def upload_attachment(occurrence_id: int):
    occurrence = get_occurrence_by_id(occurrence_id)
    if occurrence and not _ensure_occurrence_in_scope(occurrence):
        return redirect(url_for("occurrences.index"))
    form = OccurrenceAttachmentForm()
    if occurrence and form.validate_on_submit():
        try:
            add_occurrence_attachment(
                occurrence, form.arquivo.data, form.descricao.data
            )
            flash("Anexo incluído na ocorrência.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    else:
        flash(
            "Não foi possível anexar o arquivo. Use PDF ou imagem de até 8 MB.",
            "danger",
        )
    return redirect(url_for("occurrences.detail", occurrence_id=occurrence_id))


@bp.get("/attachments/<int:attachment_id>/download")
@permission_required("occurrences.view")
def download_attachment(attachment_id: int):
    attachment = get_occurrence_attachment_by_id(attachment_id)
    if not attachment or not attachment.occurrence:
        flash("Anexo não encontrado.", "warning")
        return redirect(url_for("occurrences.index"))
    if not _ensure_occurrence_in_scope(attachment.occurrence):
        return redirect(url_for("occurrences.index"))

    try:
        path = get_occurrence_attachment_path(attachment)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(
            url_for("occurrences.detail", occurrence_id=attachment.id_occurrence)
        )
    if not path.exists():
        flash("Arquivo do anexo não encontrado no armazenamento.", "warning")
        return redirect(
            url_for("occurrences.detail", occurrence_id=attachment.id_occurrence)
        )

    record_audit_log(
        action="occurrence.attachment.download",
        entity="occurrence_attachment",
        entity_id=attachment.id_attachment,
        after={
            "id_occurrence": attachment.id_occurrence,
            "filename": attachment.filename_original,
        },
        reason="Download de anexo de ocorrência.",
        commit=True,
    )
    return send_file(
        path,
        mimetype=attachment.content_type or "application/octet-stream",
        as_attachment=True,
        download_name=attachment.filename_original,
    )
