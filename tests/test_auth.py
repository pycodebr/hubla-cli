from __future__ import annotations

from typing import Any

import pytest

from hubla_cli.auth import FirebaseConfigResolver, HublaAuth
from hubla_cli.errors import HublaAuthError


class FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any],
        status_code: int = 200,
        content: bytes = b"payload",
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.content = content

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self.responses.pop(0)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": "POST", "url": url, **kwargs})
        return self.responses.pop(0)


def test_firebase_config_resolver_reads_public_hubla_config() -> None:
    session = FakeSession([FakeResponse({"apiKey": "public-browser-key"})])
    resolver = FirebaseConfigResolver(session=session)

    assert resolver.get_api_key() == "public-browser-key"
    assert resolver.get_api_key() == "public-browser-key"
    assert len(session.calls) == 1
    assert session.calls[0]["url"].endswith("/__/firebase/init.json")


def test_password_login_discovers_key_and_caches_token() -> None:
    session = FakeSession(
        [
            FakeResponse({"apiKey": "public-browser-key"}),
            FakeResponse(
                {
                    "idToken": "id-1",
                    "refreshToken": "refresh-1",
                    "expiresIn": "3600",
                    "localId": "user-1",
                }
            ),
        ]
    )
    auth = HublaAuth(
        email="owner@example.com",
        password="not-persisted",
        session=session,
        clock=lambda: 1_000,
    )

    tokens = auth.login()

    assert tokens.id_token == "id-1"
    assert tokens.refresh_token == "refresh-1"
    assert auth.get_token() == "id-1"
    assert len(session.calls) == 2
    assert session.calls[1]["json"]["email"] == "owner@example.com"
    assert session.calls[1]["json"]["password"] == "not-persisted"


def test_invalid_login_error_never_echoes_password_or_provider_payload() -> None:
    session = FakeSession(
        [
            FakeResponse({"apiKey": "public-browser-key"}),
            FakeResponse(
                {
                    "error": {
                        "message": "INVALID_LOGIN_CREDENTIALS:not-persisted",
                    }
                },
                status_code=400,
            ),
        ]
    )
    auth = HublaAuth(
        email="owner@example.com",
        password="not-persisted",
        session=session,
    )

    with pytest.raises(HublaAuthError) as caught:
        auth.login()

    assert "not-persisted" not in str(caught.value)
    assert "INVALID_LOGIN_CREDENTIALS" not in str(caught.value)
    assert "credenciais" in str(caught.value).lower()


def test_missing_login_credentials_fail_without_network_call() -> None:
    session = FakeSession([])
    auth = HublaAuth(session=session)

    with pytest.raises(HublaAuthError, match="HUBLA_EMAIL"):
        auth.login()

    assert session.calls == []


def test_saved_refresh_token_creates_session_without_password() -> None:
    session = FakeSession(
        [
            FakeResponse({"apiKey": "public-browser-key"}),
            FakeResponse(
                {
                    "id_token": "id-2",
                    "refresh_token": "refresh-2",
                    "expires_in": "3600",
                    "user_id": "user-1",
                }
            ),
        ]
    )
    auth = HublaAuth(refresh_token="refresh-1", session=session, clock=lambda: 1_000)

    assert auth.get_token() == "id-2"
    assert session.calls[1]["data"] == {
        "grant_type": "refresh_token",
        "refresh_token": "refresh-1",
    }


def test_explicit_public_key_skips_config_discovery() -> None:
    session = FakeSession(
        [
            FakeResponse(
                {
                    "idToken": "id-1",
                    "refreshToken": "refresh-1",
                    "expiresIn": "3600",
                }
            )
        ]
    )
    auth = HublaAuth(
        sign_key="explicit-public-key",
        email="owner@example.com",
        password="not-persisted",
        session=session,
    )

    auth.login()

    assert len(session.calls) == 1
    assert session.calls[0]["params"] == {"key": "explicit-public-key"}


def test_public_config_without_api_key_fails_safely() -> None:
    resolver = FirebaseConfigResolver(session=FakeSession([FakeResponse({})]))

    with pytest.raises(HublaAuthError, match="não informou"):
        resolver.get_api_key()


def test_environment_factory_prefers_explicit_saved_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HUBLA_EMAIL", "environment@example.com")
    monkeypatch.setenv("HUBLA_REFRESH_TOKEN", "environment-token")

    auth = HublaAuth.from_environment(
        email="profile@example.com",
        refresh_token="profile-token",
    )

    assert auth._email == "profile@example.com"
    assert auth._refresh_token == "profile-token"
