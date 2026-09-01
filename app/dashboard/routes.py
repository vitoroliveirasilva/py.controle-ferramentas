from __future__ import annotations

from flask import Blueprint, jsonify, render_template, url_for

from app.dashboard.services import build_dashboard_data
from app.permissions.decorators import permission_required

bp = Blueprint("dashboard", __name__, url_prefix="/admin/dashboard")


def _card_url(endpoint: str | None) -> str | None:
    if not endpoint:
        return None
    try:
        return url_for(endpoint)
    except Exception:
        return None


@bp.get("/")
@permission_required("dashboard.view")
def index():
    dashboard = build_dashboard_data()
    return render_template(
        "dashboard/index.html",
        dashboard=dashboard,
        card_url=_card_url,
    )


@bp.get("/data")
@permission_required("dashboard.view")
def data():
    dashboard = build_dashboard_data()
    return jsonify(
        {
            "cards": [
                {
                    "title": card.title,
                    "value": card.value,
                    "description": card.description,
                    "level": card.level,
                    "url": _card_url(card.url),
                }
                for card in dashboard.cards
            ],
            "tools_by_status": dashboard.tools_by_status,
            "tools_by_criticality": dashboard.tools_by_criticality,
            "top_reincidences": dashboard.top_reincidences,
            "transfer_age_buckets": dashboard.transfer_age_buckets,
            "scope": dashboard.scope_description,
        }
    )
