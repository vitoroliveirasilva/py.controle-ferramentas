from __future__ import annotations

from app.core.exceptions import ForbiddenError, UnauthorizedError


class AuthConfigurationError(UnauthorizedError):
    message = "Autenticação Microsoft não configurada."


class AuthStateError(ForbiddenError):
    message = "Estado de autenticação inválido. Tente fazer login novamente."


class AuthAccessDeniedError(ForbiddenError):
    message = "Acesso negado. Usuário autenticado, mas não autorizado no sistema."
