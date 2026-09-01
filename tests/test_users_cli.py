from __future__ import annotations

from app.extensions import db
from app.users.models import UserModel


def test_user_create_cli_creates_local_user(app):
    runner = app.test_cli_runner()

    result = runner.invoke(
        args=[
            "user-create",
            "--email",
            "Vitor.Silva@brasif.com.br",
            "--name",
            "Vitor Silva",
        ]
    )

    assert result.exit_code == 0
    assert "vitor.silva@brasif.com.br" in result.output

    user = db.session.execute(
        db.select(UserModel).where(UserModel.email_lower == "vitor.silva@brasif.com.br")
    ).scalar_one()

    assert user.nome == "Vitor Silva"
    assert user.ativo is True
    assert user.bloqueado is False


def test_user_block_cli_blocks_user(app):
    runner = app.test_cli_runner()
    runner.invoke(
        args=["user-create", "--email", "user@brasif.com.br", "--name", "User"]
    )

    result = runner.invoke(
        args=["user-block", "--email", "user@brasif.com.br", "--reason", "Teste"]
    )

    assert result.exit_code == 0
    user = db.session.execute(
        db.select(UserModel).where(UserModel.email_lower == "user@brasif.com.br")
    ).scalar_one()
    assert user.bloqueado is True
    assert user.bloqueio_motivo == "Teste"
