"""Public exceptions raised by Hubla CLI."""

from __future__ import annotations

from typing import Any


class HublaError(Exception):
    """Base exception for Hubla CLI."""


class HublaAuthError(HublaError):
    """Raised when authentication cannot provide a valid token."""


class HublaNetworkError(HublaError):
    """Raised when a Hubla or Firebase endpoint cannot be reached."""


class CredentialError(HublaError):
    """Raised when local credential metadata is invalid or unavailable."""


class HublaHttpError(HublaError):
    """Raised when a Hubla endpoint returns an unsuccessful response."""

    def __init__(
        self,
        status_code: int,
        method: str,
        url: str,
        data: Any = None,
    ) -> None:
        self.status_code = status_code
        self.method = method
        self.url = url
        self.data = data
        super().__init__(f"Hubla HTTP {status_code} para {method} {url}")


class ConfirmationRequired(HublaError):
    """Raised before an operation that needs explicit confirmation."""


class CommandError(HublaError):
    """Raised when CLI command input is invalid."""
