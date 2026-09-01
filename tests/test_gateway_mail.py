from __future__ import annotations

import pytest

from app.notifications.gateway_mail import (
    BrasifGatewayMailClient,
    GatewayHTTPResponse,
    GatewayMailAuthError,
    GatewayMailConfigError,
    GatewayMailTimeoutError,
    GatewayMailUnexpectedResponseError,
    GatewayMailValidationError,
    build_gateway_mail_message,
)


class FakeTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post_json(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _message(**overrides):
    values = {
        "subject": "Teste",
        "body": "Corpo",
        "to_recipients": ["destino@brasif.com.br"],
        "cc_recipients": [],
        "max_recipients": 50,
        "max_body_length": 50000,
        "max_attachment_mb": 10,
    }
    values.update(overrides)
    return build_gateway_mail_message(**values)


def _client(transport: FakeTransport, **overrides):
    values = {
        "base_url": "https://howard.brasif.local",
        "api_key": "secret-api-key",
        "timeout_seconds": 10,
        "verify_ssl": True,
        "max_retries": 2,
        "retry_backoff_seconds": 0,
        "transport": transport,
    }
    values.update(overrides)
    return BrasifGatewayMailClient(**values)


def test_gateway_mail_client_sends_valid_message():
    transport = FakeTransport(GatewayHTTPResponse(status_code=202, body='{"ok": true}'))
    client = _client(transport)

    response = client.send(_message())

    assert response.status_code == 202
    assert response.attempts == 1
    assert transport.calls[0]["url"] == "https://howard.brasif.local/msgraph/send-mail"
    assert transport.calls[0]["headers"] == {"x-api-key": "secret-api-key"}
    assert transport.calls[0]["payload"]["to_recipients"] == ["destino@brasif.com.br"]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"subject": ""}, "Assunto"),
        ({"body": ""}, "Corpo"),
        ({"to_recipients": []}, "destinatário"),
        ({"to_recipients": ["email-invalido"]}, "Destinatário inválido"),
        (
            {"to_recipients": ["a@brasif.com.br", "b@brasif.com.br"], "max_recipients": 1},
            "limite",
        ),
    ],
)
def test_gateway_mail_message_validation(overrides, message):
    with pytest.raises(GatewayMailValidationError) as exc:
        _message(**overrides)

    assert message.lower() in str(exc.value).lower()


def test_gateway_mail_client_requires_api_key():
    with pytest.raises(GatewayMailConfigError) as exc:
        _client(FakeTransport(), api_key="")

    assert "api" in str(exc.value).lower()
    assert "secret-api-key" not in str(exc.value)


def test_gateway_mail_timeout_retries_then_fails():
    transport = FakeTransport(TimeoutError(), TimeoutError(), TimeoutError())
    client = _client(transport, max_retries=2)

    with pytest.raises(GatewayMailTimeoutError) as exc:
        client.send(_message())

    assert len(transport.calls) == 3
    assert "api-key" not in str(exc.value).lower()
    assert "secret-api-key" not in str(exc.value)


def test_gateway_mail_422_never_retries():
    transport = FakeTransport(GatewayHTTPResponse(status_code=422, body="payload inválido"))
    client = _client(transport, max_retries=2)

    with pytest.raises(GatewayMailValidationError):
        client.send(_message())

    assert len(transport.calls) == 1


@pytest.mark.parametrize("status_code", [401, 403])
def test_gateway_mail_auth_errors_never_retry(status_code):
    transport = FakeTransport(GatewayHTTPResponse(status_code=status_code, body="forbidden"))
    client = _client(transport, max_retries=2)

    with pytest.raises(GatewayMailAuthError):
        client.send(_message())

    assert len(transport.calls) == 1


def test_gateway_mail_500_retries_and_succeeds():
    transport = FakeTransport(
        GatewayHTTPResponse(status_code=500, body="erro"),
        GatewayHTTPResponse(status_code=202, body="ok"),
    )
    client = _client(transport, max_retries=2)

    response = client.send(_message())

    assert response.status_code == 202
    assert response.attempts == 2
    assert len(transport.calls) == 2


def test_gateway_mail_unexpected_response_raises():
    transport = FakeTransport(GatewayHTTPResponse(status_code=302, body="redirect"))
    client = _client(transport)

    with pytest.raises(GatewayMailUnexpectedResponseError):
        client.send(_message())
