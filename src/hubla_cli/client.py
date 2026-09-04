"""High-level Hubla client."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from typing import Any

from hubla_cli.auth import HublaAuth
from hubla_cli.credentials import CredentialStore
from hubla_cli.errors import ConfirmationRequired, CredentialError
from hubla_cli.resources import (
    AccountResource,
    AffiliatesResource,
    AnalyticsResource,
    CouponsResource,
    FinanceResource,
    GroupsResource,
    IntegrationsResource,
    MembersAreaContentsResource,
    MembersResource,
    ProductsResource,
    RefundsResource,
    SalesResource,
    StorefrontsResource,
    SubscriptionsResource,
)
from hubla_cli.transport import HublaTransport


class HublaClient:
    """Client for Hubla creator and member resources."""

    def __init__(
        self,
        *,
        auth: HublaAuth | None = None,
        transport: Any | None = None,
        timeout: float | None = None,
        request_id: bool | None = None,
    ) -> None:
        if transport is None:
            auth = auth or HublaAuth.from_environment()
            timeout = (
                timeout
                if timeout is not None
                else float(os.getenv("HUBLA_TIMEOUT", "30"))
            )
            request_id = (
                request_id
                if request_id is not None
                else os.getenv("HUBLA_REQUEST_ID", "true").lower() == "true"
            )
            transport = HublaTransport(
                auth,
                timeout=timeout,
                request_id=request_id,
            )
        self._transport = transport
        self._offer_ids_cache: list[str] | None = None
        self.account = AccountResource(self)
        self.affiliates = AffiliatesResource(self)
        self.analytics = AnalyticsResource(self)
        self.coupons = CouponsResource(self)
        self.finance = FinanceResource(self)
        self.groups = GroupsResource(self)
        self.integrations = IntegrationsResource(self)
        self.members = MembersResource(self)
        self.members_area_contents = MembersAreaContentsResource(self)
        self.products = ProductsResource(self)
        self.refunds = RefundsResource(self)
        self.sales = SalesResource(self)
        self.storefronts = StorefrontsResource(self)
        self.subscriptions = SubscriptionsResource(self)

    @classmethod
    def from_profile(
        cls,
        *,
        profile: str = "default",
        credential_store: CredentialStore | None = None,
        **kwargs: Any,
    ) -> HublaClient:
        """Build a client from environment variables or a saved login profile."""
        env_email = os.getenv("HUBLA_EMAIL")
        env_password = os.getenv("HUBLA_PASSWORD")
        env_refresh = os.getenv("HUBLA_REFRESH_TOKEN")
        if env_refresh or (env_email and env_password):
            return cls(
                auth=HublaAuth.from_environment(
                    email=env_email,
                    refresh_token=env_refresh,
                ),
                **kwargs,
            )
        store = credential_store or CredentialStore(profile=profile)
        credentials = store.load()
        if credentials is None:
            raise CredentialError(
                f"nenhum login encontrado para o perfil '{profile}'; "
                "execute hubla-cli login"
            )
        return cls(
            auth=HublaAuth.from_environment(
                email=credentials.email,
                refresh_token=credentials.refresh_token,
            ),
            **kwargs,
        )

    def resolve_offer_selection(
        self,
        offer_ids: Sequence[str] | None,
        has_selected_all: bool | None,
    ) -> dict[str, Any]:
        """Resolve explicit offer IDs or discover all visible account offers."""
        if has_selected_all is False:
            return {"offerIds": list(offer_ids or []), "hasSelectedAll": False}
        if offer_ids:
            return {
                "offerIds": list(offer_ids),
                "hasSelectedAll": bool(has_selected_all),
            }
        if self._offer_ids_cache is None:
            self._offer_ids_cache = self._fetch_all_offer_ids()
        if not self._offer_ids_cache:
            raise ValueError("a conta Hubla não possui ofertas disponíveis")
        return {
            "offerIds": list(self._offer_ids_cache),
            "hasSelectedAll": True,
        }

    def all_offer_ids(self, refresh: bool = False) -> list[str]:
        """Return every visible owner, affiliate, and partner offer ID."""
        if refresh or self._offer_ids_cache is None:
            self._offer_ids_cache = self._fetch_all_offer_ids()
        return list(self._offer_ids_cache)

    def _fetch_all_offer_ids(self) -> list[str]:
        payload = self.products.global_offers()
        if not isinstance(payload, Mapping):
            return []
        offer_ids: list[str] = []
        for group_name in ("owner", "affiliates", "partners"):
            group = payload.get(group_name, [])
            if not isinstance(group, Sequence) or isinstance(group, (str, bytes)):
                continue
            for offer in group:
                if isinstance(offer, Mapping) and offer.get("id"):
                    offer_ids.append(str(offer["id"]))
        return list(dict.fromkeys(offer_ids))

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
        """Perform a read-only raw GET against an allowlisted Hubla service."""
        if method.upper() != "GET":
            raise ConfirmationRequired(
                f"chamada raw bloqueada: {method} {path}; use "
                "client.write(..., confirm=True)"
            )
        return self._request(
            service,
            method,
            path,
            params=params,
            json=json,
            response_type=response_type,
            headers=headers,
        )

    def _request(
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
        return self._transport.request(
            service,
            method,
            path,
            params=params,
            json=json,
            response_type=response_type,
            headers=headers,
        )

    def write(
        self,
        service: str,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        response_type: str = "json",
        confirm: bool = False,
    ) -> Any:
        """Perform an explicitly confirmed request that may change account state."""
        if confirm is not True:
            raise ConfirmationRequired(
                f"ação de escrita bloqueada: {method} {path}; "
                "use confirmação explícita somente após revisar o alvo"
            )
        return self._request(
            service,
            method,
            path,
            params=params,
            json=json,
            response_type=response_type,
        )
