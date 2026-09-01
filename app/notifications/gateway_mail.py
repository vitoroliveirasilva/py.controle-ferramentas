from __future__ import annotations

import json
import ssl
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from http.client import HTTPResponse
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from email_validator import EmailNotValidError, validate_email

TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}
PERMANENT_STATUS_CODES = {400, 401, 403, 404, 409, 422}
MAX_ERROR_BODY_LENGTH = 600


class GatewayMailError(RuntimeError):
    """Erro base do client de e-mail via Brasif Gateway"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        attempts: int | None = None,
        duration_ms: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.attempts = attempts
        self.duration_ms = duration_ms


class GatewayMailConfigError(GatewayMailError):
    """Configuração obrigatória ausente ou inválida"""


class GatewayMailValidationError(GatewayMailError):
    """Payload inválido antes da chamada HTTP"""


class GatewayMailTimeoutError(GatewayMailError):
    """Timeout na chamada ao gateway"""


class GatewayMailAuthError(GatewayMailError):
    """Falha de autenticação/autorização no gateway"""


class GatewayMailPermanentError(GatewayMailError):
    """Erro permanente retornado pelo gateway"""


class GatewayMailTransientError(GatewayMailError):
    """Erro transitório retornado pelo gateway após retries"""


class GatewayMailUnexpectedResponseError(GatewayMailError):
    """Resposta inesperada do gateway"""


@dataclass(frozen=True)
class GatewayMailResponse:
    status_code: int
    body: str
    attempts: int
    duration_ms: int


@dataclass(frozen=True)
class GatewayHTTPResponse:
    status_code: int
    body: str


@dataclass(frozen=True)
class GatewayMailMessage:
    subject: str
    body: str
    to_recipients: list[str]
    cc_recipients: list[str]
    is_html: bool = False
    sender_email: str | None = None
    attachments: list[dict[str, Any]] | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "subject": self.subject,
            "body": self.body,
            "to_recipients": self.to_recipients,
            "cc_recipients": self.cc_recipients,
            "is_html": self.is_html,
            "attachments": self.attachments or [],
        }
        if self.sender_email:
            payload["sender_email"] = self.sender_email
        return payload


# Transporte HTTP mínimo para não adicionar dependência externa
class UrlLibGatewayMailTransport:

    def post_json(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        payload: Mapping[str, Any],
        timeout_seconds: float,
        verify_ssl: bool,
    ) -> GatewayHTTPResponse:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url,
            data=data,
            headers={**dict(headers), "Content-Type": "application/json"},
            method="POST",
        )
        context = None if verify_ssl else ssl._create_unverified_context()  # noqa: S323
        response: HTTPResponse
        with urlopen(request, timeout=timeout_seconds, context=context) as response:
            body = response.read().decode("utf-8", errors="replace")
            return GatewayHTTPResponse(status_code=response.status, body=body)


def normalize_email(value: str, *, field_name: str) -> str:
    raw_email = (value or "").strip()
    if not raw_email:
        raise GatewayMailValidationError(f"{field_name} não pode ficar vazio.")
    try:
        info = validate_email(raw_email, check_deliverability=False)
    except EmailNotValidError as exc:
        raise GatewayMailValidationError(f"{field_name} inválido: {raw_email}") from exc
    return info.normalized


def mask_email(value: str | None) -> str | None:
    if not value:
        return None
    local, sep, domain = value.partition("@")
    if not sep:
        return "[invalid-email]"
    masked_local = local[:1] + "*" if len(local) <= 2 else local[:2] + "***"
    return f"{masked_local}@{domain}"


def summarize_recipients(recipients: Sequence[str]) -> dict[str, Any]:
    masked = [mask_email(email) for email in recipients[:5]]
    summary: dict[str, Any] = {"count": len(recipients), "sample": masked}
    if len(recipients) > 5:
        summary["truncated"] = len(recipients) - 5
    return summary


def _dedupe_preserving_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _estimate_attachment_size_bytes(attachment: Mapping[str, Any]) -> int:
    for key in ("contentBytes", "content_bytes", "content_base64", "content"):
        value = attachment.get(key)
        if isinstance(value, str):
            return int(len(value.encode("utf-8")) * 0.75)
    return len(json.dumps(attachment, ensure_ascii=False, default=str).encode("utf-8"))


def validate_attachments(
    attachments: Sequence[Mapping[str, Any]] | None,
    *,
    max_attachment_mb: int,
) -> list[dict[str, Any]]:
    if not attachments:
        return []
    max_bytes = max_attachment_mb * 1024 * 1024
    total_size = 0
    normalized: list[dict[str, Any]] = []
    for index, attachment in enumerate(attachments, start=1):
        if not isinstance(attachment, Mapping):
            raise GatewayMailValidationError(f"Anexo {index} deve ser um objeto JSON.")
        item = dict(attachment)
        try:
            json.dumps(item, ensure_ascii=False, default=str)
        except TypeError as exc:
            raise GatewayMailValidationError(f"Anexo {index} não é serializável.") from exc
        estimated_size = _estimate_attachment_size_bytes(item)
        total_size += estimated_size
        if estimated_size > max_bytes:
            raise GatewayMailValidationError(
                f"Anexo {index} excede o limite de {max_attachment_mb} MB."
            )
        normalized.append(item)
    if total_size > max_bytes:
        raise GatewayMailValidationError(
            f"Anexos excedem o limite total de {max_attachment_mb} MB."
        )
    return normalized


def build_gateway_mail_message(
    *,
    subject: str,
    body: str,
    to_recipients: Sequence[str],
    cc_recipients: Sequence[str] | None = None,
    sender_email: str | None = None,
    is_html: bool = False,
    attachments: Sequence[Mapping[str, Any]] | None = None,
    max_recipients: int,
    max_body_length: int,
    max_attachment_mb: int,
) -> GatewayMailMessage:
    normalized_subject = (subject or "").strip()
    if not normalized_subject:
        raise GatewayMailValidationError("Assunto do e-mail é obrigatório.")
    if len(normalized_subject) > 200:
        raise GatewayMailValidationError("Assunto do e-mail excede 200 caracteres.")

    normalized_body = body or ""
    if not normalized_body.strip():
        raise GatewayMailValidationError("Corpo do e-mail é obrigatório.")
    if len(normalized_body) > max_body_length:
        raise GatewayMailValidationError(
            f"Corpo do e-mail excede {max_body_length} caracteres."
        )

    normalized_to = _dedupe_preserving_order(
        [normalize_email(email, field_name="Destinatário") for email in to_recipients]
    )
    normalized_cc = _dedupe_preserving_order(
        [normalize_email(email, field_name="CC") for email in (cc_recipients or [])]
    )
    if not normalized_to:
        raise GatewayMailValidationError("Informe ao menos um destinatário.")

    total_recipients = len(normalized_to) + len(normalized_cc)
    if total_recipients > max_recipients:
        raise GatewayMailValidationError(
            f"Envio excede o limite de {max_recipients} destinatário(s)."
        )

    normalized_sender = None
    if sender_email:
        normalized_sender = normalize_email(sender_email, field_name="Remetente")

    normalized_attachments = validate_attachments(
        attachments,
        max_attachment_mb=max_attachment_mb,
    )
    return GatewayMailMessage(
        sender_email=normalized_sender,
        subject=normalized_subject,
        body=normalized_body,
        to_recipients=normalized_to,
        cc_recipients=normalized_cc,
        is_html=is_html,
        attachments=normalized_attachments,
    )


class BrasifGatewayMailClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: int = 10,
        verify_ssl: bool = True,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.25,
        transport: UrlLibGatewayMailTransport | None = None,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.timeout_seconds = timeout_seconds
        self.verify_ssl = verify_ssl
        self.max_retries = max(0, max_retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.transport = transport or UrlLibGatewayMailTransport()
        if not self.base_url:
            raise GatewayMailConfigError("BRASIF_GATEWAY_BASE_URL não configurada.")
        if not self.api_key:
            raise GatewayMailConfigError("BRASIF_GATEWAY_API_KEY não configurada.")
        if self.timeout_seconds <= 0:
            raise GatewayMailConfigError("Timeout do Brasif Gateway deve ser maior que zero.")

    @property
    def send_mail_url(self) -> str:
        return f"{self.base_url}/msgraph/send-mail"

    def send(self, message: GatewayMailMessage) -> GatewayMailResponse:
        start = time.monotonic()
        payload = message.to_payload()
        attempts = self.max_retries + 1
        last_error: GatewayMailError | None = None
        for attempt in range(1, attempts + 1):
            try:
                response = self.transport.post_json(
                    url=self.send_mail_url,
                    headers={"x-api-key": self.api_key},
                    payload=payload,
                    timeout_seconds=self.timeout_seconds,
                    verify_ssl=self.verify_ssl,
                )
            except TimeoutError as exc:
                last_error = GatewayMailTimeoutError(
                    "Timeout ao chamar Brasif Gateway.", attempts=attempt
                )
                if attempt >= attempts:
                    raise last_error from exc
                self._sleep_before_retry(attempt)
                continue
            except HTTPError as exc:
                body = _safe_error_body(exc.read().decode("utf-8", errors="replace"))
                response = GatewayHTTPResponse(status_code=exc.code, body=body)
            except URLError as exc:
                last_error = GatewayMailTransientError(
                    "Falha transitória de rede ao chamar Brasif Gateway.",
                    attempts=attempt,
                )
                if attempt >= attempts:
                    raise last_error from exc
                self._sleep_before_retry(attempt)
                continue

            if response.status_code in TRANSIENT_STATUS_CODES and attempt < attempts:
                self._sleep_before_retry(attempt)
                continue

            self._raise_for_status(response)
            duration_ms = int((time.monotonic() - start) * 1000)
            return GatewayMailResponse(
                status_code=response.status_code,
                body=_safe_error_body(response.body),
                attempts=attempt,
                duration_ms=duration_ms,
            )

        if last_error:
            raise last_error
        raise GatewayMailUnexpectedResponseError("Resposta inesperada do Brasif Gateway.")

    def _sleep_before_retry(self, attempt: int) -> None:
        if self.retry_backoff_seconds <= 0:
            return
        time.sleep(self.retry_backoff_seconds * attempt)

    def _raise_for_status(self, response: GatewayHTTPResponse) -> None:
        status_code = response.status_code
        body = _safe_error_body(response.body)
        if 200 <= status_code < 300:
            return
        if status_code in {401, 403}:
            raise GatewayMailAuthError(
                f"Brasif Gateway recusou autenticação/autorização ({status_code}).",
                status_code=status_code,
            )
        if status_code == 422:
            raise GatewayMailValidationError(
                "Brasif Gateway recusou o payload de e-mail (422).",
                status_code=status_code,
            )
        if status_code in TRANSIENT_STATUS_CODES:
            raise GatewayMailTransientError(
                f"Brasif Gateway retornou erro transitório ({status_code}): {body}",
                status_code=status_code,
            )
        if status_code in PERMANENT_STATUS_CODES or 400 <= status_code < 500:
            raise GatewayMailPermanentError(
                f"Brasif Gateway retornou erro permanente ({status_code}): {body}",
                status_code=status_code,
            )
        raise GatewayMailUnexpectedResponseError(
            f"Brasif Gateway retornou status inesperado ({status_code}): {body}",
            status_code=status_code,
        )


def _safe_error_body(body: str | None) -> str:
    cleaned = (body or "").strip()
    if len(cleaned) > MAX_ERROR_BODY_LENGTH:
        return cleaned[:MAX_ERROR_BODY_LENGTH] + "...[truncated]"
    return cleaned
