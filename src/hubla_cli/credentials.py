"""Cross-platform storage for renewable Hubla sessions."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from platformdirs import user_config_path

from hubla_cli.errors import CredentialError

_PROFILE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_SERVICE_PREFIX = "hubla-cli"


@dataclass(frozen=True)
class StoredCredentials:
    """Credential material needed to renew a Hubla session."""

    email: str
    refresh_token: str


class CredentialStore:
    """Store refresh tokens in an OS keyring, with a private-file fallback."""

    def __init__(
        self,
        *,
        config_dir: str | Path | None = None,
        profile: str = "default",
        keyring_backend: Any = None,
    ) -> None:
        if not _PROFILE_PATTERN.fullmatch(profile) or profile in {".", ".."}:
            raise CredentialError(
                "perfil inválido; use letras, números, ponto, hífen ou sublinhado"
            )
        self._profile = profile
        self._config_dir = Path(config_dir or user_config_path("hubla-cli"))
        self._profile_path = self._config_dir / "profiles" / f"{profile}.json"
        self._service = f"{_SERVICE_PREFIX}:{profile}"
        self._keyring = self._resolve_keyring(keyring_backend)

    @property
    def profile_path(self) -> Path:
        """Return the profile metadata path without exposing any contents."""
        return self._profile_path

    def save(self, email: str, refresh_token: str) -> str:
        """Persist a refresh token and return the selected storage backend."""
        if not email or not refresh_token:
            raise CredentialError("e-mail e token de sessão são obrigatórios")

        previous_keyring_email = self._previous_keyring_email()
        previous_keyring_token = None
        previous_keyring_removed = False
        if previous_keyring_email:
            if self._keyring is None:
                raise CredentialError(
                    "o cofre do sistema não está disponível para substituir a sessão"
                )
            try:
                previous_keyring_token = self._keyring.get_password(
                    self._service,
                    previous_keyring_email,
                )
            except Exception as exc:
                raise CredentialError(
                    "não foi possível acessar a sessão anterior no cofre"
                ) from exc
            if previous_keyring_email != email and previous_keyring_token:
                try:
                    self._keyring.delete_password(
                        self._service,
                        previous_keyring_email,
                    )
                    previous_keyring_removed = True
                except Exception as exc:
                    raise CredentialError(
                        "não foi possível remover a sessão anterior do cofre"
                    ) from exc
        storage = "file"
        metadata: dict[str, str] = {
            "email": email,
            "storage": storage,
        }
        if self._keyring is not None:
            try:
                self._keyring.set_password(self._service, email, refresh_token)
            except Exception as exc:  # pragma: no cover - backend-specific failures
                if previous_keyring_email:
                    if previous_keyring_removed and previous_keyring_token:
                        try:
                            self._keyring.set_password(
                                self._service,
                                previous_keyring_email,
                                previous_keyring_token,
                            )
                        except Exception:
                            self._keyring = None
                    raise CredentialError(
                        "não foi possível atualizar a sessão no cofre"
                    ) from exc
                self._keyring = None
            else:
                storage = "keyring"
                metadata["storage"] = storage
        if storage == "file":
            metadata["refresh_token"] = refresh_token

        try:
            self._write_private_json(metadata)
        except CredentialError:
            if storage == "keyring" and self._keyring is not None:
                try:
                    if previous_keyring_email == email and previous_keyring_token:
                        self._keyring.set_password(
                            self._service,
                            email,
                            previous_keyring_token,
                        )
                    else:
                        self._keyring.delete_password(self._service, email)
                        if previous_keyring_removed and previous_keyring_token:
                            self._keyring.set_password(
                                self._service,
                                previous_keyring_email,
                                previous_keyring_token,
                            )
                except Exception:
                    self._keyring = None
            raise
        return storage

    def load(self) -> StoredCredentials | None:
        """Load the current profile or return None when no login exists."""
        if not self._profile_path.exists():
            return None
        try:
            metadata = json.loads(self._profile_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CredentialError(
                f"perfil local inválido em {self._profile_path}; execute hubla-cli login"
            ) from exc
        if not isinstance(metadata, dict):
            raise CredentialError("perfil local inválido; execute hubla-cli login")
        email = metadata.get("email")
        storage = metadata.get("storage")
        if not isinstance(email, str) or not email:
            raise CredentialError("perfil local sem e-mail; execute hubla-cli login")

        refresh_token = None
        if storage == "keyring":
            if self._keyring is None:
                raise CredentialError(
                    "o cofre do sistema não está disponível; execute hubla-cli login"
                )
            try:
                refresh_token = self._keyring.get_password(self._service, email)
            except Exception as exc:  # pragma: no cover - backend-specific failures
                raise CredentialError(
                    "não foi possível acessar o cofre de credenciais do sistema"
                ) from exc
        elif storage == "file":
            refresh_token = metadata.get("refresh_token")
        else:
            raise CredentialError("perfil local com formato desconhecido")

        if not isinstance(refresh_token, str) or not refresh_token:
            raise CredentialError("sessão local ausente; execute hubla-cli login")
        return StoredCredentials(email=email, refresh_token=refresh_token)

    def delete(self) -> None:
        """Remove profile metadata and any corresponding keyring secret."""
        email = None
        storage = None
        if self._profile_path.exists():
            try:
                metadata = json.loads(self._profile_path.read_text(encoding="utf-8"))
                if isinstance(metadata, dict):
                    email = metadata.get("email")
                    storage = metadata.get("storage")
            except (OSError, json.JSONDecodeError) as exc:
                raise CredentialError("não foi possível ler o perfil local") from exc
        if storage == "keyring":
            if not isinstance(email, str) or not email:
                raise CredentialError("perfil local sem identidade do cofre")
            if self._keyring is None:
                raise CredentialError(
                    "o cofre do sistema não está disponível; o perfil foi preservado"
                )
            try:
                self._keyring.delete_password(self._service, email)
            except Exception as exc:
                if exc.__class__.__name__ != "PasswordDeleteError":
                    raise CredentialError(
                        "não foi possível remover a sessão do cofre; o perfil foi preservado"
                    ) from exc
        try:
            self._profile_path.unlink(missing_ok=True)
        except OSError as exc:
            raise CredentialError("não foi possível remover o perfil local") from exc

    @staticmethod
    def _resolve_keyring(backend: Any) -> Any:
        if backend is False:
            return None
        if backend is not None:
            return backend
        try:
            import keyring

            selected = keyring.get_keyring()
            if getattr(selected, "priority", 0) <= 0:
                return None
            return keyring
        except Exception:
            return None

    def _previous_keyring_email(self) -> str | None:
        if not self._profile_path.is_file():
            return None
        try:
            metadata = json.loads(self._profile_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(metadata, dict) or metadata.get("storage") != "keyring":
            return None
        email = metadata.get("email")
        return email if isinstance(email, str) and email else None

    def _write_private_json(self, metadata: dict[str, str]) -> None:
        directory = self._profile_path.parent
        try:
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            if os.name != "nt":
                directory.chmod(0o700)
            fd, temporary_name = tempfile.mkstemp(
                dir=directory,
                prefix=f".{self._profile}.",
                suffix=".tmp",
            )
            temporary_path = Path(temporary_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(metadata, handle, ensure_ascii=False, indent=2)
                    handle.write("\n")
                if os.name != "nt":
                    temporary_path.chmod(0o600)
                os.replace(temporary_path, self._profile_path)
                if os.name != "nt":
                    self._profile_path.chmod(0o600)
            finally:
                temporary_path.unlink(missing_ok=True)
        except OSError as exc:
            raise CredentialError("não foi possível salvar a sessão local") from exc
