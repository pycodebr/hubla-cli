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
            {
                "service": service,
                "method": method,
                "path": path,
                **kwargs,
            }
        )
        return {"ok": True}


class OfferAwareTransport(FakeTransport):
    def request(
        self,
        service: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "service": service,
                "method": method,
                "path": path,
                **kwargs,
            }
        )
        if path == "/filters/offers":
            return {
                "owner": [{"id": "offer-1"}],
                "affiliates": [{"id": "offer-2"}],
                "partners": [{"id": "offer-1"}],
            }
        return {"ok": True}


def test_client_exposes_all_resource_groups() -> None:
    client = HublaClient(transport=FakeTransport())

    assert {
        "account",
        "affiliates",
        "analytics",
        "coupons",
        "finance",
        "groups",
        "integrations",
        "members",
        "products",
        "refunds",
        "sales",
        "storefronts",
        "subscriptions",
    } <= set(vars(client))


def test_sales_list_matches_portal_contract() -> None:
    transport = FakeTransport()
    client = HublaClient(transport=transport)

    result = client.sales.list(
        offer_ids=["offer-1"],
        has_selected_all=False,
        start_date="2026-01-01T00:00:00-03:00",
        end_date="2026-01-31T23:59:59-03:00",
        statuses=["paid"],
        search="cliente@example.com",
        page=2,
        page_size=25,
    )

    assert result == {"ok": True}
    call = transport.calls[0]
    assert call["service"] == "web"
    assert call["method"] == "POST"
    assert call["path"] == "/invoices/list"
    assert call["json"]["offerIds"] == ["offer-1"]
    assert call["json"]["hasSelectedAll"] is False
    assert call["json"]["filters"]["search"] == "cliente@example.com"
    assert call["json"]["filters"]["status"] == ["paid"]
    assert call["json"]["page"] == 2
    assert call["json"]["pageSize"] == 25


def test_all_offer_ids_are_discovered_deduplicated_and_cached() -> None:
    transport = OfferAwareTransport()
    client = HublaClient(transport=transport)

    assert client.all_offer_ids() == ["offer-1", "offer-2"]
    assert client.all_offer_ids() == ["offer-1", "offer-2"]
    assert [call["path"] for call in transport.calls] == ["/filters/offers"]


def test_refund_requires_explicit_confirmation() -> None:
    client = HublaClient(transport=FakeTransport())

    with pytest.raises(ConfirmationRequired, match="invoice-1"):
        client.sales.refund("invoice-1")


@pytest.mark.parametrize("invalid_confirmation", [1, "true", "false", object()])
def test_resource_confirmation_requires_literal_true(
    invalid_confirmation: Any,
) -> None:
    client = HublaClient(transport=FakeTransport())

    with pytest.raises(ConfirmationRequired):
        client.sales.refund("invoice-1", confirm=invalid_confirmation)


def test_raw_write_requires_explicit_confirmation() -> None:
    client = HublaClient(transport=FakeTransport())

    with pytest.raises(ConfirmationRequired, match="ação de escrita"):
        client.write("web", "PATCH", "/known-route")


@pytest.mark.parametrize("invalid_confirmation", [1, "true", "false", object()])
def test_raw_write_confirmation_requires_literal_true(
    invalid_confirmation: Any,
) -> None:
    client = HublaClient(transport=FakeTransport())

    with pytest.raises(ConfirmationRequired):
        client.write(
            "web",
            "PATCH",
            "/known-route",
            confirm=invalid_confirmation,
        )


def test_public_raw_request_cannot_bypass_confirmation_for_non_get() -> None:
    client = HublaClient(transport=FakeTransport())

    with pytest.raises(ConfirmationRequired, match="client.write"):
        client.request("web", "POST", "/known-route")


def test_members_create_free_subscription_builds_expected_body() -> None:
    transport = FakeTransport()
    client = HublaClient(transport=transport)

    client.members.create_free_subscription(
        product_id="product-1",
        offer_id="offer-1",
        emails=["member@example.com"],
        days=30,
        lifetime=False,
        confirm=True,
    )

    call = transport.calls[0]
    assert call["service"] == "members_area"
    assert call["method"] == "POST"
    assert call["path"] == "/members/create-invites-free-subscription"
    assert call["json"] == {
        "productId": "product-1",
        "receiverEmails": ["member@example.com"],
        "days": 30,
        "lifetime": False,
        "offerId": "offer-1",
    }


def test_offer_update_quotes_ids_and_preserves_payload() -> None:
    transport = FakeTransport()
    client = HublaClient(transport=transport)

    client.products.update_offer(
        product_id="product/one",
        offer_id="offer one",
        payload={"name": "Nova oferta"},
        confirm=True,
    )

    call = transport.calls[0]
    assert call["method"] == "PUT"
    assert call["path"] == "/products/product%2Fone/offers/offer%20one/edit"
    assert call["json"] == {"name": "Nova oferta"}
