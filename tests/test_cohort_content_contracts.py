from __future__ import annotations

from typing import Any

import pytest

from hubla_cli.catalog import build_catalog
from hubla_cli.client import HublaClient
from hubla_cli.errors import (
    AmbiguousMemberError,
    CohortReadbackError,
    MemberFilterIgnoredError,
)


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: dict[str, Any] = {}

    def request(
        self,
        service: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        call = {"service": service, "method": method, "path": path, **kwargs}
        self.calls.append(call)
        result = self.responses.get(path, {"ok": True})
        return result(call) if callable(result) else result


def test_get_cohort_reads_the_product_cohort_detail_route() -> None:
    transport = FakeTransport()
    transport.responses["/products/product-1/cohorts/cohort-1"] = {
        "id": "cohort-1",
        "name": "Turma 1",
        "resources": [],
    }
    client = HublaClient(transport=transport)

    result = client.products.get_cohort("product-1", "cohort-1")

    assert result == {
        "id": "cohort-1",
        "name": "Turma 1",
        "resources": [],
    }
    assert transport.calls == [
        {
            "service": "product",
            "method": "GET",
            "path": "/products/product-1/cohorts/cohort-1",
            "params": None,
            "json": None,
            "response_type": "json",
            "headers": None,
        }
    ]


def test_members_area_contents_resource_is_exposed_and_lists_sections() -> None:
    transport = FakeTransport()
    transport.responses["/hub/sections/v2"] = {
        "items": [{"id": "section-1", "cohortIds": ["cohort-1"]}],
        "total": 1,
        "totalPages": 1,
    }
    client = HublaClient(transport=transport)

    result = client.members_area_contents.list_sections(
        "product-1",
        page=2,
        page_size=10,
        post_page_size=25,
    )

    assert result == transport.responses["/hub/sections/v2"]
    assert transport.calls == [
        {
            "service": "members_area",
            "method": "GET",
            "path": "/hub/sections/v2",
            "params": {
                "productId": "product-1",
                "page": 2,
                "pageSize": 10,
                "postPageSize": 25,
            },
            "json": None,
            "response_type": "json",
            "headers": None,
        }
    ]


def test_cohort_and_section_iterators_are_available() -> None:
    client = HublaClient(transport=FakeTransport())

    assert callable(client.products.iter_cohorts)
    assert callable(client.members_area_contents.iter_sections)


def test_offer_cohort_and_section_iterators_do_not_fetch_until_consumed() -> None:
    transport = FakeTransport()
    transport.responses.update(
        {
            "/products/product-1/offers": {
                "items": [{"id": "offer-1"}],
                "total": 1,
            },
            "/products/product-1/cohorts": {
                "items": [{"id": "cohort-1"}],
                "total": 1,
            },
            "/hub/sections/v2": {
                "items": [{"id": "section-1"}],
                "total": 1,
            },
        }
    )
    client = HublaClient(transport=transport)

    offers = client.products.iter_offers("product-1")
    cohorts = client.products.iter_cohorts("product-1")
    sections = client.members_area_contents.iter_sections("product-1")

    assert transport.calls == []
    assert list(offers) == [{"id": "offer-1"}]
    assert list(cohorts) == [{"id": "cohort-1"}]
    assert list(sections) == [{"id": "section-1"}]


def test_member_contents_resource_is_in_the_catalog_with_expected_defaults() -> None:
    operation = build_catalog()["resources"]["members_area_contents"]["operations"][
        "list_sections"
    ]

    assert operation["parameters"]["page"]["default"] == 1
    assert operation["parameters"]["page_size"]["default"] == 999
    assert operation["parameters"]["post_page_size"]["default"] == 999


def test_find_exact_member_by_product_and_email() -> None:
    transport = FakeTransport()
    transport.responses["/members/actives/list"] = {
        "items": [
            {
                "id": "member-1",
                "productId": "product-1",
                "email": "member@example.test",
                "cohortIds": ["cohort-1"],
            }
        ],
        "itemsQuantityTotal": 1,
    }
    client = HublaClient(transport=transport)

    member = client.members.find_exact_by_email("product-1", "MEMBER@example.test")

    assert member["id"] == "member-1"


def test_find_exact_member_rejects_an_ignored_product_filter() -> None:
    transport = FakeTransport()
    transport.responses["/members/actives/list"] = {
        "items": [
            {
                "id": "member-1",
                "productId": "another-product",
                "email": "member@example.test",
            }
        ],
        "itemsQuantityTotal": 1,
    }
    client = HublaClient(transport=transport)

    with pytest.raises(MemberFilterIgnoredError):
        client.members.find_exact_by_email("product-1", "member@example.test")


def test_find_exact_member_rejects_ambiguous_matches() -> None:
    transport = FakeTransport()
    transport.responses["/members/actives/list"] = {
        "items": [
            {"id": "member-1", "email": "member@example.test"},
            {"id": "member-2", "email": "member@example.test"},
        ],
        "itemsQuantityTotal": 2,
    }
    client = HublaClient(transport=transport)

    with pytest.raises(AmbiguousMemberError):
        client.members.find_exact_by_email("product-1", "member@example.test")


def test_change_cohorts_with_readback_confirms_the_exact_result() -> None:
    transport = FakeTransport()
    transport.responses["/access/change-members-cohorts"] = {"ok": True}
    member_reads = 0

    def read_member(_call: dict[str, Any]) -> dict[str, Any]:
        nonlocal member_reads
        member_reads += 1
        cohort_id = "cohort-1" if member_reads == 1 else "cohort-2"
        return {
            "items": [
                {
                    "id": "member-1",
                    "email": "member@example.test",
                    "cohortIds": [cohort_id],
                }
            ],
            "itemsQuantityTotal": 1,
        }

    transport.responses["/members/actives/list"] = read_member
    client = HublaClient(transport=transport)

    result = client.members.change_cohorts_with_readback(
        product_id="product-1",
        member={"id": "member-1", "cohortIds": ["cohort-1"]},
        email="member@example.test",
        new_cohorts=["cohort-2"],
        confirm=True,
    )

    assert result["cohort_ids"] == ["cohort-2"]
    write_call = next(
        call
        for call in transport.calls
        if call["path"] == "/access/change-members-cohorts"
    )
    assert write_call["json"]["members"][0]["currentCohorts"] == ["cohort-1"]


def test_change_cohorts_normalizes_object_shaped_current_cohorts() -> None:
    transport = FakeTransport()
    client = HublaClient(transport=transport)

    client.members.change_cohorts(
        members=[
            {
                "memberId": "member-1",
                "currentCohorts": [
                    {"id": "cohort-1"},
                    {"cohortId": "cohort-2"},
                ],
            }
        ],
        new_cohorts=["cohort-3"],
        confirm=True,
    )

    write_call = next(
        call
        for call in transport.calls
        if call["path"] == "/access/change-members-cohorts"
    )
    assert write_call["json"]["members"][0]["currentCohorts"] == [
        "cohort-1",
        "cohort-2",
    ]


def test_change_cohorts_with_readback_rejects_a_divergent_result() -> None:
    transport = FakeTransport()
    transport.responses["/access/change-members-cohorts"] = {"ok": True}
    transport.responses["/members/actives/list"] = {
        "items": [
            {
                "id": "member-1",
                "email": "member@example.test",
                "cohortIds": ["cohort-1"],
            }
        ],
        "itemsQuantityTotal": 1,
    }
    client = HublaClient(transport=transport)

    with pytest.raises(CohortReadbackError):
        client.members.change_cohorts_with_readback(
            product_id="product-1",
            member={"id": "member-1", "cohortIds": ["cohort-1"]},
            email="member@example.test",
            new_cohorts=["cohort-2"],
            confirm=True,
        )


def test_change_cohorts_rejects_a_mismatched_member_before_writing() -> None:
    transport = FakeTransport()
    transport.responses["/members/actives/list"] = {
        "items": [
            {
                "id": "member-actual",
                "productId": "product-1",
                "email": "member@example.test",
                "cohortIds": ["cohort-1"],
            }
        ],
        "itemsQuantityTotal": 1,
    }
    client = HublaClient(transport=transport)

    with pytest.raises(MemberFilterIgnoredError):
        client.members.change_cohorts_with_readback(
            product_id="product-1",
            member={"id": "member-wrong", "cohortIds": ["cohort-1"]},
            email="member@example.test",
            new_cohorts=["cohort-2"],
            confirm=True,
        )

    assert all(
        call["path"] != "/access/change-members-cohorts" for call in transport.calls
    )


def test_change_cohorts_rejects_readback_from_another_member() -> None:
    transport = FakeTransport()
    transport.responses["/access/change-members-cohorts"] = {"ok": True}
    member_reads = 0

    def read_member(_call: dict[str, Any]) -> dict[str, Any]:
        nonlocal member_reads
        member_reads += 1
        return {
            "items": [
                {
                    "id": "member-1" if member_reads == 1 else "member-2",
                    "email": "member@example.test",
                    "cohortIds": ["cohort-2"],
                }
            ],
            "itemsQuantityTotal": 1,
        }

    transport.responses["/members/actives/list"] = read_member
    client = HublaClient(transport=transport)

    with pytest.raises(CohortReadbackError):
        client.members.change_cohorts_with_readback(
            product_id="product-1",
            member={"id": "member-1", "cohortIds": ["cohort-1"]},
            email="member@example.test",
            new_cohorts=["cohort-2"],
            confirm=True,
        )


def test_cohort_snapshot_contains_only_associated_sections() -> None:
    transport = FakeTransport()
    transport.responses["/hub/sections/v2"] = {
        "items": [
            {"id": "section-2", "cohortIds": ["cohort-1"]},
            {"id": "section-1", "cohortIds": ["cohort-1", "cohort-2"]},
            {"id": "section-3", "cohortIds": ["cohort-2"]},
        ],
        "total": 3,
    }
    client = HublaClient(transport=transport)

    snapshot = client.members_area_contents.cohort_snapshot("product-1", "cohort-1")

    assert snapshot["section_ids"] == ["section-1", "section-2"]
