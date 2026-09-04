"""Python client and terminal interface for Hubla accounts."""

from hubla_cli.auth import AuthTokens, FirebaseConfigResolver, HublaAuth
from hubla_cli.client import HublaClient
from hubla_cli.errors import (
    AmbiguousMemberError,
    CohortReadbackError,
    CommandError,
    ConfirmationRequired,
    CredentialError,
    HublaAuthError,
    HublaError,
    HublaHttpError,
    HublaNetworkError,
    MemberFilterIgnoredError,
    MemberLookupError,
    MemberNotFoundError,
    PaginationError,
)
from hubla_cli.pagination import PaginatedResult, PaginationResult, collect_paginated
from hubla_cli.version import __version__

__all__ = [
    "AuthTokens",
    "AmbiguousMemberError",
    "CohortReadbackError",
    "CommandError",
    "ConfirmationRequired",
    "CredentialError",
    "FirebaseConfigResolver",
    "HublaAuth",
    "HublaAuthError",
    "HublaClient",
    "HublaError",
    "HublaHttpError",
    "HublaNetworkError",
    "MemberFilterIgnoredError",
    "MemberLookupError",
    "MemberNotFoundError",
    "PaginationError",
    "PaginatedResult",
    "PaginationResult",
    "collect_paginated",
    "__version__",
]
