"""Authenticated transport for Hubla's first-party API hosts."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

import requests

from hubla_cli.auth import HublaAuth
from hubla_cli.errors import HublaHttpError, HublaNetworkError
from hubla_cli.version import __version__

BASE_URLS = {
    "web": "https://backend-bff-web.platform.hub.la/api/v1",
    "product": "https://backend-bff-product.platform.hub.la/api/v1",
    "members_area": "https://backend-bff-members-area.platform.hub.la/api/v1",
    "access": "https://backend-bff-access.platform.hub.la/api/v1",
    "creators": "https://backend-bff-creators.platform.hub.la/api/v1",
    "crm": "https://backend-bff-web-crm.platform.hub.la/api/v1",
    "data": "https://backend-bff-data.platform.hub.la/api/v1",
    "pay": "https://bff-pay.platform.hub.la/v1",
    "member_portal": "https://backend-bff-member-portal.platform.hub.la/api/v1",
    "certificate": "https://bff-certificate.platform.hub.la",
    "functions": "https://us-central1-chatpay-cd120.cloudfunctions.net",
}

_SENSITIVE_KEYS = {
    "accesscode",
    "accesstoken",
    "apikey",
    "authorization",
    "captcha",
    "clientsecret",
    "cookie",
    "cpf",
    "cnpj",
    "document",
    "documentnumber",
    "email",
    "emails",
    "idtoken",
    "mfacode",
    "passwd",
    "password",
    "phone",
    "phonenumber",
    "receiveremail",
    "receiveremails",
    "refreshtoken",
    "secret",
    "token",
    "touseremail",
    "validationcode",
}


def redact_sensitive(value: Any, key: str = "") -> Any:
    """Redact common credential fields from provider error payloads."""
    normalized_key = "".join(
        character for character in key.lower() if character.isalnum()
    )
    if normalized_key in _SENSITIVE_KEYS:
        return "<redacted>"
    if isinstance(value, Mapping):
        return {
            str(item_key): redact_sensitive(item, str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    return value


class HublaTransport:
    """Authenticated JSON/bytes transport with one 401 refresh retry."""

    def __init__(
        self,
        auth: HublaAuth,
        *,
        session: requests.Session | Any | None = None,
        timeout: float = 30,
        request_id: bool = True,
    ) -> None:
        self._auth = auth
        self._session = session or requests.Session()
        self._timeout = timeout
        self._request_id = request_id

    def request(
        self,
        service: str,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        response_type: str = "json",
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Execute one request against an allowlisted Hubla service."""
        if response_type not in {"json", "text", "bytes"}:
            raise ValueError("response_type deve ser json, text ou bytes")
        url = self._build_url(service, path)
        method = method.upper()
        request_headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": f"hubla-cli/{__version__}",
        }
        if json is not None:
            request_headers["Content-Type"] = "application/json"
        if self._request_id:
            request_headers["x-request-id"] = str(uuid.uuid4())
        if headers:
            protected_headers = {
                "authorization",
                "cookie",
                "host",
                "proxy-authorization",
            }
            if any(name.lower() in protected_headers for name in headers):
                raise ValueError("não é permitido substituir cabeçalho protegido")
            request_headers.update(headers)

        response = None
        for attempt in range(2):
            attempt_headers = dict(request_headers)
            attempt_headers["Authorization"] = (
                f"Bearer {self._auth.get_token(force_refresh=attempt == 1)}"
            )
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    headers=attempt_headers,
                    timeout=self._timeout,
                    allow_redirects=False,
                )
            except requests.RequestException as exc:
                raise HublaNetworkError(
                    "não foi possível conectar ao serviço da Hubla"
                ) from exc
            if response.status_code != 401 or attempt == 1:
                break
            self._auth.invalidate()

        if response is None:  # pragma: no cover - loop invariant
            raise RuntimeError("nenhuma resposta recebida")
        if response.status_code >= 400:
            data = None
            try:
                data = redact_sensitive(response.json())
            except (TypeError, ValueError):
                pass
            raise HublaHttpError(response.status_code, method, url, data)
        if response_type == "bytes":
            return response.content
        if response.status_code == 204 or not response.content:
            return None
        if response_type == "text":
            return response.text
        try:
            return response.json()
        except (TypeError, ValueError) as exc:
            raise HublaHttpError(response.status_code, method, url) from exc

    @staticmethod
    def _build_url(service: str, path: str) -> str:
        if service not in BASE_URLS:
            raise ValueError(f"serviço Hubla desconhecido: {service}")
        parsed = urlsplit(path)
        has_control_character = any(
            ord(character) < 32 or ord(character) == 127 for character in path
        )
        if (
            parsed.scheme
            or parsed.netloc
            or path.startswith("//")
            or "\\" in path
            or has_control_character
        ):
            raise ValueError("use um caminho relativo dentro de um serviço Hubla")
        return BASE_URLS[service].rstrip("/") + "/" + path.lstrip("/")
