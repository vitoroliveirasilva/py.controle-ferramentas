from __future__ import annotations

import click
from flask import Flask

from app.extensions import db
from app.permissions.models import RoleModel, UserRoleModel, UserScopeModel
from app.permissions.repositories import list_roles
from app.permissions.services import (
    assign_role_to_user,
    assign_scope_to_user,
    revoke_role_from_user,
    revoke_scope_from_user,
    seed_permissions_and_roles,
)
from app.users.repositories import get_user_by_email


@click.command("access-seed")
def access_seed_command() -> None:
    try:
        summary = seed_permissions_and_roles()
    except Exception as exc:
        db.session.rollback()
        raise click.ClickException(f"Falha ao aplicar seed de acessos: {exc}") from exc

    click.echo(
        "Seed de acessos aplicado: "
        f"{summary.roles_count} perfis, "
        f"{summary.permissions_count} permissões, "
        f"{summary.role_permissions_count} vínculos perfil-permissão."
    )


@click.command("access-list-roles")
def access_list_roles_command() -> None:
    roles = list_roles()
    if not roles:
        click.echo("Nenhum perfil cadastrado. Rode access-seed.")
        return

    for role in roles:
        status = "ativo" if role.ativo else "inativo"
        click.echo(f"{role.codigo} | {role.nome} | {status}")


@click.command("user-grant-role")
@click.option("--email", required=True, help="E-mail do usuário local.")
@click.option("--role", "role_code", required=True, help="Código do perfil.")
def user_grant_role_command(email: str, role_code: str) -> None:
    try:
        assignment = assign_role_to_user(email=email, role_code=role_code)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Perfil atribuído: usuario={assignment.id_usuario} role={role_code}")


@click.command("user-revoke-role")
@click.option("--email", required=True, help="E-mail do usuário local.")
@click.option("--role", "role_code", required=True, help="Código do perfil.")
def user_revoke_role_command(email: str, role_code: str) -> None:
    removed = revoke_role_from_user(email=email, role_code=role_code)
    if not removed:
        raise click.ClickException("Vínculo usuário-perfil não encontrado.")
    click.echo(f"Perfil removido: {email} -> {role_code}")


@click.command("user-grant-scope")
@click.option("--email", required=True, help="E-mail do usuário local.")
@click.option(
    "--scope-type", required=True, help="Tipo: global, filial, local, tecnico etc."
)
@click.option(
    "--scope-value",
    default="*",
    help="Valor do escopo. Use * para acesso amplo no tipo.",
)
@click.option("--description", default=None, help="Descrição administrativa do escopo.")
def user_grant_scope_command(
    email: str,
    scope_type: str,
    scope_value: str,
    description: str | None,
) -> None:
    try:
        scope = assign_scope_to_user(
            email=email,
            scope_type=scope_type,
            scope_value=scope_value,
            description=description,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Escopo atribuído: {email} -> {scope.tipo_escopo}:{scope.valor_escopo}")


@click.command("user-revoke-scope")
@click.option("--email", required=True, help="E-mail do usuário local.")
@click.option("--scope-type", required=True, help="Tipo do escopo.")
@click.option("--scope-value", default="*", help="Valor do escopo.")
def user_revoke_scope_command(email: str, scope_type: str, scope_value: str) -> None:
    removed = revoke_scope_from_user(
        email=email, scope_type=scope_type, scope_value=scope_value
    )
    if not removed:
        raise click.ClickException("Escopo não encontrado para o usuário.")
    click.echo(f"Escopo removido: {email} -> {scope_type}:{scope_value}")


@click.command("access-list-user")
@click.option("--email", required=True, help="E-mail do usuário local.")
def access_list_user_command(email: str) -> None:
    user = get_user_by_email(email)
    if not user:
        raise click.ClickException(f"Usuário não encontrado: {email}")

    click.echo(f"Usuário: {user.email_lower} - {user.nome}")
    assignments = db.session.execute(
        db.select(RoleModel.codigo, RoleModel.nome)
        .join(UserRoleModel, UserRoleModel.id_role == RoleModel.id_role)
        .where(UserRoleModel.id_usuario == user.id_usuario)
        .order_by(RoleModel.codigo)
    ).all()
    scopes = db.session.execute(
        db.select(UserScopeModel.tipo_escopo, UserScopeModel.valor_escopo)
        .where(UserScopeModel.id_usuario == user.id_usuario)
        .order_by(UserScopeModel.tipo_escopo, UserScopeModel.valor_escopo)
    ).all()

    click.echo("Perfis:")
    if not assignments:
        click.echo("  nenhum")
    for role_code, role_name in assignments:
        click.echo(f"  {role_code} - {role_name}")

    click.echo("Escopos:")
    if not scopes:
        click.echo("  nenhum")
    for scope_type, scope_value in scopes:
        click.echo(f"  {scope_type}:{scope_value}")


def register_permission_commands(app: Flask) -> None:
    app.cli.add_command(access_seed_command)
    app.cli.add_command(access_list_roles_command)
    app.cli.add_command(user_grant_role_command)
    app.cli.add_command(user_revoke_role_command)
    app.cli.add_command(user_grant_scope_command)
    app.cli.add_command(user_revoke_scope_command)
    app.cli.add_command(access_list_user_command)
