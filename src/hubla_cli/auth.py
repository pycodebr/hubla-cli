"""Firebase authentication used by Hubla's public web application."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import requests

from hubla_cli.errors import HublaAuthError

FIREBASE_INIT_URL = "https://app.hub.la/__/firebase/init.json"
IDENTITY_TOOLKIT_URL = (
    "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
)
SECURE_TOKEN_URL = "https://securetoken.googleapis.com/v1/token"  # nosec B105
TOKEN_SAFETY_MARGIN_SECONDS = 60


@dataclass(frozen=True)
class AuthTokens:
    """Short-lived ID token and its renewable session token."""

    id_token: str
    refresh_token: str | None
    expires_at: float
    local_id: str | None = None


class FirebaseConfigResolver:
    """Resolve the public Firebase API key exposed by Hubla's web app."""

    def __init__(
        self,
        *,
        session: requests.Session | Any | None = None,
        init_url: str = FIREBASE_INIT_URL,
        timeout: float = 30,
    ) -> None:
        self._session = session or requests.Session()
        self._init_url = init_url
        self._timeout = timeout
        self._api_key: str | None = None

    def get_api_key(self) -> str:
        """Return and cache Hubla's public browser configuration key."""
        if self._api_key:
            return self._api_key
        try:
            response = self._session.get(self._init_url, timeout=self._timeout)
        except requests.RequestException as exc:
            raise HublaAuthError(
                "não foi possível consultar a configuração pública da Hubla"
            ) from exc
        if response.status_code >= 400:
            raise HublaAuthError(
                "não foi possível consultar a configuração pública da Hubla"
            )
        try:
            payload = response.json()
        except (TypeError, ValueError) as exc:
            raise HublaAuthError(
                "a configuração pública de autenticação da Hubla é inválida"
            ) from exc
        api_key = payload.get("apiKey") if isinstance(payload, dict) else None
        if not isinstance(api_key, str) or not api_key.strip():
            raise HublaAuthError(
                "a configuração pública da Hubla não informou a chave de autenticação"
            )
        self._api_key = api_key.strip()
        return self._api_key


