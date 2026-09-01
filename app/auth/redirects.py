from __future__ import annotations

DEFAULT_MICROSOFT_REDIRECT_PATH = "/auth/callback"
LEGACY_MICROSOFT_REDIRECT_PATH = "/getAToken"


# Normaliza o caminho do callback Microsoft usado pelo MSAL
def normalize_microsoft_redirect_path(raw_path: str | None) -> str:
    redirect_path = (raw_path or DEFAULT_MICROSOFT_REDIRECT_PATH).strip()
    if not redirect_path:
        return DEFAULT_MICROSOFT_REDIRECT_PATH
    if not redirect_path.startswith("/"):
        redirect_path = f"/{redirect_path}"
    return redirect_path


def is_default_microsoft_redirect_path(raw_path: str | None) -> bool:
    return (
        normalize_microsoft_redirect_path(raw_path) == DEFAULT_MICROSOFT_REDIRECT_PATH
    )
