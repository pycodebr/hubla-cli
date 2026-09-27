from __future__ import annotations

import json
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from hubla_cli import cli
from hubla_cli.client import HublaClient
from hubla_cli.credentials import CredentialStore, StoredCredentials
from hubla_cli.errors import (
    CredentialError,
    HublaAuthError,
    HublaContractError,
    HublaHttpError,
)


class CollaboratorTransport:
    def __init__(self, accesses: Any, status: int = 404) -> None:
        self.accesses = accesses
        self.status = status
        self.paths: list[str] = []

    def request(self, service: str, method: str, path: str, **kwargs: Any) -> Any:
        self.paths.append(path)
        if path == "/business":
            raise HublaHttpError(self.status, "GET", "https://hub.la/business")
        if path == "/user/roleplay/my-access":
            return self.accesses
        raise AssertionError(path)


def test_collaborator_only_identity_is_verified_by_access_list() -> None:
    transport = CollaboratorTransport([{"userId": "owner-1"}])

    assert HublaClient(transport=transport).account.identity() == {
        "kind": "collaborator",
        "accesses": [{"userId": "owner-1"}],
    }
    assert transport.paths == ["/business", "/user/roleplay/my-access"]


@pytest.mark.parametrize("accesses", [[], {}, None])
def test_empty_or_invalid_access_is_not_a_verified_account(accesses: Any) -> None:
    with pytest.raises(HublaHttpError) as caught:
        HublaClient(transport=CollaboratorTransport(accesses)).account.identity()
    assert caught.value.status_code == 404


def test_non_404_business_error_does_not_fall_back_to_access() -> None:
    transport = CollaboratorTransport([{"userId": "owner-1"}], status=403)
    with pytest.raises(HublaHttpError) as caught:
        HublaClient(transport=transport).account.identity()
    assert caught.value.status_code == 403
    assert transport.paths == ["/business"]


def test_named_profile_ignores_environment_owner_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Store:
        def load(self) -> StoredCredentials:
            return StoredCredentials(
                email="collaborator@example.com",
                refresh_token="collaborator-refresh",
            )

    monkeypatch.setenv("HUBLA_EMAIL", "owner@example.com")
    monkeypatch.setenv("HUBLA_PASSWORD", "environment-password")
    monkeypatch.setenv("HUBLA_REFRESH_TOKEN", "environment-refresh")
    client = HublaClient.from_profile(
        profile="collaborator", credential_store=cast(CredentialStore, Store())
    )
    auth = client._transport._auth

    assert auth._email == "collaborator@example.com"
    assert auth._refresh_token == "collaborator-refresh"
    assert auth._password is None


def test_named_profile_requires_saved_login_even_when_environment_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Store:
        def load(self) -> None:
            return None

    monkeypatch.setenv("HUBLA_EMAIL", "owner@example.com")
    monkeypatch.setenv("HUBLA_PASSWORD", "environment-password")
    with pytest.raises(CredentialError, match="nenhum login encontrado"):
        HublaClient.from_profile(
            profile="collaborator", credential_store=cast(CredentialStore, Store())
        )


def test_named_profile_status_identifies_saved_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Store:
        def load(self) -> StoredCredentials:
            return StoredCredentials(
                email="collaborator@example.com",
                refresh_token="collaborator-refresh",
            )

    class Account:
        def identity(self) -> dict[str, Any]:
            return {"kind": "collaborator", "accesses": [{"userId": "owner-1"}]}

    class Client:
        account = Account()

    monkeypatch.setenv("HUBLA_EMAIL", "owner@example.com")
    monkeypatch.setenv("HUBLA_PASSWORD", "environment-password")
    monkeypatch.setattr(cli, "CredentialStore", lambda profile: Store())
    monkeypatch.setattr(cli, "get_client", lambda profile: Client())
    result = CliRunner().invoke(
        cli.app, ["--profile", "collaborator", "--json", "status"]
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)["data"]
    assert data["email"] == "collaborator@example.com"
    assert data["source"] == "saved_profile"
    assert data["account"]["kind"] == "collaborator"


def test_assume_account_checks_access_before_exchanging_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ParentTransport:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def request(self, service: str, method: str, path: str, **kwargs: Any) -> Any:
            self.calls.append((method, path))
            if path == "/user/roleplay/my-access":
                return [{"userId": "owner-1"}]
            if path == "/user/roleplay/sign-in":
                assert kwargs["json"] == {"roleplayUserId": "owner-1"}
                assert kwargs["response_type"] == "text"
                return "custom-token"
            raise AssertionError(path)

    class ScopedAuth:
        def __init__(self, **kwargs: Any) -> None:
            self.custom_token: str | None = None

        def login_with_custom_token(self, token: str) -> None:
            self.custom_token = token

    class ScopedTransport:
        def __init__(self, auth: ScopedAuth, **kwargs: Any) -> None:
            assert auth.custom_token == "custom-token"

        def request(self, service: str, method: str, path: str, **kwargs: Any) -> Any:
            assert path == "/user/roleplay/reference"
            return {"userId": "owner-1"}

    monkeypatch.setattr("hubla_cli.client.HublaAuth", ScopedAuth)
    monkeypatch.setattr("hubla_cli.client.HublaTransport", ScopedTransport)
    parent_transport = ParentTransport()
    parent = HublaClient(auth=cast(Any, object()), transport=parent_transport)

    with pytest.raises(HublaAuthError, match="não encontrada"):
        parent.assume_account("someone-else")
    assert parent_transport.calls == [("GET", "/user/roleplay/my-access")]

    scoped = parent.assume_account("owner-1")
    assert scoped is not parent
    assert parent_transport.calls[-2:] == [
        ("GET", "/user/roleplay/my-access"),
        ("POST", "/user/roleplay/sign-in"),
    ]


def test_assume_account_rejects_mismatched_roleplay_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ParentTransport:
        def request(self, service: str, method: str, path: str, **kwargs: Any) -> Any:
            if path == "/user/roleplay/my-access":
                return [{"userId": "owner-1"}]
            return "custom-token"

    class ScopedAuth:
        def __init__(self, **kwargs: Any) -> None:
            pass

        def login_with_custom_token(self, token: str) -> None:
            pass

    class ScopedTransport:
        def __init__(self, auth: ScopedAuth, **kwargs: Any) -> None:
            pass

        def request(self, service: str, method: str, path: str, **kwargs: Any) -> Any:
            return {"userId": "different-owner"}

    monkeypatch.setattr("hubla_cli.client.HublaAuth", ScopedAuth)
    monkeypatch.setattr("hubla_cli.client.HublaTransport", ScopedTransport)
    parent = HublaClient(auth=cast(Any, object()), transport=ParentTransport())
    with pytest.raises(HublaContractError, match="não corresponde"):
        parent.assume_account("owner-1")
