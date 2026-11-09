"""Transport for Hubla's official Public API (integration token, no portal login)."""

from __future__ import annotations

import os
import re
import time
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import quote, urlsplit

import requests

from hubla_cli.errors import HublaAuthError, HublaHttpError, HublaNetworkError
from hubla_cli.transport import redact_sensitive
from hubla_cli.version import __version__

PUBLIC_BASE_URL = "https://backend-bff-public-api.platform.hub.la"
TOKEN_ENV = "HUBLA_API_TOKEN"  # nosec B105

# POST routes that only read data (listings with complex filters in the body).
READ_POST_PATHS = frozenset(
    {
        "/v1/products/list",
        "/v1/invoices/list",
        "/v1/coupons/list",
        "/v1/leads/list",
        "/v1/refunds/list",
        "/v1/smart-installments/list",
    }
)

_DEFAULT_THROTTLE_WAITS = (2.0, 5.0, 10.0, 20.0)


def quote_id(value: Any) -> str:
    """Quote one external identifier for use as a single path segment."""
    return quote(str(value), safe="")


def is_read_request(method: str, path: str) -> bool:
    """Return whether a Public API call cannot change account state."""
    method = method.upper()
    return method == "GET" or (method == "POST" and path in READ_POST_PATHS)


def validate_token(token: Any) -> str:
    """Reject empty tokens, whitespace and a pasted ``Bearer`` prefix."""
    if not isinstance(token, str) or not token:
        raise HublaAuthError(
            f"token da API pública ausente; defina {TOKEN_ENV} ou execute "
            "hubla-cli login --api-token"
        )
    if token != token.strip() or re.search(r"\s", token):
        raise HublaAuthError("o token da API pública contém espaços")
    if token.lower().startswith("bearer"):
        raise HublaAuthError("informe o token puro, sem o prefixo Bearer")
    return token


class PublicApiTransport:
    """JSON transport for the Public API with bounded waits on HTTP 429 for reads.

    The integration token goes raw in the ``Authorization`` header, as documented
    by Hubla. Reads that receive HTTP 429 wait (``Retry-After`` when present) and
    retry a bounded number of times; writes are never retried.
    """

    def __init__(
        self,
        token: str,
        *,
        session: requests.Session | Any | None = None,
        timeout: float = 30,
        throttle_waits: tuple[float, ...] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._token = validate_token(token)
        self._session = session or requests.Session()
        self._timeout = timeout
        self._throttle_waits = (
            _DEFAULT_THROTTLE_WAITS if throttle_waits is None else throttle_waits
        )
        self._sleep = sleep
        self.calls = 0

    @classmethod
    def from_environment(cls, **kwargs: Any) -> PublicApiTransport:
        return cls(os.getenv(TOKEN_ENV, ""), **kwargs)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        method = method.upper()
        url = self._build_url(path)
        headers = {
            "Accept": "application/json",
            "Authorization": self._token,
            "User-Agent": f"hubla-cli/{__version__}",
        }
        if json is not None:
            headers["Content-Type"] = "application/json"
        read = is_read_request(method, path)
        waits = list(self._throttle_waits) if read else []
        while True:
            self.calls += 1
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=self._timeout,
                    allow_redirects=False,
                )
            except requests.RequestException as exc:
                raise HublaNetworkError(
                    "não foi possível conectar à API pública da Hubla"
                ) from exc
            if response.status_code == 429 and waits:
                wait = waits.pop(0)
                retry_after = response.headers.get("Retry-After", "")
                if re.fullmatch(r"[0-9]{1,3}", retry_after or ""):
                    wait = max(wait, float(retry_after))
                self._sleep(wait)
                continue
            break
        if response.status_code >= 400:
            data = None
            try:
                data = redact_sensitive(response.json())
            except (TypeError, ValueError):
                pass
            raise HublaHttpError(response.status_code, method, url, data)
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except (TypeError, ValueError) as exc:
            raise HublaHttpError(response.status_code, method, url) from exc

    @staticmethod
    def _build_url(path: str) -> str:
        parsed = urlsplit(path)
        has_control_character = any(
            ord(character) < 32 or ord(character) == 127 for character in path
        )
        if (
            parsed.scheme
            or parsed.netloc
            or parsed.query
            or path.startswith("//")
            or "\\" in path
            or has_control_character
            or any(part in {".", ".."} for part in path.split("/"))
        ):
            raise ValueError("use um caminho relativo da API pública, sem query string")
        if not path.startswith("/v1/"):
            raise ValueError("os caminhos da API pública começam com /v1/")
        return PUBLIC_BASE_URL + path
