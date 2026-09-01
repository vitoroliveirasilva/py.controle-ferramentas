from __future__ import annotations

import importlib
from pathlib import Path

from flask import Flask

from app.audit.routes import bp as audit_bp
from app.auth.routes import bp as auth_bp
from app.auth.routes import register_microsoft_callback_route
from app.auth.services import configure_login_manager
from app.categories.routes import bp as categories_bp
from app.config import get_config, validate_runtime_config
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.security import register_security_headers
from app.custody.routes import bp as custody_bp
from app.dashboard.routes import bp as dashboard_bp
from app.db.cli import register_db_commands
from app.extensions import csrf, db, login_manager, migrate
from app.health.routes import bp as health_bp
from app.inventories.routes import bp as inventories_bp
from app.locations.routes import bp as locations_bp
from app.main.routes import bp as main_bp
from app.notifications.cli import register_notification_commands
from app.notifications.routes import bp as notifications_bp
from app.occurrences.routes import bp as occurrences_bp
from app.permissions.cli import register_permission_commands
from app.permissions.routes import bp as permissions_bp
from app.reports.routes import bp as reports_bp
from app.signatures.routes import bp as signatures_bp
from app.tools.routes import bp as tools_bp
from app.transfers.routes import bp as transfers_bp
from app.users.cli import register_user_commands
from app.users.routes import bp as users_bp


# Criação e configuração da aplicação Flask
def create_app(
    config_name: str | None = None, config_overrides: dict | None = None
) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.from_object(get_config(config_name))

    if config_overrides:
        app.config.update(config_overrides)

    validate_runtime_config(app)
    configure_logging(app)
    register_extensions(app)
    register_blueprints(app)
    register_cli(app)
    register_template_context(app)
    register_security_headers(app)
    register_error_handlers(app)

    app.logger.info("Aplicação inicializada no ambiente %s", app.config["APP_ENV"])
    return app


# Registro de extensões, blueprints e outros componentes da aplicação
def register_extensions(app: Flask) -> None:
    csrf.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    configure_login_manager(app)

    # Importa os models para que o Flask-Migrate detecte as tabelas nas migrations.
    importlib.import_module("app.models")
    importlib.import_module("app.audit.models")
    importlib.import_module("app.categories.models")
    importlib.import_module("app.custody.models")
    importlib.import_module("app.inventories.models")
    importlib.import_module("app.locations.models")
    importlib.import_module("app.occurrences.models")
    importlib.import_module("app.notifications.models")
    importlib.import_module("app.permissions.models")
    importlib.import_module("app.reports")
    importlib.import_module("app.signatures.models")
    importlib.import_module("app.tools.models")
    importlib.import_module("app.transfers.models")
    importlib.import_module("app.users.models")

    migrate.init_app(app, db, render_as_batch=False, compare_type=True)


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    register_microsoft_callback_route(app)
    app.register_blueprint(permissions_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(locations_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(custody_bp)
    app.register_blueprint(transfers_bp)
    app.register_blueprint(inventories_bp)
    app.register_blueprint(occurrences_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(signatures_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(reports_bp)


def register_cli(app: Flask) -> None:
    register_db_commands(app)
    register_user_commands(app)
    register_permission_commands(app)
    register_notification_commands(app)


def register_template_context(app: Flask) -> None:
    @app.context_processor
    def inject_app_context() -> dict:
        from app.permissions.services import (
            current_user_any_permission,
            current_user_can,
        )

        return {
            "project_name": app.config["PROJECT_NAME"],
            "app_version": app.config["APP_VERSION"],
            "app_env": app.config["APP_ENV"],
            "can": current_user_can,
            "can_any": current_user_any_permission,
        }
