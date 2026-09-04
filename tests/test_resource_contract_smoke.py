from __future__ import annotations

import inspect
from typing import Any

import pytest

from hubla_cli.catalog import RESOURCE_CLASSES
from hubla_cli.client import HublaClient
from hubla_cli.errors import ConfirmationRequired


class ContractTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        service: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        self.calls.append(
            {"service": service, "method": method, "path": path, **kwargs}
        )
        if path == "/filters/offers":
            return {
                "owner": [{"id": "offer-1"}],
                "affiliates": [],
                "partners": [],
            }
        if path == "/members/actives/list":
            return {
                "items": [
                    {
                        "id": "member-1",
                        "email": "email-1",
                        "cohortIds": ["item-1"],
                    }
                ],
                "itemsQuantityTotal": 1,
            }
        if path in {
            "/hub/sections/v2",
            "/invoices/list",
            "/subscriptions/list",
        } or path.endswith(("/offers", "/cohorts")):
            return {"items": [], "total": 0}
        if path == "/financial-statement/balance":
            return {
                "availableInCents": 0,
                "receivableInCents": 0,
                "reservedInCents": 0,
                "currency": "BRL",
            }
        if path == "/financial-statement/movements":
            return {"movements": []}
        return {"ok": True}


def _required_value(name: str, annotation: Any) -> Any:
    sequence_names = {
        "cohort_ids",
        "cohorts",
        "emails",
        "event_ids",
        "main_offer_ids",
        "member_ids",
        "new_cohorts",
        "offer_ids",
        "product_ids",
        "products",
        "sections",
        "tracks",
        "types",
        "user_ids",
    }
    if name == "members":
        return [{"memberId": "member-1", "currentCohorts": []}]
    if name == "member":
        return {"memberId": "member-1", "currentCohorts": []}
    if name == "payload":
        return {"name": "Exemplo", "id": "item-1"}
    if name == "filters" or name == "params":
        return {}
    if name in sequence_names:
        return ["item-1"]
    if name == "lifetime":
        return False
    if name in {"amount_in_cents", "days", "installments", "quantity"}:
        return 1
    if name == "period":
        return "daily"
    if name == "account_type":
        return "receivable"
    if name in {"start_date", "end_date"}:
        return "2026-01-01T00:00:00-03:00"
    if annotation is bool:
        return False
    if annotation is int:
        return 1
    return f"{name.replace('_', '-')}-1"


def _required_kwargs(method: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    for parameter in inspect.signature(method).parameters.values():
        if parameter.name == "confirm":
            kwargs["confirm"] = True
        elif parameter.default is inspect.Parameter.empty and parameter.kind not in {
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        }:
            kwargs[parameter.name] = _required_value(
                parameter.name,
                parameter.annotation,
            )
    return kwargs


@pytest.mark.parametrize(
    ("resource_name", "method_name"),
    [
        (resource_name, method_name)
        for resource_name, resource_class in RESOURCE_CLASSES.items()
        for method_name, method in inspect.getmembers(
            resource_class,
            predicate=inspect.isfunction,
        )
        if not method_name.startswith("_") and callable(method)
    ],
)
def test_every_catalog_operation_reaches_only_the_fake_transport(
    resource_name: str,
    method_name: str,
) -> None:
    transport = ContractTransport()
    client = HublaClient(transport=transport)
    method = getattr(getattr(client, resource_name), method_name)

    result = method(**_required_kwargs(method))
    if method_name.startswith("iter_"):
        list(result)

    assert transport.calls


@pytest.mark.parametrize(
    ("resource_name", "method_name"),
    [
        (resource_name, method_name)
        for resource_name, resource_class in RESOURCE_CLASSES.items()
        for method_name, method in inspect.getmembers(
            resource_class,
            predicate=inspect.isfunction,
        )
        if not method_name.startswith("_")
        and "confirm" in inspect.signature(method).parameters
    ],
)
def test_every_mutating_catalog_operation_is_blocked_without_confirmation(
    resource_name: str,
    method_name: str,
) -> None:
    client = HublaClient(transport=ContractTransport())
    method = getattr(getattr(client, resource_name), method_name)
    kwargs = _required_kwargs(method)
    kwargs["confirm"] = False

    with pytest.raises(ConfirmationRequired):
        method(**kwargs)
