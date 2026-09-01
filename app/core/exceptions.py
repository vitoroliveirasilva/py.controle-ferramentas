from __future__ import annotations


# Base exceção para erros controlados na aplicação
class AppError(Exception):

    status_code = 400
    message = "Não foi possível processar a solicitação."

    def __init__(
        self, message: str | None = None, status_code: int | None = None
    ) -> None:
        self.message = message or self.message
        self.status_code = status_code or self.status_code
        super().__init__(self.message)


class BadRequestError(AppError):
    status_code = 400
    message = "Solicitação inválida."


class UnauthorizedError(AppError):
    status_code = 401
    message = "Autenticação necessária."


class ForbiddenError(AppError):
    status_code = 403
    message = "Você não tem permissão para acessar este recurso."


class NotFoundError(AppError):
    status_code = 404
    message = "Recurso não encontrado."


class TooManyRequestsError(AppError):
    status_code = 429
    message = "Muitas solicitações em pouco tempo."
