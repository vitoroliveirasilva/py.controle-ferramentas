from __future__ import annotations

from io import BytesIO
from urllib.parse import urlencode

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

from app.categories.repositories import list_active_categories_for_tool_scope
from app.models.enums import (
    InventoryStatus,
    InventoryType,
    OccurrenceStatus,
    OccurrenceType,
    ToolStatus,
    TransferStatus,
)
from app.permissions.decorators import permission_required
from app.reports.exporters import rows_to_csv, rows_to_xlsx
from app.reports.services import (
    build_report_rows,
    enforce_report_export_limit,
    record_report_export,
    report_definitions,
)

bp = Blueprint("reports", __name__, url_prefix="/admin/reports")


_FILTER_KEYS = ("q", "status", "tipo", "categoria")


def _filters() -> dict[str, str]:
    return {key: request.args.get(key, "").strip() for key in _FILTER_KEYS}


def _filter_query(filters: dict[str, str]) -> str:
    return urlencode({key: value for key, value in filters.items() if value})


@bp.get("/")
@permission_required("reports.view")
def index():
    return render_template("reports/index.html", reports=report_definitions().values())


@bp.get("/<report_code>")
@permission_required("reports.view")
def show(report_code: str):
    filters = _filters()
    try:
        definition, rows = build_report_rows(report_code, filters, user=current_user)
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("reports.index"))

    return render_template(
        "reports/report.html",
        definition=definition,
        rows=rows[:200],
        total=len(rows),
        filters=filters,
        filter_query=_filter_query(filters),
        categories=list_active_categories_for_tool_scope(current_user),
        tool_statuses=ToolStatus.choices(),
        inventory_statuses=InventoryStatus.choices(),
        inventory_types=InventoryType.choices(),
        transfer_statuses=TransferStatus.choices(),
        occurrence_statuses=OccurrenceStatus.choices(),
        occurrence_types=OccurrenceType.choices(),
    )


@bp.get("/<report_code>/print")
@permission_required("reports.view")
def print_view(report_code: str):
    filters = _filters()
    try:
        definition, rows = build_report_rows(report_code, filters, user=current_user)
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("reports.index"))
    return render_template(
        "reports/print.html",
        definition=definition,
        rows=rows,
        filters=filters,
    )


@bp.get("/<report_code>/export/<export_format>")
@permission_required("reports.export")
def export(report_code: str, export_format: str):
    filters = _filters()
    try:
        definition, rows = build_report_rows(report_code, filters, user=current_user)
    except ValueError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("reports.index"))

    try:
        enforce_report_export_limit(len(rows))
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("reports.show", report_code=report_code, **filters))

    if export_format == "csv":
        payload = rows_to_csv(rows)
        record_report_export(report_code, "csv", len(rows), filters)
        return Response(
            payload,
            mimetype="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename={report_code}.csv",
            },
        )

    if export_format == "xlsx":
        payload = rows_to_xlsx(rows, sheet_name=definition.title)
        record_report_export(report_code, "xlsx", len(rows), filters)
        return send_file(
            BytesIO(payload),
            as_attachment=True,
            download_name=f"{report_code}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    flash("Formato de exportação não suportado.", "warning")
    return redirect(url_for("reports.show", report_code=report_code, **filters))
