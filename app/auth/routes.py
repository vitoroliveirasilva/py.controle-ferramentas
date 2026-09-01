from __future__ import annotations

from flask import (
    Blueprint,
    Flask,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, logout_user

from app.auth.decorators import active_user_required
from app.auth.exceptions import AuthAccessDeniedError, AuthConfigurationError
from app.auth.forms import DevLoginForm
from app.auth.msal_client import MicrosoftAuthClient, pop_auth_next_url
from app.auth.redirects import (
    DEFAULT_MICROSOFT_REDIRECT_PATH,
    normalize_microsoft_redirect_path,
)
from app.auth.services import login_authorized_user_from_claims, record_login_failure
from app.core.security import is_safe_next_url

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next_url(raw_next: str | None) -> str:
    if raw_next and is_safe_next_url(raw_next):
        return raw_next
    return url_for("main.index")


def _dev_login_enabled() -> bool:
    return bool(current_app.config.get("AUTH_DEV_LOGIN_ENABLED"))


def register_microsoft_callback_route(app: Flask) -> None:
    redirect_path = normalize_microsoft_redirect_path(
        app.config.get("AUTH_MICROSOFT_REDIRECT_PATH")
    )

    if redirect_path == DEFAULT_MICROSOFT_REDIRECT_PATH:
        return

    app.add_url_rule(
        redirect_path,
        endpoint="auth_microsoft_callback_alias",
        view_func=callback,
        methods=["GET"],
    )


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_safe_next_url(request.args.get("next")))

    next_url = _safe_next_url(request.args.get("next"))
    form = DevLoginForm()
    msal_client = MicrosoftAuthClient()

    if _dev_login_enabled() and form.validate_on_submit():
        email = form.email.data.strip().lower()
        claims = {
            "oid": (
                form.microsoft_oid.data.strip()
                if form.microsoft_oid.data
                else f"dev-{email}"
            ),
            "preferred_username": email,
            "name": form.nome.data.strip() if form.nome.data else email,
        }
        try:
            login_authorized_user_from_claims(claims)
        except AuthAccessDeniedError as exc:
            record_login_failure(claims, exc.message)
            current_app.logger.warning("Login dev negado: %s", exc.message)
            flash(exc.message, "danger")
            return render_template(
                "auth/login.html",
                form=form,
                msal_configured=msal_client.is_configured,
            )

        flash("Login de desenvolvimento realizado com sucesso.", "success")
        return redirect(next_url)

    if request.method == "POST" and not _dev_login_enabled():
        raise AuthConfigurationError("Login de desenvolvimento está desabilitado.")

    if msal_client.is_configured and not _dev_login_enabled():
        return redirect(msal_client.build_authorization_url(next_url=next_url))

    return render_template(
        "auth/login.html",
        form=form,
        msal_configured=msal_client.is_configured,
    )


@bp.get("/microsoft")
def microsoft_login():
    next_url = _safe_next_url(request.args.get("next"))
    msal_client = MicrosoftAuthClient()
    return redirect(msal_client.build_authorization_url(next_url=next_url))


@bp.get("/callback")
def callback():
    error = request.args.get("error")
    if error:
        description = request.args.get("error_description") or error
        current_app.logger.warning("Callback Microsoft retornou erro: %s", description)
        raise AuthAccessDeniedError(
            "A Microsoft recusou a autenticação ou o usuário cancelou o login."
        )

    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        raise AuthAccessDeniedError("Callback Microsoft sem código de autorização.")

    msal_client = MicrosoftAuthClient()
    msal_client.validate_state(state)

    token_result = msal_client.acquire_token_by_auth_code(code)
    claims = msal_client.extract_claims(token_result)

    try:
        login_authorized_user_from_claims(claims)
    except AuthAccessDeniedError as exc:
        record_login_failure(claims, exc.message)
        raise

    flash("Login Microsoft realizado com sucesso.", "success")
    return redirect(_safe_next_url(pop_auth_next_url()))


@bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        current_app.logger.info("Logout do usuário: %s", current_user.email_lower)

    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("main.index"))


@bp.get("/denied")
def denied():
    return render_template("auth/denied.html"), 403


@bp.get("/me")
@active_user_required
def me():
    return jsonify(
        {
            "id_usuario": current_user.id_usuario,
            "email": current_user.email_lower,
            "nome": current_user.nome,
            "ativo": current_user.ativo,
            "bloqueado": current_user.bloqueado,
        }
    )
