from __future__ import annotations

from typing import Any

import pytest

from hubla_cli.client import HublaClient
from hubla_cli.errors import (
    AmbiguousMemberError,
    MemberNotFoundError,
    PaginationError,
)


class RoutingTransport:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        service: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        call = {"service": service, "method": method, "path": path, **kwargs}
        self.calls.append(call)
        response = self.responses[path]
        if callable(response):
            return response(call)
        return response


def _page(call: dict[str, Any]) -> int:
    body = call.get("json")
    if isinstance(body, dict) and "page" in body:
        return int(body["page"])
    params = call.get("params")
    if isinstance(params, dict):
        return int(params["page"])
    raise AssertionError("page was not sent")


def test_sales_all_collects_every_page_and_preserves_filters() -> None:
    responses = {
        "/invoices/list": lambda call: {
            "data": {
                "rows": (
                    [{"id": "sale-1"}, {"id": "sale-2"}]
                    if _page(call) == 1
                    else [{"id": "sale-3"}]
                )
            },
            "meta": {"total": 3},
        },
    }
    transport = RoutingTransport(responses)
    client = HublaClient(transport=transport)

    result = client.sales.all(
        offer_ids=["offer-1"],
        has_selected_all=False,
        statuses=["paid"],
        page_size=2,
    )

    assert result == [
        {"id": "sale-1"},
        {"id": "sale-2"},
        {"id": "sale-3"},
    ]
    assert [_page(call) for call in transport.calls] == [1, 2]
    assert all(call["json"]["pageSize"] == 2 for call in transport.calls)
    assert all(call["json"]["offerIds"] == ["offer-1"] for call in transport.calls)
    assert all(call["json"]["hasSelectedAll"] is False for call in transport.calls)


def test_sales_iter_all_is_deferred_and_preserves_every_filter() -> None:
    responses = {
        "/invoices/list": lambda call: {
            "rows": ([{"id": "sale-1"}] if _page(call) == 1 else [{"id": "sale-2"}]),
            "total": 2,
        },
    }
    transport = RoutingTransport(responses)
    client = HublaClient(transport=transport)

    iterator = client.sales.iter_all(
        offer_ids=["offer-1"],
        has_selected_all=False,
        start_date="2026-01-01T00:00:00-03:00",
        end_date="2026-01-31T23:59:59-03:00",
        statuses=["paid"],
        types=["one-time"],
        methods=["card"],
        search="sale-key",
        utm_source="source",
        utm_medium="medium",
        utm_campaign="campaign",
        utm_content="content",
        utm_term="term",
        date_range_by="createdAt",
        wallet="wallet-1",
        page_size=1,
        order_by="paidAt",
        order_direction="ASC",
    )

    assert transport.calls == []
    assert list(iterator) == [{"id": "sale-1"}, {"id": "sale-2"}]
    assert len(transport.calls) == 2
    for call in transport.calls:
        body = call["json"]
        assert body["offerIds"] == ["offer-1"]
        assert body["hasSelectedAll"] is False
        assert body["pageSize"] == 1
        assert body["orderBy"] == "paidAt"
        assert body["orderDirection"] == "ASC"
        assert body["filters"] == {
            "startDate": "2026-01-01T00:00:00-03:00",
            "endDate": "2026-01-31T23:59:59-03:00",
            "status": ["paid"],
            "type": ["one-time"],
            "paymentMethod": ["card"],
            "search": "sale-key",
            "utmSource": "source",
            "utmMedium": "medium",
            "utmCampaign": "campaign",
            "utmContent": "content",
            "utmTerm": "term",
            "dateRangeBy": "createdAt",
            "wallet": "wallet-1",
        }


def test_subscriptions_all_collects_rows_until_the_provider_total() -> None:
    responses = {
        "/subscriptions/list": lambda call: {
            "rows": ([{"id": "sub-1"}] if _page(call) == 1 else [{"id": "sub-2"}]),
            "pagination": {"totalItems": 2},
        },
    }
    transport = RoutingTransport(responses)
    client = HublaClient(transport=transport)

    assert client.subscriptions.all(
        offer_ids=["offer-1"],
        has_selected_all=False,
        page_size=1,
    ) == [{"id": "sub-1"}, {"id": "sub-2"}]
    assert [_page(call) for call in transport.calls] == [1, 2]


def test_subscriptions_iter_all_is_deferred_and_preserves_every_filter() -> None:
    responses = {
        "/subscriptions/list": lambda call: {
            "rows": ([{"id": "sub-1"}] if _page(call) == 1 else [{"id": "sub-2"}]),
            "total": 2,
        },
    }
    transport = RoutingTransport(responses)
    client = HublaClient(transport=transport)

    iterator = client.subscriptions.iter_all(
        offer_ids=["offer-1"],
        has_selected_all=False,
        start_date="2026-01-01T00:00:00-03:00",
        end_date="2026-01-31T23:59:59-03:00",
        statuses=["active"],
        search="subscription-key",
        date_range_by="createdAt",
        plan_type="recurring",
        is_free_trial_active=True,
        page_size=1,
        order_by="startedAt",
        order_direction="ASC",
    )

    assert transport.calls == []
    assert list(iterator) == [{"id": "sub-1"}, {"id": "sub-2"}]
    assert len(transport.calls) == 2
    for call in transport.calls:
        body = call["json"]
        assert body["offerIds"] == ["offer-1"]
        assert body["hasSelectedAll"] is False
        assert body["pageSize"] == 1
        assert body["orderBy"] == "startedAt"
        assert body["orderDirection"] == "ASC"
        assert body["filters"] == {
            "search": "subscription-key",
            "status": ["active"],
            "startDate": "2026-01-01T00:00:00-03:00",
            "endDate": "2026-01-31T23:59:59-03:00",
            "dateRangeBy": "createdAt",
            "planType": "recurring",
            "isFreeTrialActive": True,
        }