class HublaAuth:
    """Authenticate with the same Firebase password flow used by Hubla."""

    def __init__(
        self,
        *,
        sign_key: str | None = None,
        email: str | None = None,
        password: str | None = None,
        refresh_token: str | None = None,
        session: requests.Session | Any | None = None,
        timeout: float = 30,
        clock: Callable[[], float] = time.time,
        config_resolver: FirebaseConfigResolver | None = None,
    ) -> None:
        self._sign_key = sign_key
        self._email = email
        self._password = password
        self._refresh_token = refresh_token
        self._session = session or requests.Session()
        self._timeout = timeout
        self._clock = clock
        self._tokens: AuthTokens | None = None
        self._config_resolver = config_resolver or FirebaseConfigResolver(
            session=self._session,
            timeout=timeout,
        )

    @classmethod
    def from_environment(
        cls,
        *,
        email: str | None = None,
        refresh_token: str | None = None,
        **kwargs: Any,
    ) -> HublaAuth:
        """Build authentication using explicit values, then environment values."""
        return cls(
            sign_key=os.getenv("HUBLA_SIGN_KEY"),
            email=email or os.getenv("HUBLA_EMAIL"),
            password=os.getenv("HUBLA_PASSWORD"),
            refresh_token=refresh_token or os.getenv("HUBLA_REFRESH_TOKEN"),
            **kwargs,
        )

    def login(self) -> AuthTokens:
        """Validate email/password credentials and return a renewable session."""
        self._validate_password_credentials()
        self._tokens = self._sign_in()
        return self._tokens

    def get_token(self, force_refresh: bool = False) -> str:
        """Return a valid ID token, refreshing or signing in when necessary."""
        if not force_refresh and self._tokens and self._is_valid(self._tokens):
            return self._tokens.id_token

        refresh_token = None
        if self._tokens and self._tokens.refresh_token:
            refresh_token = self._tokens.refresh_token
        elif self._refresh_token:
            refresh_token = self._refresh_token

        if refresh_token:
            try:
                self._tokens = self._refresh(refresh_token)
                return self._tokens.id_token
            except HublaAuthError:
                self._tokens = None

        self._validate_password_credentials()
        self._tokens = self._sign_in()
        return self._tokens.id_token

    def invalidate(self) -> None:
        """Invalidate only the short-lived token while preserving refresh ability."""
        if self._tokens and self._tokens.refresh_token:
            self._refresh_token = self._tokens.refresh_token
        self._tokens = None

    def _api_key(self) -> str:
        return self._sign_key or self._config_resolver.get_api_key()

    def _is_valid(self, tokens: AuthTokens) -> bool:
        return self._clock() < tokens.expires_at - TOKEN_SAFETY_MARGIN_SECONDS

    def _validate_password_credentials(self) -> None:
        missing = [
            name
            for name, value in (
                ("HUBLA_EMAIL", self._email),
                ("HUBLA_PASSWORD", self._password),
            )
            if not value
        ]
        if missing:
            raise HublaAuthError("credenciais ausentes: " + ", ".join(missing))

    def _sign_in(self) -> AuthTokens:
        try:
            response = self._session.post(
                IDENTITY_TOOLKIT_URL,
                params={"key": self._api_key()},
                json={
                    "returnSecureToken": True,
                    "email": self._email,
                    "password": self._password,
                    "clientType": "CLIENT_TYPE_WEB",
                },
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Client-Version": "Chrome/JsCore/11.4.0/FirebaseCore-web",
                },
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise HublaAuthError(
                "não foi possível conectar à autenticação da Hubla"
            ) from exc
        return self._parse_tokens(response, "idToken", "refreshToken")

    def _refresh(self, refresh_token: str) -> AuthTokens:
        try:
            response = self._session.post(
                SECURE_TOKEN_URL,
                params={"key": self._api_key()},
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise HublaAuthError("não foi possível renovar a sessão da Hubla") from exc
        return self._parse_tokens(response, "id_token", "refresh_token")

    def _parse_tokens(
        self,
        response: requests.Response | Any,
        id_key: str,
        refresh_key: str,
    ) -> AuthTokens:
        try:
            payload = response.json()
        except (TypeError, ValueError) as exc:
            raise HublaAuthError(
                "a autenticação da Hubla retornou resposta inválida"
            ) from exc
        if response.status_code >= 400:
            self._raise_safe_auth_error(payload)
        if not isinstance(payload, dict):
            raise HublaAuthError("a autenticação da Hubla retornou resposta inválida")

        id_token = payload.get(id_key)
        if not isinstance(id_token, str) or not id_token:
            if payload.get("mfaPendingCredential"):
                raise HublaAuthError(
                    "esta conta exige verificação adicional no portal da Hubla"
                )
            raise HublaAuthError("a Hubla não retornou uma sessão válida")
        try:
            expires_in = int(
                payload.get("expiresIn") or payload.get("expires_in") or 3600
            )
        except (TypeError, ValueError) as exc:
            raise HublaAuthError("a Hubla retornou uma sessão inválida") from exc
        refresh_token = payload.get(refresh_key) or self._refresh_token
        if refresh_token is not None and not isinstance(refresh_token, str):
            raise HublaAuthError("a Hubla retornou uma sessão inválida")
        if refresh_token:
            self._refresh_token = refresh_token
        local_id = payload.get("localId") or payload.get("user_id")
        return AuthTokens(
            id_token=id_token,
            refresh_token=refresh_token,
            expires_at=self._clock() + expires_in,
            local_id=str(local_id) if local_id is not None else None,
        )

    @staticmethod
    def _raise_safe_auth_error(payload: Any) -> None:
        code = ""
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                code = str(error.get("message", "")).upper()
        if "TOO_MANY_ATTEMPTS" in code or "BLOCKED" in code:
            message = "muitas tentativas de login; aguarde e tente novamente"
        elif "MFA" in code:
            message = "esta conta exige verificação adicional no portal da Hubla"
        else:
            message = "credenciais inválidas para a conta Hubla"
        raise HublaAuthError(message)
