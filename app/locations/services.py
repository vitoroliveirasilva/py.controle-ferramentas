from __future__ import annotations

from typing import Any

from app.audit.services import record_audit_log
from app.extensions import db
from app.locations.models import LocationModel
from app.locations.repositories import get_location_by_code, normalize_code

CRITICAL_FIELDS = {"codigo", "tipo_local", "filial", "departamento", "ativo"}


def _snapshot(location: LocationModel) -> dict[str, Any]:
    return location.to_dict()


def _clean(value: str | None) -> str | None:
    return (value or "").strip() or None


def _apply(location: LocationModel, data: dict[str, Any]) -> None:
    location.codigo = normalize_code(data["codigo"])
    location.nome = data["nome"].strip()
    location.tipo_local = data["tipo_local"]
    location.filial = _clean(data.get("filial"))
    location.departamento = _clean(data.get("departamento"))
    location.responsavel_nome = _clean(data.get("responsavel_nome"))
    location.endereco = _clean(data.get("endereco"))
    location.observacoes = _clean(data.get("observacoes"))
    location.ativo = bool(data.get("ativo"))


def create_location(data: dict[str, Any]) -> LocationModel:
    code = normalize_code(data["codigo"])
    if get_location_by_code(code):
        raise ValueError(f"Já existe local com o código {code}.")

    location = LocationModel(codigo=code, nome="", tipo_local=data["tipo_local"])
    _apply(location, data)
    db.session.add(location)
    db.session.flush()
    record_audit_log(
        action="locations.create",
        entity="location",
        entity_id=location.id_location,
        after=_snapshot(location),
        reason=data.get("motivo") or "Criação de local.",
    )
    db.session.commit()
    return location


def update_location(location: LocationModel, data: dict[str, Any]) -> LocationModel:
    code = normalize_code(data["codigo"])
    existing = get_location_by_code(code)
    if existing and existing.id_location != location.id_location:
        raise ValueError(f"Já existe local com o código {code}.")

    before = _snapshot(location)
    changed_critical = any(
        before.get(field) != data.get(field) for field in CRITICAL_FIELDS
    )
    if changed_critical and not (data.get("motivo") or "").strip():
        raise ValueError("Informe o motivo para alterar campos críticos do local.")

    _apply(location, data)
    db.session.flush()
    record_audit_log(
        action="locations.update",
        entity="location",
        entity_id=location.id_location,
        before=before,
        after=_snapshot(location),
        reason=data.get("motivo"),
    )
    db.session.commit()
    return location


def set_location_active(location: LocationModel, active: bool, reason: str) -> None:
    if not reason.strip():
        raise ValueError("Informe o motivo da alteração de status.")
    before = _snapshot(location)
    location.ativo = active
    record_audit_log(
        action="locations.activate" if active else "locations.deactivate",
        entity="location",
        entity_id=location.id_location,
        before=before,
        after=_snapshot(location),
        reason=reason,
    )
    db.session.commit()