def test_members_all_reconciles_before_applying_client_side_cohort_filter() -> None:
    responses = {
        "/members/actives/list": lambda call: {
            "items": (
                [
                    {"id": "member-1", "cohortIds": ["cohort-1"]},
                    {"id": "member-2", "cohortIds": ["cohort-2"]},
                ]
                if _page(call) == 1
                else [{"id": "member-3", "cohortIds": ["cohort-1", "cohort-3"]}]
            ),
            "itemsQuantityTotal": 3,
        },
    }
    transport = RoutingTransport(responses)
    client = HublaClient(transport=transport)

    result = client.members.all(
        product_id="product-1",
        cohort_ids=["cohort-1"],
        page_size=2,
    )

    assert result == [
        {"id": "member-1", "cohortIds": ["cohort-1"]},
        {"id": "member-3", "cohortIds": ["cohort-1", "cohort-3"]},
    ]
    assert all(call["params"]["cohortIds"] == [] for call in transport.calls)


def test_members_iter_all_is_deferred_and_filters_only_after_full_product_collection() -> (
    None
):
    responses = {
        "/members/actives/list": lambda call: {
            "items": (
                [{"id": "member-1", "cohortIds": ["cohort-2"]}]
                if _page(call) == 1
                else [{"id": "member-2", "cohortIds": ["cohort-1"]}]
            ),
            "itemsQuantityTotal": 2,
        },
    }
    transport = RoutingTransport(responses)
    client = HublaClient(transport=transport)

    iterator = client.members.iter_all(
        "product-1",
        types=["student"],
        search="member-key",
        cohort_ids=["cohort-1"],
        page_size=1,
    )

    assert transport.calls == []
    assert list(iterator) == [{"id": "member-2", "cohortIds": ["cohort-1"]}]
    assert len(transport.calls) == 2
    for call in transport.calls:
        assert call["params"]["productId"] == "product-1"
        assert call["params"]["types"] == ["student"]
        assert call["params"]["search"] == "member-key"
        assert call["params"]["cohortIds"] == []
        assert call["params"]["includeItemsQuantityTotal"] is True


def test_members_all_rejects_missing_provider_total_before_filtering() -> None:
    transport = RoutingTransport(
        {
            "/members/actives/list": {
                "items": [{"id": "member-1", "cohortIds": ["cohort-1"]}],
            }
        }
    )
    client = HublaClient(transport=transport)

    with pytest.raises(PaginationError, match="total"):
        client.members.all(product_id="product-1", cohort_ids=["cohort-1"])


def test_member_readback_matches_one_email_and_normalizes_cohort_ids() -> None:
    transport = RoutingTransport(
        {
            "/members/actives/list": {
                "items": [
                    {
                        "id": "member-1",
                        "user": {"email": "Target@Example.com"},
                        "currentCohorts": [
                            {"id": "cohort-1"},
                            {"cohortId": "cohort-2"},
                            "cohort-1",
                        ],
                    },
                    {
                        "id": "member-2",
                        "email": "other@example.com",
                        "cohortIds": ["cohort-3"],
                    },
                ],
                "itemsQuantityTotal": 2,
            }
        }
    )
    client = HublaClient(transport=transport)

    assert client.members.get_current_cohort_ids("product-1", "target@example.com") == [
        "cohort-1",
        "cohort-2",
    ]
    assert transport.calls[0]["params"]["search"] == "target@example.com"
    assert transport.calls[0]["params"]["cohortIds"] == []


def test_member_readback_rejects_no_match_and_multiple_matches() -> None:
    no_match = RoutingTransport(
        {
            "/members/actives/list": {
                "items": [{"id": "member-1", "email": "other@example.com"}],
                "total": 1,
            }
        }
    )
    with pytest.raises(MemberNotFoundError):
        HublaClient(transport=no_match).members.get_current_cohort_ids(
            "product-1", "target@example.com"
        )

    multiple = RoutingTransport(
        {
            "/members/actives/list": {
                "items": [
                    {"id": "member-1", "email": "target@example.com"},
                    {"id": "member-2", "email": "TARGET@example.com"},
                ],
                "total": 2,
            }
        }
    )
    with pytest.raises(AmbiguousMemberError):
        HublaClient(transport=multiple).members.get_member_cohort_ids(
            "product-1", "target@example.com"
        )


def test_products_all_methods_collect_offers_and_cohorts() -> None:
    responses = {
        "/products/product-1/offers": lambda call: {
            "items": ([{"id": "offer-1"}] if _page(call) == 1 else [{"id": "offer-2"}]),
            "total": 2,
        },
        "/products/product-1/cohorts": lambda call: {
            "data": (
                [{"id": "cohort-1"}] if _page(call) == 1 else [{"id": "cohort-2"}]
            ),
            "totalCount": 2,
        },
    }
    transport = RoutingTransport(responses)
    client = HublaClient(transport=transport)

    assert client.products.all_offers("product-1", page_size=1) == [
        {"id": "offer-1"},
        {"id": "offer-2"},
    ]
    assert client.products.all_cohorts("product-1", page_size=1) == [
        {"id": "cohort-1"},
        {"id": "cohort-2"},
    ]
    assert [_page(call) for call in transport.calls] == [1, 2, 1, 2]
