from __future__ import annotations

import click
from flask import Flask

from app.extensions import db
from app.users.models import UserModel
from app.users.services import create_local_user, set_user_status


@click.command("user-create")
@click.option("--email", required=True, help="E-mail corporativo do usuário.")
@click.option("--name", "nome", required=True, help="Nome de exibição do usuário.")
@click.option(
    "--microsoft-oid", default=None, help="Object ID do usuário no Microsoft Entra ID."
)
@click.option("--inactive", is_flag=True, help="Cria o usuário como inativo.")
@click.option("--blocked", is_flag=True, help="Cria o usuário como bloqueado.")
@click.option(
    "--notes", "observacoes", default=None, help="Observações administrativas."
)
def user_create_command(
    email: str,
    nome: str,
    microsoft_oid: str | None,
    inactive: bool,
    blocked: bool,
    observacoes: str | None,
) -> None:
    # Cria o usuário local e trata erros de validação (e.g. e-mail já existe)
    try:
        user = create_local_user(
            email=email,
            nome=nome,
            microsoft_oid=microsoft_oid,
            ativo=not inactive,
            bloqueado=blocked,
            observacoes=observacoes,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Usuário criado: {user.id_usuario} - {user.email_lower}")


@click.command("user-list")
def user_list_command() -> None:
    # Listagem simples de usuários locais, mostrando apenas informações básicas
    users = (
        db.session.execute(db.select(UserModel).order_by(UserModel.email_lower))
        .scalars()
        .all()
    )
    if not users:
        click.echo("Nenhum usuário local cadastrado.")
        return

    for user in users:
        status = "ativo" if user.ativo else "inativo"
        lock = "bloqueado" if user.bloqueado else "liberado"
        has_oid = "com_oid" if user.microsoft_oid else "sem_oid"
        click.echo(
            f"{user.id_usuario} | {user.email_lower} | {user.nome} | {status} | {lock} | {has_oid}"
        )


@click.command("user-activate")
@click.option("--email", required=True, help="E-mail do usuário.")
def user_activate_command(email: str) -> None:
    user = set_user_status(email=email, ativo=True)
    click.echo(f"Usuário ativado: {user.email_lower}")


@click.command("user-deactivate")
@click.option("--email", required=True, help="E-mail do usuário.")
def user_deactivate_command(email: str) -> None:
    user = set_user_status(email=email, ativo=False)
    click.echo(f"Usuário inativado: {user.email_lower}")


@click.command("user-block")
@click.option("--email", required=True, help="E-mail do usuário.")
@click.option("--reason", required=True, help="Motivo do bloqueio.")
def user_block_command(email: str, reason: str) -> None:
    user = set_user_status(email=email, bloqueado=True, bloqueio_motivo=reason)
    click.echo(f"Usuário bloqueado: {user.email_lower} - motivo: {reason}")


@click.command("user-unblock")
@click.option("--email", required=True, help="E-mail do usuário.")
def user_unblock_command(email: str) -> None:
    user = set_user_status(email=email, bloqueado=False)
    click.echo(f"Usuário desbloqueado: {user.email_lower}")


def register_user_commands(app: Flask) -> None:
    app.cli.add_command(user_create_command)
    app.cli.add_command(user_list_command)
    app.cli.add_command(user_activate_command)
    app.cli.add_command(user_deactivate_command)
    app.cli.add_command(user_block_command)
    app.cli.add_command(user_unblock_command)
