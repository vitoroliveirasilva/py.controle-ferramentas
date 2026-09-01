from __future__ import annotations

from typing import Any

from app.audit.services import record_audit_log
from app.categories.models import ToolCategoryModel
from app.categories.repositories import get_category_by_code, normalize_code
from app.extensions import db

CRITICAL_FIELDS = {
    "codigo",
    "controle_individual_padrao",
    "requer_numero_serie",
    "requer_calibracao",
    "ativo",
}


def _snapshot(category: ToolCategoryModel) -> dict[str, Any]:
    return category.to_dict()


def _apply(category: ToolCategoryModel, data: dict[str, Any]) -> None:
    category.codigo = normalize_code(data["codigo"])
    category.nome = data["nome"].strip()
    category.descricao = (data.get("descricao") or "").strip() or None
    category.ativo = bool(data.get("ativo"))
    category.controle_individual_padrao = bool(data.get("controle_individual_padrao"))
    category.requer_numero_serie = bool(data.get("requer_numero_serie"))
    category.requer_calibracao = bool(data.get("requer_calibracao"))


def create_category(data: dict[str, Any]) -> ToolCategoryModel:
    code = normalize_code(data["codigo"])
    if get_category_by_code(code):
        raise ValueError(f"Já existe categoria com o código {code}.")

    category = ToolCategoryModel(codigo=code, nome="")
    _apply(category, data)
    db.session.add(category)
    db.session.flush()
    record_audit_log(
        action="categories.create",
        entity="tool_category",
        entity_id=category.id_categoria,
        after=_snapshot(category),
        reason=data.get("motivo") or "Criação de categoria.",
    )
    db.session.commit()
    return category


def update_category(
    category: ToolCategoryModel, data: dict[str, Any]
) -> ToolCategoryModel:
    code = normalize_code(data["codigo"])
    existing = get_category_by_code(code)
    if existing and existing.id_categoria != category.id_categoria:
        raise ValueError(f"Já existe categoria com o código {code}.")

    before = _snapshot(category)
    changed_critical = any(
        before.get(field) != data.get(field) for field in CRITICAL_FIELDS
    )
    if changed_critical and not (data.get("motivo") or "").strip():
        raise ValueError("Informe o motivo para alterar campos críticos da categoria.")

    _apply(category, data)
    db.session.flush()
    record_audit_log(
        action="categories.update",
        entity="tool_category",
        entity_id=category.id_categoria,
        before=before,
        after=_snapshot(category),
        reason=data.get("motivo"),
    )
    db.session.commit()
    return category


def set_category_active(category: ToolCategoryModel, active: bool, reason: str) -> None:
    if not reason.strip():
        raise ValueError("Informe o motivo da alteração de status.")
    before = _snapshot(category)
    category.ativo = active
    record_audit_log(
        action="categories.activate" if active else "categories.deactivate",
        entity="tool_category",
        entity_id=category.id_categoria,
        before=before,
        after=_snapshot(category),
        reason=reason,
    )
    db.session.commit()
