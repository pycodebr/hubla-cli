from __future__ import annotations

from typing import Any

import pytest
import requests

from hubla_cli.errors import HublaHttpError, HublaNetworkError
from hubla_cli.transport import HublaTransport


class FakeAuth:
    def __init__(self) -> None:
        self.tokens = ["token-1", "token-2"]
        self.calls: list[bool] = []
        self.invalidations = 0

    def get_token(self, force_refresh: bool = False) -> str:
        self.calls.append(force_refresh)
        return self.tokens[1] if force_refresh else self.tokens[0]

    def invalidate(self) -> None:
        self.invalidations += 1


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: Any = None,
        content: bytes = b"payload",
    ) -> None:
        self.status_code = status_code
        self.payload = payload
        self.content = content

    def json(self) -> Any:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", "replace")


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> FakeResponse:
        self.calls.append(kwargs)
        return self.responses.pop(0)


def test_transport_refreshes_once_after_401() -> None:
    auth = FakeAuth()
    session = FakeSession(
        [
            FakeResponse(401, {"error": "expired"}),
            FakeResponse(200, {"ok": True}),
        ]
    )
    transport = HublaTransport(auth, session=session, request_id=False)

    assert transport.request("web", "GET", "/business") == {"ok": True}
    assert auth.invalidations == 1
    assert auth.calls == [False, True]
    assert session.calls[0]["headers"]["Authorization"] == "Bearer token-1"
    assert session.calls[1]["headers"]["Authorization"] == "Bearer token-2"
    assert session.calls[0]["allow_redirects"] is False


def test_transport_returns_bytes_without_json_decoding() -> None:
    auth = FakeAuth()
    session = FakeSession([FakeResponse(201, {"ignored": True}, content=b"xlsx-data")])
    transport = HublaTransport(auth, session=session, request_id=False)

    result = transport.request(
        "web",
        "POST",
        "/invoices/export",
        response_type="bytes",
    )

    assert result == b"xlsx-data"


def test_transport_redacts_sensitive_error_fields() -> None:
    auth = FakeAuth()
    session = FakeSession(
        [
            FakeResponse(
                403,
                {
                    "errorCode": "forbidden",
                    "token": "secret-token",
                    "nested": {
                        "password": "secret-password",
                        "accessCode": "sensitive-code",
                        "clientSecret": "sensitive-secret",
                        "email": "person@example.com",
                    },
                },
            )
        ]
    )
    transport = HublaTransport(auth, session=session, request_id=False)

    with pytest.raises(HublaHttpError) as caught:
        transport.request("web", "GET", "/business")

    assert caught.value.status_code == 403
    assert caught.value.data == {
        "errorCode": "forbidden",
        "token": "<redacted>",
        "nested": {
            "password": "<redacted>",
            "accessCode": "<redacted>",
            "clientSecret": "<redacted>",
            "email": "<redacted>",
        },
    }


@pytest.mark.parametrize(
    "path",
    [
        "https://example.com/steal",
        "http://127.0.0.1/private",
        "//example.com/steal",
        "\\\\example.com\\steal",
        "/business\nX-Injected: value",
    ],
)
def test_transport_rejects_absolute_or_protocol_relative_urls(path: str) -> None:
    transport = HublaTransport(FakeAuth(), session=FakeSession([]))

    with pytest.raises(ValueError, match="caminho relativo"):
        transport.request("web", "GET", path)


def test_transport_wraps_network_failures_without_echoing_provider_details() -> None:
    class FailingSession:
        def request(self, **kwargs: Any) -> FakeResponse:
            raise requests.ConnectionError("internal network detail")

    transport = HublaTransport(FakeAuth(), session=FailingSession())

    with pytest.raises(HublaNetworkError) as caught:
        transport.request("web", "GET", "/business")

    assert "internal network detail" not in str(caught.value)
    assert "conectar" in str(caught.value)


@pytest.mark.parametrize("header", ["Authorization", "Host", "Cookie"])
def test_transport_rejects_security_sensitive_header_overrides(header: str) -> None:
    transport = HublaTransport(FakeAuth(), session=FakeSession([]))

    with pytest.raises(ValueError, match="cabeçalho protegido"):
        transport.request(
            "web",
            "GET",
            "/business",
            headers={header: "attacker-controlled"},
        )
