from __future__ import annotations

from io import BytesIO

import qrcode
from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user
from qrcode.image.svg import SvgPathImage

from app.audit.services import record_audit_log
from app.categories.repositories import (
    list_active_categories,
    list_active_categories_for_tool_scope,
)
from app.core.pagination import clamp_page, paginate
from app.models.enums import ToolStatus
from app.permissions.decorators import permission_required
from app.permissions.scope_filters import ScopeAccessDenied, assert_can_access_tool
from app.permissions.services import current_user_can
from app.tools.forms import ToolForm, ToolLookupForm, ToolReferencePhotoForm
from app.tools.repositories import (
    base_tool_query,
    get_tool_by_any_identifier,
    get_tool_by_id,
)
from app.tools.services import (
    create_tool,
    delete_reference_photo,
    get_reference_photo_path,
    save_reference_photo,
    set_tool_active,
    update_tool,
)

bp = Blueprint("tools", __name__, url_prefix="/admin/tools")


def _configure_choices(form: ToolForm) -> None:
    categories = list_active_categories()
    form.id_categoria.choices = [
        (category.id_categoria, category.nome) for category in categories
    ]


def _form_data(form: ToolForm) -> dict:
    return {
        "codigo_interno": form.codigo_interno.data,
        "nome": form.nome.data,
        "descricao": form.descricao.data,
        "id_categoria": form.id_categoria.data,
        "status": form.status.data,
        "criticidade": form.criticidade.data,
        "ativo_imobilizado": form.ativo_imobilizado.data,
        "numero_serie": form.numero_serie.data,
        "marca": form.marca.data,
        "modelo": form.modelo.data,
        "controle_individual": form.controle_individual.data,
        "requer_calibracao": form.requer_calibracao.data,
        "ativo": form.ativo.data,
        "observacoes": form.observacoes.data,
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
@permission_required("tools.view")
def index():
    page = clamp_page(request.args.get("page"))
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    category_id_raw = request.args.get("categoria", "").strip()
    category_id = int(category_id_raw) if category_id_raw.isdigit() else None
    result = paginate(
        base_tool_query(search, status, category_id, user=current_user),
        page=page,
        per_page=15,
    )
    return render_template(
        "tools/index.html",
        page=result,
        search=search,
        status=status,
        category_id=category_id,
        categories=list_active_categories_for_tool_scope(current_user),
        statuses=ToolStatus.choices(),
    )


@bp.route("/new", methods=["GET", "POST"])
@permission_required("tools.create")
def create():
    form = ToolForm(
        ativo=True, controle_individual=True, status=ToolStatus.DISPONIVEL.value
    )
    _configure_choices(form)
    if not form.id_categoria.choices:
        flash(
            "Cadastre ao menos uma categoria ativa antes de criar ferramentas.",
            "warning",
        )
    if form.validate_on_submit():
        try:
            tool = create_tool(_form_data(form))
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Ferramenta criada com sucesso.", "success")
            return redirect(url_for("tools.edit", tool_id=tool.id_tool))
    return render_template("tools/form.html", form=form, tool=None, photo_form=None)


@bp.route("/<int:tool_id>/edit", methods=["GET", "POST"])
@permission_required("tools.update")
def edit(tool_id: int):
    tool = get_tool_by_id(tool_id)
    if not tool or tool.is_deleted:
        flash("Ferramenta não encontrada.", "warning")
        return redirect(url_for("tools.index"))
    if not _ensure_tool_in_scope(tool):
        return redirect(url_for("tools.index"))
    form = ToolForm(obj=tool)
    _configure_choices(form)
    if form.validate_on_submit():
        try:
            update_tool(
                tool,
                _form_data(form),
                can_critical_update=current_user_can("tools.critical_update"),
            )
        except PermissionError as exc:
            flash(str(exc), "danger")
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Ferramenta atualizada com sucesso.", "success")
            return redirect(url_for("tools.edit", tool_id=tool.id_tool))
    return render_template(
        "tools/form.html",
        form=form,
        tool=tool,
        photo_form=ToolReferencePhotoForm(),
    )


@bp.post("/<int:tool_id>/deactivate")
@permission_required("tools.deactivate")
def deactivate(tool_id: int):
    tool = get_tool_by_id(tool_id)
    reason = request.form.get("motivo", "").strip()
    if tool and not _ensure_tool_in_scope(tool):
        return redirect(url_for("tools.index"))
    if tool:
        try:
            set_tool_active(tool, False, reason)
            flash("Ferramenta inativada.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("tools.index"))


@bp.post("/<int:tool_id>/activate")
@permission_required("tools.deactivate")
def activate(tool_id: int):
    tool = get_tool_by_id(tool_id)
    reason = request.form.get("motivo", "Reativação administrativa.").strip()
    if tool and not _ensure_tool_in_scope(tool):
        return redirect(url_for("tools.index"))
    if tool:
        try:
            set_tool_active(tool, True, reason)
            flash("Ferramenta ativada.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    return redirect(url_for("tools.index"))


@bp.route("/lookup", methods=["GET", "POST"])
@permission_required("tools.view")
def lookup():
    form = ToolLookupForm()
    tool = None
    code = request.values.get("codigo") or request.values.get("code") or ""
    if request.method == "POST" and form.validate_on_submit():
        code = form.codigo.data
    if code:
        tool = get_tool_by_any_identifier(code, user=current_user)
        if not tool:
            flash(
                "Nenhuma ferramenta encontrada para o identificador informado.",
                "warning",
            )
    return render_template("tools/lookup.html", form=form, tool=tool, code=code.strip())


@bp.get("/<int:tool_id>/reference-photo")
@permission_required("tools.view")
def reference_photo(tool_id: int):
    tool = get_tool_by_id(tool_id)
    if not tool or tool.is_deleted:
        flash("Ferramenta não encontrada.", "warning")
        return redirect(url_for("tools.index"))
    if not _ensure_tool_in_scope(tool):
        return redirect(url_for("tools.index"))
    path = get_reference_photo_path(tool)
    if not path:
        flash("Ferramenta não possui foto de referência cadastrada.", "warning")
        return redirect(url_for("tools.edit", tool_id=tool.id_tool))
    record_audit_log(
        action="tools.reference_photo.download",
        entity="tool",
        entity_id=tool.id_tool,
        after={"filename": tool.referencia_foto_filename},
        reason="Download de foto de referência.",
        commit=True,
    )
    return send_file(path, mimetype=tool.referencia_foto_content_type or "image/jpeg")


@bp.post("/<int:tool_id>/reference-photo")
@permission_required("tools.update")
def upload_reference_photo(tool_id: int):
    tool = get_tool_by_id(tool_id)
    if not tool or tool.is_deleted:
        flash("Ferramenta não encontrada.", "warning")
        return redirect(url_for("tools.index"))
    if not _ensure_tool_in_scope(tool):
        return redirect(url_for("tools.index"))
    form = ToolReferencePhotoForm()
    if form.validate_on_submit():
        try:
            save_reference_photo(tool, request.files.get("foto"), form.motivo.data)
        except ValueError as exc:
            flash(str(exc), "danger")
        else:
            flash("Foto de referência atualizada.", "success")
    else:
        flash("Não foi possível validar o envio da foto.", "danger")
    return redirect(url_for("tools.edit", tool_id=tool.id_tool))


@bp.post("/<int:tool_id>/reference-photo/delete")
@permission_required("tools.update")
def remove_reference_photo(tool_id: int):
    tool = get_tool_by_id(tool_id)
    reason = request.form.get("motivo", "").strip()
    if not tool or tool.is_deleted:
        flash("Ferramenta não encontrada.", "warning")
        return redirect(url_for("tools.index"))
    if not _ensure_tool_in_scope(tool):
        return redirect(url_for("tools.index"))
    try:
        delete_reference_photo(tool, reason)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        flash("Foto de referência removida.", "success")
    return redirect(url_for("tools.edit", tool_id=tool.id_tool))


@bp.get("/<int:tool_id>/qr.svg")
@permission_required("tools.view")
def qr_svg(tool_id: int):
    tool = get_tool_by_id(tool_id)
    if not tool or tool.is_deleted:
        flash("Ferramenta não encontrada.", "warning")
        return redirect(url_for("tools.index"))
    if not _ensure_tool_in_scope(tool):
        return redirect(url_for("tools.index"))
    lookup_url = url_for("tools.lookup", code=tool.codigo_interno, _external=True)
    image = qrcode.make(lookup_url, image_factory=SvgPathImage)
    stream = BytesIO()
    image.save(stream)
    return Response(stream.getvalue(), mimetype="image/svg+xml")


@bp.get("/<int:tool_id>/label")
@permission_required("tools.view")
def qr_label(tool_id: int):
    tool = get_tool_by_id(tool_id)
    if not tool or tool.is_deleted:
        flash("Ferramenta não encontrada.", "warning")
        return redirect(url_for("tools.index"))
    if not _ensure_tool_in_scope(tool):
        return redirect(url_for("tools.index"))
    return render_template("tools/label.html", tool=tool)
