from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv
from flask import Flask

from app.auth.redirects import normalize_microsoft_redirect_path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Variável {name} deve ser um número inteiro.") from exc


def _env_list(name: str, default: str = "") -> list[str]:
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"Variável {name} deve ser um número.") from exc


def _normalize_yes_no(value: str | None, default: str = "yes") -> str:
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    return "yes" if normalized in {"1", "true", "yes", "y", "on"} else "no"


def _build_sqlserver_uri_from_env() -> str | None:
    host = os.getenv("SQLSERVER_HOST")
    database = os.getenv("SQLSERVER_DATABASE")

    if not host or not database:
        return None

    driver = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
    port = os.getenv("SQLSERVER_PORT", "1433")
    username = os.getenv("SQLSERVER_USERNAME")
    password = os.getenv("SQLSERVER_PASSWORD")
    trusted_connection = _env_bool("SQLSERVER_TRUSTED_CONNECTION", False)
    encrypt = _normalize_yes_no(os.getenv("SQLSERVER_ENCRYPT"), "yes")
    trust_server_certificate = _normalize_yes_no(
        os.getenv("SQLSERVER_TRUST_SERVER_CERTIFICATE"),
        "yes",
    )
    timeout = _env_int("SQLSERVER_CONNECTION_TIMEOUT", 30)

    normalized_host = host.removeprefix("tcp:").strip()
    server = normalized_host if "," in normalized_host or not port else f"{normalized_host},{port}"
    parts = [
        f"DRIVER={{{driver}}}",
        f"SERVER={server}",
        f"DATABASE={database}",
        f"Encrypt={encrypt}",
        f"TrustServerCertificate={trust_server_certificate}",
        f"Connection Timeout={timeout}",
    ]

    if trusted_connection:
        parts.append("Trusted_Connection=yes")
    else:
        if not username or not password:
            raise RuntimeError(
                "Defina SQLSERVER_USERNAME e SQLSERVER_PASSWORD ou habilite "
                "SQLSERVER_TRUSTED_CONNECTION=1."
            )
        parts.extend([f"UID={username}", f"PWD={password}"])

    odbc_connect = ";".join(parts)
    return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_connect)}"


def _database_uri(app_env: str) -> str:
    explicit_uri = os.getenv("DATABASE_URL")
    if explicit_uri:
        return explicit_uri

    sqlserver_uri = _build_sqlserver_uri_from_env()
    if sqlserver_uri:
        return sqlserver_uri

    if app_env == "testing":
        return "sqlite:///:memory:"

    return f"sqlite:///{BASE_DIR / 'instance' / 'dev-controle-ferramentas.db'}"


def _engine_options(database_uri: str) -> dict:
    options = {
        "pool_pre_ping": True,
        "pool_recycle": _env_int("SQLALCHEMY_POOL_RECYCLE", 1800),
    }

    if database_uri.startswith("mssql+pyodbc"):
        options["fast_executemany"] = _env_bool("SQLSERVER_FAST_EXECUTEMANY", True)

    return options


