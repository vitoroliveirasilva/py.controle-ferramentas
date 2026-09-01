from __future__ import annotations

from app.audit.services import record_audit_log
from app.extensions import db
from app.permissions.services import assign_role_to_user
from app.users.repositories import create_user


def _login(client, email: str, name: str = "Audit Admin"):
    return client.post(
        "/auth/login",
        data={"email": email, "nome": name, "microsoft_oid": f"oid-{email}"},
        follow_redirects=True,
    )


def test_admin_can_open_audit_logs(app, client):
    with app.app_context():
        user = create_user(email="audit-admin@brasif.com.br", nome="Audit Admin")
        db.session.commit()
        assign_role_to_user(user.email_lower, "admin_sistema")
        record_audit_log(
            action="audit.test",
            entity="test",
            entity_id="1",
            after={"message": "ok"},
            commit=True,
        )

    _login(client, user.email, user.nome)

    response = client.get("/admin/audit/")

    assert response.status_code == 200
    assert "Logs de auditoria" in response.get_data(as_text=True)
    assert "audit.test" in response.get_data(as_text=True)
