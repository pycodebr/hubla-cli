from __future__ import annotations

from typing import Any

import pytest

from hubla_cli.catalog import build_catalog, invoke_resource
from hubla_cli.client import HublaClient
from hubla_cli.errors import CommandError, ConfirmationRequired


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        service: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(
            {"service": service, "method": method, "path": path, **kwargs}
        )
        if path == "/filters/offers":
            return {"owner": [{"id": "offer-1"}]}
        return {"ok": True}


def test_catalog_exposes_every_resource_and_operation_metadata() -> None:
    catalog = build_catalog()

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
    } == set(catalog["resources"])
    refund = catalog["resources"]["sales"]["operations"]["refund"]
    assert refund["mutating"] is True
    assert refund["parameters"]["invoice_id"]["required"] is True
    assert refund["parameters"]["confirm"]["required"] is False
    assert catalog["resources"]["sales"]["operations"]["list"]["mutating"] is False
    assert (
        "start_date"
        in catalog["resources"]["sales"]["operations"]["summaries"]["parameters"]
    )
    assert (
        "offer_ids"
        in catalog["resources"]["sales"]["operations"]["export"]["parameters"]
    )
    assert catalog["resources"]["sales"]["operations"]["export"]["binary"] is True
    assert catalog["resources"]["sales"]["operations"]["list"]["binary"] is False


def test_dynamic_resource_call_executes_read_with_keyword_parameters() -> None:
    transport = FakeTransport()
    client = HublaClient(transport=transport)

    result = invoke_resource(
        client,
        "products",
        "list",
        {"page": 2, "page_size": 5},
    )

    assert result == {"ok": True}
    assert transport.calls[0]["params"]["page"] == 2
    assert transport.calls[0]["params"]["pageSize"] == 5


def test_dynamic_resource_call_cannot_invoke_private_methods() -> None:
    client = HublaClient(transport=FakeTransport())

    with pytest.raises(CommandError, match="operação desconhecida"):
        invoke_resource(client, "sales", "_call", {})


def test_dynamic_resource_call_cannot_smuggle_confirmation_in_json() -> None:
    client = HublaClient(transport=FakeTransport())

    with pytest.raises(ConfirmationRequired):
        invoke_resource(
            client,
            "sales",
            "refund",
            {"invoice_id": "invoice-1", "confirm": True},
            confirm=False,
        )


def test_dynamic_resource_call_adds_explicit_confirmation() -> None:
    transport = FakeTransport()
    client = HublaClient(transport=transport)

    invoke_resource(
        client,
        "sales",
        "refund",
        {"invoice_id": "invoice-1"},
        confirm=True,
    )

    assert transport.calls[0]["method"] == "PUT"
    assert transport.calls[0]["path"] == "/invoices/invoice-1/refund"


def test_dynamic_resource_call_reports_invalid_parameters_safely() -> None:
    client = HublaClient(transport=FakeTransport())

    with pytest.raises(CommandError, match="parâmetros inválidos"):
        invoke_resource(client, "products", "get", {"wrong": "value"})