class BaseConfig:
    PROJECT_NAME = os.getenv("PROJECT_NAME", "Sistema de Controle de Ferramentas")
    APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
    APP_ENV = os.getenv("APP_ENV", "development")

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    WTF_CSRF_ENABLED = _env_bool("WTF_CSRF_ENABLED", True)

    SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
    SERVER_PORT = _env_int("SERVER_PORT", 8000)

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    JSON_SORT_KEYS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", APP_ENV == "production")
    PERMANENT_SESSION_LIFETIME_MINUTES = _env_int("PERMANENT_SESSION_LIFETIME_MINUTES", 480)

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE

    MAX_CONTENT_LENGTH = _env_int("MAX_CONTENT_LENGTH_MB", 16) * 1024 * 1024
    FORCE_HTTPS_HEADERS = _env_bool("FORCE_HTTPS_HEADERS", APP_ENV == "production")
    APP_TRUST_PROXY_HEADERS = _env_bool("APP_TRUST_PROXY_HEADERS", False)

    UPLOAD_BASE_DIR = os.getenv("UPLOAD_BASE_DIR") or str(BASE_DIR / "instance" / "uploads")
    TOOL_REFERENCE_PHOTO_MAX_MB = _env_int("TOOL_REFERENCE_PHOTO_MAX_MB", 8)
    INVENTORY_EVIDENCE_MAX_MB = _env_int("INVENTORY_EVIDENCE_MAX_MB", 8)
    OCCURRENCE_ATTACHMENT_MAX_MB = _env_int("OCCURRENCE_ATTACHMENT_MAX_MB", 8)
    ALLOWED_IMAGE_EXTENSIONS = set(
        item.lower() for item in _env_list("ALLOWED_IMAGE_EXTENSIONS", "png,jpg,jpeg,webp")
    )
    ALLOWED_EVIDENCE_EXTENSIONS = set(
        item.lower() for item in _env_list("ALLOWED_EVIDENCE_EXTENSIONS", "pdf,png,jpg,jpeg,webp")
    )
    ALLOWED_OCCURRENCE_ATTACHMENT_EXTENSIONS = set(
        item.lower()
        for item in _env_list("ALLOWED_OCCURRENCE_ATTACHMENT_EXTENSIONS", "pdf,png,jpg,jpeg,webp")
    )

    SQLALCHEMY_DATABASE_URI = _database_uri(APP_ENV)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = _env_bool("SQLALCHEMY_ECHO", False)
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options(SQLALCHEMY_DATABASE_URI)

    AUTH_MICROSOFT_TENANT_ID = os.getenv("AUTH_MICROSOFT_TENANT_ID", "")
    AUTH_MICROSOFT_CLIENT_ID = os.getenv("AUTH_MICROSOFT_CLIENT_ID", "")
    AUTH_MICROSOFT_CLIENT_SECRET = os.getenv("AUTH_MICROSOFT_CLIENT_SECRET", "")
    AUTH_MICROSOFT_REDIRECT_URI = os.getenv("AUTH_MICROSOFT_REDIRECT_URI", "")
    AUTH_MICROSOFT_REDIRECT_PATH = os.getenv("AUTH_MICROSOFT_REDIRECT_PATH", "/auth/callback")
    AUTH_MICROSOFT_SCOPES = _env_list("AUTH_MICROSOFT_SCOPES", "openid,profile,email")
    AUTH_ALLOWED_EMAIL_DOMAINS = [
        domain.lower() for domain in _env_list("AUTH_ALLOWED_EMAIL_DOMAINS")
    ]
    AUTH_DEV_LOGIN_ENABLED = _env_bool("AUTH_DEV_LOGIN_ENABLED", False)

    BOOTSTRAP_CSS_URL = os.getenv(
        "BOOTSTRAP_CSS_URL",
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css",
    )
    BOOTSTRAP_JS_URL = os.getenv(
        "BOOTSTRAP_JS_URL",
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js",
    )

    NOTIFICATIONS_EMAIL_ENABLED = _env_bool("NOTIFICATIONS_EMAIL_ENABLED", False)
    BRASIF_GATEWAY_BASE_URL = os.getenv(
        "BRASIF_GATEWAY_BASE_URL", "https://howard.brasif.local"
    ).rstrip("/")
    BRASIF_GATEWAY_API_KEY = os.getenv("BRASIF_GATEWAY_API_KEY", "")
    BRASIF_GATEWAY_TIMEOUT_SECONDS = _env_int("BRASIF_GATEWAY_TIMEOUT_SECONDS", 10)
    BRASIF_GATEWAY_VERIFY_SSL = _env_bool("BRASIF_GATEWAY_VERIFY_SSL", True)
    BRASIF_GATEWAY_MAX_RETRIES = _env_int("BRASIF_GATEWAY_MAX_RETRIES", 2)
    BRASIF_GATEWAY_RETRY_BACKOFF_SECONDS = _env_float(
        "BRASIF_GATEWAY_RETRY_BACKOFF_SECONDS", 0.25
    )
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "")
    MAIL_MAX_RECIPIENTS = _env_int("MAIL_MAX_RECIPIENTS", 50)
    MAIL_MAX_BODY_LENGTH = _env_int("MAIL_MAX_BODY_LENGTH", 50000)
    MAIL_MAX_ATTACHMENT_MB = _env_int("MAIL_MAX_ATTACHMENT_MB", 10)

    REPORT_EXPORT_MAX_ROWS = _env_int("REPORT_EXPORT_MAX_ROWS", 500)
    TRANSFER_EXPIRATION_DAYS = _env_int("TRANSFER_EXPIRATION_DAYS", 7)


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False


class TestingConfig(BaseConfig):
    APP_ENV = "testing"
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SECRET_KEY = os.getenv("SECRET_KEY", "testing-secret-key")
    SERVER_HOST = "127.0.0.1"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    AUTH_DEV_LOGIN_ENABLED = True
    AUTH_MICROSOFT_TENANT_ID = "test-tenant"
    AUTH_MICROSOFT_CLIENT_ID = "test-client"
    AUTH_MICROSOFT_CLIENT_SECRET = "test-secret"


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    APP_ENV = "production"
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    FORCE_HTTPS_HEADERS = True
    AUTH_DEV_LOGIN_ENABLED = False


CONFIG_BY_NAME: dict[str, type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "dev": DevelopmentConfig,
    "testing": TestingConfig,
    "test": TestingConfig,
    "production": ProductionConfig,
    "prod": ProductionConfig,
}


def get_config(config_name: str | None = None) -> type[BaseConfig]:
    selected = config_name or os.getenv("APP_ENV", "development")
    return CONFIG_BY_NAME.get(selected.lower(), DevelopmentConfig)


