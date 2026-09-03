from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hubla_cli.credentials import CredentialStore, StoredCredentials
from hubla_cli.errors import CredentialError


class FakeKeyring:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.values.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.values[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self.values.pop((service, username), None)


class FailingDeleteKeyring(FakeKeyring):
    def __init__(self) -> None:
        super().__init__()
        self.fail_deletes = False

    def delete_password(self, service: str, username: str) -> None:
        if self.fail_deletes:
            raise RuntimeError("keyring locked")
        super().delete_password(service, username)


def test_credentials_use_keyring_without_writing_refresh_token(tmp_path: Path) -> None:
    keyring = FakeKeyring()
    store = CredentialStore(config_dir=tmp_path, keyring_backend=keyring)

    store.save("owner@example.com", "refresh-secret")

    metadata = (tmp_path / "profiles" / "default.json").read_text()
    assert "refresh-secret" not in metadata
    assert json.loads(metadata)["storage"] == "keyring"
    assert store.load() == StoredCredentials(
        email="owner@example.com",
        refresh_token="refresh-secret",
    )


def test_credentials_fall_back_to_private_file_and_never_store_password(
    tmp_path: Path,
) -> None:
    store = CredentialStore(config_dir=tmp_path, keyring_backend=False)

    store.save("owner@example.com", "refresh-secret")

    path = tmp_path / "profiles" / "default.json"
    contents = path.read_text()
    assert "refresh-secret" in contents
    assert "password" not in contents.lower()
    assert store.load() == StoredCredentials(
        email="owner@example.com",
        refresh_token="refresh-secret",
    )
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700


def test_logout_removes_file_and_keyring_secret(tmp_path: Path) -> None:
    keyring = FakeKeyring()
    store = CredentialStore(config_dir=tmp_path, keyring_backend=keyring)
    store.save("owner@example.com", "refresh-secret")

    store.delete()

    assert store.load() is None
    assert not (tmp_path / "profiles" / "default.json").exists()
    assert keyring.values == {}


def test_logout_preserves_profile_and_reports_keyring_deletion_failure(
    tmp_path: Path,
) -> None:
    keyring = FailingDeleteKeyring()
    store = CredentialStore(config_dir=tmp_path, keyring_backend=keyring)
    store.save("owner@example.com", "refresh-secret")
    keyring.fail_deletes = True

    with pytest.raises(CredentialError, match="cofre"):
        store.delete()

    assert store.profile_path.exists()
    assert keyring.values == {
        ("hubla-cli:default", "owner@example.com"): "refresh-secret"
    }


def test_failed_metadata_write_rolls_back_new_keyring_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keyring = FakeKeyring()
    store = CredentialStore(config_dir=tmp_path, keyring_backend=keyring)

    def fail_write(_metadata: dict[str, str]) -> None:
        raise CredentialError("disk failure")

    monkeypatch.setattr(store, "_write_private_json", fail_write)

    with pytest.raises(CredentialError, match="disk failure"):
        store.save("owner@example.com", "refresh-secret")

    assert keyring.values == {}


def test_relogin_with_new_email_removes_previous_keyring_session(
    tmp_path: Path,
) -> None:
    keyring = FakeKeyring()
    store = CredentialStore(config_dir=tmp_path, keyring_backend=keyring)
    store.save("old@example.com", "old-refresh")

    store.save("new@example.com", "new-refresh")

    assert keyring.values == {("hubla-cli:default", "new@example.com"): "new-refresh"}


def test_relogin_aborts_if_previous_keyring_session_cannot_be_removed(
    tmp_path: Path,
) -> None:
    keyring = FailingDeleteKeyring()
    store = CredentialStore(config_dir=tmp_path, keyring_backend=keyring)
    store.save("old@example.com", "old-refresh")
    keyring.fail_deletes = True

    with pytest.raises(CredentialError, match="cofre"):
        store.save("new@example.com", "new-refresh")

    assert store.load() == StoredCredentials(
        email="old@example.com",
        refresh_token="old-refresh",
    )
    assert keyring.values == {("hubla-cli:default", "old@example.com"): "old-refresh"}


def test_failed_relogin_restores_previous_keyring_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keyring = FakeKeyring()
    store = CredentialStore(config_dir=tmp_path, keyring_backend=keyring)
    store.save("owner@example.com", "old-refresh")

    def fail_write(_metadata: dict[str, str]) -> None:
        raise CredentialError("disk failure")

    monkeypatch.setattr(store, "_write_private_json", fail_write)

    with pytest.raises(CredentialError, match="disk failure"):
        store.save("owner@example.com", "new-refresh")

    assert keyring.values == {("hubla-cli:default", "owner@example.com"): "old-refresh"}


@pytest.mark.parametrize("profile", ["../other", "a/b", "", ".", "..", "x" * 65])
def test_profile_name_cannot_escape_config_directory(
    tmp_path: Path,
    profile: str,
) -> None:
    with pytest.raises(CredentialError):
        CredentialStore(
            config_dir=tmp_path,
            profile=profile,
            keyring_backend=False,
        )
