from __future__ import annotations

from typing import Any

import pytest

from hubla_cli.errors import PaginationError
from hubla_cli.pagination import collect_paginated


@pytest.mark.parametrize(
    "payload_factory",
    [
        lambda items: {"items": items, "total": 3},
        lambda items: {"rows": items, "totalCount": 3},
        lambda items: {"data": items, "meta": {"total": 3}},
        lambda items: {"data": {"rows": items, "pagination": {"totalItems": 3}}},
    ],
)
def test_collect_paginated_extracts_common_item_and_total_shapes(
    payload_factory: Any,
) -> None:
    calls: list[tuple[int, int]] = []
    pages = {
        1: payload_factory([{"id": "one"}, {"id": "two"}]),
        2: payload_factory([{"id": "three"}]),
    }

    def fetch(page: int, page_size: int) -> Any:
        calls.append((page, page_size))
        return pages[page]

    result = collect_paginated(
        fetch,
        page_size=2,
    )

    assert result == [{"id": "one"}, {"id": "two"}, {"id": "three"}]
    assert calls == [(1, 2), (2, 2)]


def test_collect_paginated_stops_on_empty_page_without_total() -> None:
    calls: list[int] = []

    def fetch(page: int, _page_size: int) -> list[dict[str, str]]:
        calls.append(page)
        return [{"id": "one"}] if page == 1 else []

    result = collect_paginated(
        fetch,
        page_size=10,
    )

    assert result == [{"id": "one"}]
    assert calls == [1, 2]


def test_collect_paginated_rejects_a_repeated_page() -> None:
    page = {"items": [{"id": "same"}], "total": 3}

    with pytest.raises(PaginationError, match="repeated page"):
        collect_paginated(lambda _page, _page_size: page)


def test_collect_paginated_rejects_a_provider_page_that_does_not_match_request() -> (
    None
):
    response = {
        "items": [{"id": "one"}],
        "total": 1,
        "currentPage": 1,
    }

    with pytest.raises(PaginationError, match="page"):
        collect_paginated(lambda _page, _page_size: response, page=2)


def test_complete_collection_must_start_at_first_page() -> None:
    with pytest.raises(PaginationError, match="start at page 1"):
        collect_paginated(
            lambda _page, _page_size: {
                "items": [{"id": "two"}],
                "total": 2,
                "currentPage": 2,
                "totalPages": 2,
            },
            page=2,
        )


def test_collect_paginated_rejects_empty_page_before_declared_total() -> None:
    responses = {
        1: {"items": [{"id": "one"}], "total": 2},
        2: {"items": [], "total": 2},
    }

    with pytest.raises(PaginationError, match="empty page"):
        collect_paginated(lambda page, _page_size: responses[page])


def test_collect_paginated_rejects_total_drift() -> None:
    responses = {
        1: {"items": [{"id": "one"}], "total": 2},
        2: {"items": [{"id": "two"}], "total": 3},
    }

    with pytest.raises(PaginationError, match="total drift"):
        collect_paginated(lambda page, _page_size: responses[page])


def test_collect_paginated_can_require_a_reconciled_provider_total() -> None:
    responses = {
        1: {"items": [{"id": "one"}]},
        2: {"items": []},
    }

    with pytest.raises(PaginationError, match="total"):
        collect_paginated(
            lambda page, _page_size: responses[page],
            require_total=True,
        )


def test_collect_paginated_rejects_an_unrecognized_mapping() -> None:
    with pytest.raises(PaginationError, match="unrecognized"):
        collect_paginated(lambda _page, _page_size: {"error": "provider failed"})


def test_collect_paginated_returns_normalized_totals() -> None:
    result = collect_paginated(
        lambda _page, _page_size: {
            "data": [{"id": "one"}],
            "pagination": {"totalItems": "1"},
        }
    )

    assert result.items == [{"id": "one"}]
    assert result.declared_total == 1
    assert result.collected_total == 1
    assert result.total == 1
    assert list(result) == result.items


def test_collect_paginated_rejects_over_collection() -> None:
    with pytest.raises(PaginationError, match="over|cannot reconcile"):
        collect_paginated(
            lambda _page, _page_size: {
                "items": [{"id": "one"}, {"id": "two"}],
                "total": 1,
            }
        )


def test_collect_paginated_rejects_total_reached_before_declared_last_page() -> None:
    response = {
        "items": [{"id": "one"}],
        "total": 1,
        "totalPages": 2,
        "currentPage": 1,
    }

    with pytest.raises(PaginationError, match="total pages|contradictory"):
        collect_paginated(lambda _page, _page_size: response)


@pytest.mark.parametrize(
    "requested_page,response",
    [
        (2, {"items": [{"id": "one"}], "totalPages": 1}),
        (1, {"items": [{"id": "one"}], "total": 1, "totalPages": 0}),
    ],
)
def test_collect_paginated_rejects_impossible_page_total_pages_combination(
    requested_page: int,
    response: dict[str, Any],
) -> None:
    with pytest.raises(PaginationError, match="page"):
        collect_paginated(
            lambda _page, _page_size: response,
            page=requested_page,
        )


def test_collect_paginated_follows_cursor_and_passes_the_next_cursor() -> None:
    calls: list[tuple[Any, int]] = []

    def fetch(cursor: Any, page_size: int) -> dict[str, Any]:
        calls.append((cursor, page_size))
        pages = {
            None: {
                "items": [{"id": "one"}],
                "pagination": {"total": 3, "nextCursor": "cursor-1"},
            },
            "cursor-1": {
                "rows": [{"id": "two"}],
                "pagination": {"total": 3, "nextCursor": "cursor-2"},
            },
            "cursor-2": {
                "data": [{"id": "three"}],
                "pagination": {"total": 3},
            },
        }
        return pages[cursor]

    result = collect_paginated(fetch, page_size=7)

    assert result.items == [{"id": "one"}, {"id": "two"}, {"id": "three"}]
    assert calls == [(None, 7), ("cursor-1", 7), ("cursor-2", 7)]


def test_collect_paginated_supports_a_required_third_cursor_argument() -> None:
    calls: list[tuple[int, int, Any]] = []

    def fetch(page: int, page_size: int, cursor: Any) -> dict[str, Any]:
        calls.append((page, page_size, cursor))
        return {
            "items": [{"id": str(page)}],
            "total": 2,
            "nextCursor": "next" if page == 1 else None,
        }

    result = collect_paginated(fetch, page_size=4)

    assert result.items == [{"id": "1"}, {"id": "2"}]
    assert calls == [(1, 4, None), (2, 4, "next")]


def test_collect_paginated_rejects_a_repeated_cursor() -> None:
    def fetch(cursor: Any, _page_size: int) -> dict[str, Any]:
        return {
            "items": [{"id": str(cursor)}],
            "total": 3,
            "nextCursor": "loop",
        }

    with pytest.raises(PaginationError, match="repeated cursor"):
        collect_paginated(fetch)


def test_collect_paginated_uses_total_pages_when_record_total_is_absent() -> None:
    calls: list[int] = []

    def fetch(page: int, _page_size: int) -> dict[str, Any]:
        calls.append(page)
        return {
            "items": [{"id": str(page)}],
            "pagination": {"totalPages": 2},
        }

    result = collect_paginated(fetch)

    assert result.items == [{"id": "1"}, {"id": "2"}]
    assert result.declared_total is None
    assert calls == [1, 2]
