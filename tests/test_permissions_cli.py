from __future__ import annotations

from app.extensions import db
from app.users.repositories import create_user


def test_access_seed_command(app):
    runner = app.test_cli_runner()

    result = runner.invoke(args=["access-seed"])

    assert result.exit_code == 0
    assert "Seed de acessos aplicado" in result.output


def test_user_grant_role_command(app):
    with app.app_context():
        create_user(email="cli-role@brasif.com.br", nome="Cli Role")
        db.session.commit()

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "user-grant-role",
            "--email",
            "cli-role@brasif.com.br",
            "--role",
            "tecnico",
        ]
    )

    assert result.exit_code == 0
    assert "Perfil atribuído" in result.output


def test_user_grant_scope_command(app):
    with app.app_context():
        create_user(email="cli-scope@brasif.com.br", nome="Cli Scope")
        db.session.commit()

    runner = app.test_cli_runner()
    result = runner.invoke(
        args=[
            "user-grant-scope",
            "--email",
            "cli-scope@brasif.com.br",
            "--scope-type",
            "filial",
            "--scope-value",
            "jundiai",
        ]
    )

    assert result.exit_code == 0
    assert "Escopo atribuído" in result.output
