"""Base helpers for high-level Hubla resources."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from hubla_cli.errors import ConfirmationRequired


class ResourceBase:
    """Share safe transport and confirmation behavior across resources."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def _call(
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
        return self._client._request(
            service,
            method,
            path,
            params=params,
            json=json,
            response_type=response_type,
            headers=headers,
        )

    def _offer_selection(
        self,
        offer_ids: Any,
        has_selected_all: bool | None,
    ) -> dict[str, Any]:
        return self._client.resolve_offer_selection(offer_ids, has_selected_all)

    def _write(
        self,
        service: str,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Mapping[str, Any] | None = None,
        response_type: str = "json",
        confirm: bool = False,
    ) -> Any:
        if confirm is not True:
            raise ConfirmationRequired(
                f"ação de escrita bloqueada: {method} {path}; "
                "use confirmação explícita somente após revisar o alvo"
            )
        return self._call(
            service,
            method,
            path,
            params=params,
            json=json,
            response_type=response_type,
        )
