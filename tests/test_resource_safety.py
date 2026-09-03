from __future__ import annotations

from typing import Any

import pytest

from hubla_cli.client import HublaClient
from hubla_cli.errors import ConfirmationRequired


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        service: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, bool]:
        self.calls.append(
            {"service": service, "method": method, "path": path, **kwargs}
        )
        return {"ok": True}


@pytest.mark.parametrize(
    ("resource_name", "method_name", "args"),
    [
        ("refunds", "accept", ("refund-1",)),
        ("subscriptions", "deactivate", ("subscription-1",)),
        ("products", "delete", ("product-1",)),
        ("members", "remove_free_subscription", ("product-1", "user-1")),
        ("finance", "withdraw", (1000,)),
        ("integrations", "delete", ("integration-1",)),
        ("coupons", "delete", ("coupon-1",)),
        ("storefronts", "create", ({"name": "Vitrine"},)),
        ("account", "remove_collaborator", ("collaborator-1",)),
        ("groups", "remove_whitelist_member", ({"id": "member-1"},)),
    ],
)
def test_state_changing_resources_require_confirmation(
    resource_name: str,
    method_name: str,
    args: tuple[Any, ...],
) -> None:
    client = HublaClient(transport=FakeTransport())
    method = getattr(getattr(client, resource_name), method_name)

    with pytest.raises(ConfirmationRequired):
        method(*args)


def test_sales_export_is_treated_as_sensitive_and_requires_confirmation() -> None:
    client = HublaClient(transport=FakeTransport())

    with pytest.raises(ConfirmationRequired):
        client.sales.export(offer_ids=["offer-1"], has_selected_all=False)


def test_starting_mfa_requires_confirmation() -> None:
    client = HublaClient(transport=FakeTransport())

    with pytest.raises(ConfirmationRequired):
        client.account.start_mfa()
