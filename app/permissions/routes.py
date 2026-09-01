from __future__ import annotations

from flask import Blueprint, jsonify, render_template

from app.permissions.decorators import permission_required
from app.permissions.services import (
    get_access_matrix,
    get_user_permission_codes,
    get_user_scopes,
)

bp = Blueprint("permissions", __name__, url_prefix="/admin/access")


@bp.get("/")
@permission_required("roles.view")
def index():
    return render_template("permissions/index.html", **get_access_matrix())


@bp.get("/matrix.json")
@permission_required("roles.view")
def matrix_json():
    matrix = get_access_matrix()
    roles = matrix["roles"]
    groups = matrix["permissions_by_group"]
    return jsonify(
        {
            "roles": [
                {
                    "codigo": role.codigo,
                    "nome": role.nome,
                    "ativo": role.ativo,
                    "permissions": [
                        link.permission.codigo for link in role.permissions
                    ],
                }
                for role in roles
            ],
            "permissions_by_group": {
                group: [permission.codigo for permission in permissions]
                for group, permissions in groups.items()
            },
        }
    )


@bp.get("/me")
@permission_required("dashboard.view")
def my_access():
    from flask_login import current_user

    scopes = get_user_scopes(current_user)
    return jsonify(
        {
            "email": current_user.email_lower,
            "permissions": sorted(get_user_permission_codes(current_user)),
            "scopes": [
                {
                    "tipo_escopo": scope.tipo_escopo,
                    "valor_escopo": scope.valor_escopo,
                    "descricao": scope.descricao,
                }
                for scope in scopes
            ],
        }
    )
