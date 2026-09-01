from __future__ import annotations

import os
from urllib.parse import unquote

import click
from flask import Flask, current_app
from sqlalchemy import text

from app.extensions import db


def _safe_database_uri(uri: str) -> str:
    sanitized = uri
    decoded = unquote(sanitized)
    env_password = os.getenv("SQLSERVER_PASSWORD")
    if env_password:
        decoded = decoded.replace(env_password, "***")
    return decoded


@click.command("db-ping")
def db_ping_command() -> None:
    # Validação da conexão com o banco de dados
    try:
        with db.engine.connect() as connection:
            value = connection.execute(text("SELECT 1")).scalar_one()
    except Exception as exc:
        raise click.ClickException(f"Falha ao conectar no banco: {exc}") from exc

    click.echo(f"Banco respondeu com sucesso: {value}")


@click.command("db-info")
def db_info_command() -> None:
    # Mostra detalhes não sensíveis da configuração do banco de dados
    engine = db.engine
    click.echo(f"Dialect: {engine.dialect.name}")
    click.echo(f"Driver: {engine.dialect.driver}")
    click.echo(
        f"URL: {_safe_database_uri(current_app.config['SQLALCHEMY_DATABASE_URI'])}"
    )


def register_db_commands(app: Flask) -> None:
    app.cli.add_command(db_ping_command)
    app.cli.add_command(db_info_command)