def _validate_partial_microsoft_config(app: Flask) -> None:
    microsoft_values = {
        "AUTH_MICROSOFT_TENANT_ID": app.config.get("AUTH_MICROSOFT_TENANT_ID"),
        "AUTH_MICROSOFT_CLIENT_ID": app.config.get("AUTH_MICROSOFT_CLIENT_ID"),
        "AUTH_MICROSOFT_CLIENT_SECRET": app.config.get("AUTH_MICROSOFT_CLIENT_SECRET"),
    }
    configured = [name for name, value in microsoft_values.items() if value]
    if configured and len(configured) != len(microsoft_values):
        missing = sorted(name for name, value in microsoft_values.items() if not value)
        raise RuntimeError(
            "Configuração Microsoft incompleta. Defina também: " + ", ".join(missing)
        )


def _validate_microsoft_redirect_config(app: Flask) -> None:
    redirect_path = normalize_microsoft_redirect_path(
        app.config.get("AUTH_MICROSOFT_REDIRECT_PATH")
    )
    app.config["AUTH_MICROSOFT_REDIRECT_PATH"] = redirect_path

    redirect_uri = (app.config.get("AUTH_MICROSOFT_REDIRECT_URI") or "").strip()
    if not redirect_uri:
        return

    parsed = urlparse(redirect_uri)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(
            "AUTH_MICROSOFT_REDIRECT_URI deve ser uma URL absoluta http(s)."
        )

    if parsed.path.rstrip("/") != redirect_path.rstrip("/"):
        raise RuntimeError(
            "AUTH_MICROSOFT_REDIRECT_URI e AUTH_MICROSOFT_REDIRECT_PATH precisam apontar "
            "para o mesmo caminho de callback."
        )


def _validate_mail_config(app: Flask) -> None:
    if not app.config.get("NOTIFICATIONS_EMAIL_ENABLED"):
        return

    if not app.config.get("BRASIF_GATEWAY_API_KEY"):
        raise RuntimeError(
            "NOTIFICATIONS_EMAIL_ENABLED=1 exige BRASIF_GATEWAY_API_KEY configurada. "
            "O projeto não deve usar SMTP."
        )

    if app.config.get("MAIL_MAX_RECIPIENTS", 0) <= 0:
        raise RuntimeError("MAIL_MAX_RECIPIENTS deve ser maior que zero.")

    if app.config.get("MAIL_MAX_BODY_LENGTH", 0) <= 0:
        raise RuntimeError("MAIL_MAX_BODY_LENGTH deve ser maior que zero.")

    if app.config.get("MAIL_MAX_ATTACHMENT_MB", 0) <= 0:
        raise RuntimeError("MAIL_MAX_ATTACHMENT_MB deve ser maior que zero.")

    if app.config.get("BRASIF_GATEWAY_MAX_RETRIES", 0) < 0:
        raise RuntimeError("BRASIF_GATEWAY_MAX_RETRIES não pode ser negativo.")

    if app.config.get("BRASIF_GATEWAY_RETRY_BACKOFF_SECONDS", 0) < 0:
        raise RuntimeError("BRASIF_GATEWAY_RETRY_BACKOFF_SECONDS não pode ser negativo.")


def validate_runtime_config(app: Flask) -> None:
    is_production = app.config["APP_ENV"] == "production"
    weak_secret_keys = {"", "secret-key", "dev-only-change-me", "testing-secret-key"}

    if is_production and app.config["SECRET_KEY"] in weak_secret_keys:
        raise RuntimeError("Defina SECRET_KEY forte antes de executar em produção.")

    database_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if is_production and database_uri.startswith("sqlite"):
        raise RuntimeError(
            "Produção não pode usar SQLite. Configure SQL Server em DATABASE_URL."
        )

    if is_production and app.config.get("AUTH_DEV_LOGIN_ENABLED"):
        raise RuntimeError("AUTH_DEV_LOGIN_ENABLED não pode ficar ativo em produção.")

    _validate_partial_microsoft_config(app)
    _validate_microsoft_redirect_config(app)

    if is_production:
        required_microsoft = (
            "AUTH_MICROSOFT_TENANT_ID",
            "AUTH_MICROSOFT_CLIENT_ID",
            "AUTH_MICROSOFT_CLIENT_SECRET",
            "AUTH_MICROSOFT_REDIRECT_URI",
        )
        missing = [name for name in required_microsoft if not app.config.get(name)]
        if missing:
            raise RuntimeError(
                "Produção exige autenticação Microsoft configurada. Faltando: "
                + ", ".join(missing)
            )

    _validate_mail_config(app)

    if app.config.get("TRANSFER_EXPIRATION_DAYS", 0) <= 0:
        raise RuntimeError("TRANSFER_EXPIRATION_DAYS deve ser maior que zero.")

    if app.config.get("REPORT_EXPORT_MAX_ROWS", 0) <= 0:
        raise RuntimeError("REPORT_EXPORT_MAX_ROWS deve ser maior que zero.")
