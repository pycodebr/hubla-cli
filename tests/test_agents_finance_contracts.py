from __future__ import annotations

from typing import Any

import pytest

from hubla_cli.client import HublaClient
from hubla_cli.errors import ConfirmationRequired, HublaContractError


class Transport:
    def __init__(self, responses: dict[str, list[Any]] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[dict[str, Any]] = []

    def request(self, service: str, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append(
            {"service": service, "method": method, "path": path, **kwargs}
        )
        if path in self.responses:
            return self.responses[path].pop(0)
        return {"ok": True}


def _entry(amount: str, kind: str, currency: str = "USD") -> dict[str, Any]:
    return {
        "consolidated": {
            "amountCents": amount,
            "transactionType": kind,
            "currency": currency,
            "referenceDate": {"year": 2026},
        }
    }


def test_usd_report_paginates_and_sums_signed_cents_without_conversion() -> None:
    transport = Transport(
        {
            "/financial-statement/account-statement": [
                {"entries": [_entry("125", "SALE")], "cursors": {"after": "cursor-1"}},
                {"entries": [_entry("-25", "REFUND"), _entry("375", "SALE")]},
            ],
            "/financial-statement/balance": [
                {"currency": "USD", "availableInCents": 50}
            ],
            "/financial-statement/withdrawal/exchange-rate": [{"fxRateCents": 512}],
        }
    )
    report = HublaClient(transport=transport).finance.wallet_report(
        start_date="2026-09-01T00:00:00-03:00",
        end_date="2026-09-27T23:59:59-03:00",
        page_size=1,
        include_exchange_rate=True,
    )

    assert report["currency"] == "USD"
    assert report["entryCount"] == 3
    assert report["totalsByTransactionType"] == {
        "SALE": {"count": 2, "amountCents": 500},
        "REFUND": {"count": 1, "amountCents": -25},
    }
    assert transport.calls[0]["params"]["currency"] == "USD"
    assert transport.calls[1]["params"]["after"] == "cursor-1"
    assert transport.calls[2]["params"] == {"currency": "USD"}
    assert transport.calls[3]["method"] == "GET"


def test_usd_report_rejects_mixed_currency_without_reporting_totals() -> None:
    transport = Transport(
        {
            "/financial-statement/account-statement": [
                {"entries": [_entry("100", "SALE", currency="BRL")]},
            ]
        }
    )
    with pytest.raises(HublaContractError, match="misturou moedas"):
        HublaClient(transport=transport).finance.wallet_report(
            start_date="2026-09-01T00:00:00-03:00",
            end_date="2026-09-27T23:59:59-03:00",
        )
    assert len(transport.calls) == 1


def test_wallet_report_preserves_movements_without_double_counting() -> None:
    transport = Transport(
        {
            "/financial-statement/account-statement": [
                {
                    "entries": [
                        {
                            "movement": {
                                "currency": "BRL",
                                "amountCents": "50",
                                "creditAccount": "account-a",
                                "debitAccount": "account-b",
                            }
                        },
                        _entry("-25", "FEE", currency="BRL"),
                    ]
                }
            ],
            "/financial-statement/balance": [{"currency": "BRL"}],
        }
    )
    report = HublaClient(transport=transport).finance.wallet_report(
        start_date="2026-09-01T00:00:00-03:00",
        end_date="2026-09-27T23:59:59-03:00",
        currency="BRL",
    )

    assert report["entryCount"] == 2
    assert report["movementCount"] == 1
    assert report["consolidatedCount"] == 1
    assert report["totalsByTransactionType"] == {
        "FEE": {"count": 1, "amountCents": -25},
    }
    assert len(report["entries"]) == 2


def test_wallet_report_rejects_movement_from_another_currency() -> None:
    transport = Transport(
        {
            "/financial-statement/account-statement": [
                {"entries": [{"movement": {"currency": "USD", "amountCents": "100"}}]}
            ],
        }
    )
    with pytest.raises(HublaContractError, match="misturou moedas"):
        HublaClient(transport=transport).finance.wallet_report(
            start_date="2026-09-01T00:00:00-03:00",
            end_date="2026-09-27T23:59:59-03:00",
            currency="BRL",
        )
    assert len(transport.calls) == 1


def test_wallet_report_rejects_repeated_cursor() -> None:
    transport = Transport(
        {
            "/financial-statement/account-statement": [
                {"entries": [_entry("100", "SALE")], "cursors": {"after": "same"}},
                {"entries": [_entry("100", "SALE")], "cursors": {"after": "same"}},
            ],
        }
    )
    with pytest.raises(HublaContractError, match="cursor"):
        HublaClient(transport=transport).finance.wallet_report(
            start_date="2026-09-01T00:00:00-03:00",
            end_date="2026-09-27T23:59:59-03:00",
        )


@pytest.mark.parametrize("currency", ["EUR", "USD/BRL", ""])
def test_wallet_report_rejects_unknown_currency_before_network(currency: str) -> None:
    transport = Transport()
    with pytest.raises(ValueError, match="BRL ou USD"):
        HublaClient(transport=transport).finance.wallet_report(
            start_date="2026-09-01T00:00:00-03:00",
            end_date="2026-09-27T23:59:59-03:00",
            currency=currency,
        )
    assert transport.calls == []


def test_agents_reads_use_confirmed_bffs_and_writes_require_confirmation() -> None:
    transport = Transport()
    client = HublaClient(transport=transport)
    client.agents_workflows.list(page=2, page_size=5, workflow_type="specialist")
    client.agents_conversations.list(page=1, page_size=4, statuses=["open"])
    client.agents_knowledge.list({"page": 1, "pageSize": 5})
    client.agents_insights.opportunities()

    assert [(c["service"], c["method"], c["path"]) for c in transport.calls] == [
        ("crm", "GET", "/workflows"),
        ("conversations", "POST", "/conversations/list"),
        ("crm", "POST", "/knowledge/list"),
        ("data", "POST", "/query/05bcd3c3-0e58-47b5-b0fe-9194cce6c91e"),
    ]
    assert transport.calls[0]["params"]["type"] == "specialist"
    assert transport.calls[1]["json"]["statuses"] == ["open"]
    with pytest.raises(ConfirmationRequired):
        client.agents_conversations.send_message({"content": "Olá"})
    with pytest.raises(ConfirmationRequired):
        client.agents_workflows.publish("workflow-1")
    assert len(transport.calls) == 4


def test_agent_ids_are_path_encoded_and_empty_ids_rejected() -> None:
    transport = Transport()
    client = HublaClient(transport=transport)
    client.agents_brains.get("brain/1")
    assert transport.calls[0]["path"] == "/brains/brain%2F1"
    with pytest.raises(ValueError, match="identificador"):
        client.agents_brains.get("")


def test_sales_rejects_invalid_wallet_and_currency_metric_uses_portal_value() -> None:
    transport = Transport()
    client = HublaClient(transport=transport)
    with pytest.raises(ValueError, match="minúsculas"):
        client.sales.list(
            offer_ids=["offer-1"],
            has_selected_all=False,
            wallet="INTERNATIONAL",
        )
    assert transport.calls == []

    client.analytics.average_ticket_by_currency(
        start_date="2026-09-26T00:00:00-03:00",
        end_date="2026-09-26T23:59:59-03:00",
        offer_ids=["offer-1"],
        has_selected_all=False,
    )
    assert transport.calls[0]["json"]["wallet"] == "international"


def test_agent_home_uses_bundle_metric_ids_and_period_filter() -> None:
    transport = Transport()
    report = HublaClient(transport=transport).agents_insights.home(
        start_date="2026-09-26", end_date="2026-09-27"
    )
    assert list(report) == [
        "period",
        "agentsMetricsDaily",
        "agentsBreakdown",
        "opportunities",
    ]
    assert [call["path"] for call in transport.calls] == [
        "/query/7c9e4b2a-1d3f-4a8c-9b6e-2f5a8c1d7e30",
        "/query/b3f8d6c1-4e2a-4d9b-8c7f-1a6e3b2d5c40",
        "/query/05bcd3c3-0e58-47b5-b0fe-9194cce6c91e",
    ]
    assert transport.calls[0]["json"]["where"]["date"] == {
        "$gte": "2026-09-26 00:00:00",
        "$lte": "2026-09-27 23:59:59",
    }
