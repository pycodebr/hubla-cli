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


class HublaContractError(HublaError):
    """Raised when live Hubla data cannot be reconciled safely."""


class ConfirmationRequired(HublaError):
    """Raised before an operation that needs explicit confirmation."""


class CommandError(HublaError):
    """Raised when CLI command input is invalid."""


class PaginationError(HublaError):
    """Raised when a paginated response cannot be reconciled safely."""


class CohortReadbackError(HublaError):
    """Raised when a cohort readback cannot be verified safely."""


class MemberLookupError(CohortReadbackError):
    """Raised when a member cannot be identified unambiguously."""


class MemberNotFoundError(MemberLookupError):
    """Raised when no member matches the requested product and e-mail."""


class MemberFilterIgnoredError(MemberLookupError):
    """Raised when the API returns data outside the requested member filter."""


class AmbiguousMemberError(MemberLookupError):
    """Raised when more than one member matches the requested identity."""
