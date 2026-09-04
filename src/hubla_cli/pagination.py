"""Shared helpers for safely collecting Hubla paginated responses."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, overload

from hubla_cli.errors import PaginationError

ItemT = TypeVar("ItemT")
PageFetcher = Callable[..., Any]

_ITEM_KEYS = ("items", "rows", "data", "results", "records", "content")
_ENVELOPE_KEYS = ("data", "result", "response", "payload", "body")
_TOTAL_KEYS = (
    "total",
    "totalCount",
    "totalItems",
    "totalElements",
    "itemsQuantityTotal",
    "recordsTotal",
    "totalRecords",
    "totalResults",
    "total_count",
    "total_items",
    "total_elements",
    "items_quantity_total",
    "records_total",
    "count",
)
_TOTAL_CONTAINER_KEYS = ("pagination", "meta", "pageInfo", "page_info")
_TOTAL_PAGES_KEYS = (
    "totalPages",
    "total_pages",
    "pages",
)
_PAGE_NUMBER_KEYS = (
    "page",
    "currentPage",
    "current_page",
    "pageNumber",
    "page_number",
)
_NEXT_CURSOR_KEYS = (
    "nextCursor",
    "next_cursor",
    "nextPageToken",
    "next_page_token",
    "nextToken",
    "next_token",
    "next",
)
_CURSOR_PARAMETER_NAMES = {
    "cursor",
    "page_token",
    "pageToken",
    "next_cursor",
    "nextCursor",
    "continuation_token",
    "continuationToken",
}


@dataclass(frozen=True, eq=False)
class PaginationResult(Sequence[ItemT], Generic[ItemT]):
    """Normalized result returned after a paginated collection.

    ``items`` is a regular list so callers can pass it to existing code.  The
    result itself also behaves like a read-only sequence for compatibility with
    callers that previously consumed the collector as a list.
    """

    items: list[ItemT]
    declared_total: int | None
    collected_total: int

    def __iter__(self) -> Iterator[ItemT]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    @overload
    def __getitem__(self, index: int) -> ItemT: ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[ItemT]: ...

    def __getitem__(self, index: int | slice) -> ItemT | Sequence[ItemT]:
        return self.items[index]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PaginationResult):
            return (
                self.items == other.items
                and self.declared_total == other.declared_total
                and self.collected_total == other.collected_total
            )
        if isinstance(other, Sequence) and not isinstance(
            other, (str, bytes, bytearray)
        ):
            return self.items == list(other)
        return NotImplemented

    @property
    def total(self) -> int:
        """Return the provider total when declared, otherwise the collected one."""
        return (
            self.declared_total
            if self.declared_total is not None
            else self.collected_total
        )

    @property
    def declared(self) -> int | None:
        """Compatibility alias for :attr:`declared_total`."""
        return self.declared_total

    @property
    def collected(self) -> int:
        """Compatibility alias for :attr:`collected_total`."""
        return self.collected_total


# A descriptive spelling used by some integrations.
PaginatedResult = PaginationResult


def _as_items(value: Any) -> list[Any] | None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return None


def _as_non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        try:
            parsed = int(value.strip())
        except ValueError:
            return None
        return parsed if parsed >= 0 else None
    return None


def _find_nested_value(
    payload: Mapping[str, Any],
    keys: Sequence[str],
    *,
    containers: Sequence[str],
) -> tuple[bool, Any]:
    """Find a metadata value in a page envelope without walking item records."""
    for key in keys:
        if key in payload:
            return True, payload[key]
    for key in containers:
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            found, value = _find_nested_value(
                nested,
                keys,
                containers=containers,
            )
            if found:
                return True, value
    for key in _ENVELOPE_KEYS:
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            found, value = _find_nested_value(
                nested,
                keys,
                containers=containers,
            )
            if found:
                return True, value
    return False, None


def _find_total(payload: Mapping[str, Any]) -> int | None:
    found, value = _find_nested_value(
        payload,
        _TOTAL_KEYS,
        containers=(*_TOTAL_CONTAINER_KEYS, "data"),
    )
    return _as_non_negative_int(value) if found else None


def _find_total_pages(payload: Mapping[str, Any]) -> int | None:
    found, value = _find_nested_value(
        payload,
        _TOTAL_PAGES_KEYS,
        containers=(*_TOTAL_CONTAINER_KEYS, "data"),
    )
    return _as_non_negative_int(value) if found else None


def _find_page_number(payload: Mapping[str, Any]) -> int | None:
    found, value = _find_nested_value(
        payload,
        _PAGE_NUMBER_KEYS,
        containers=(*_TOTAL_CONTAINER_KEYS, "data"),
    )
    return _as_non_negative_int(value) if found else None


def _find_next_cursor(payload: Mapping[str, Any]) -> tuple[bool, Any]:
    found, value = _find_nested_value(
        payload,
        _NEXT_CURSOR_KEYS,
        containers=(*_TOTAL_CONTAINER_KEYS, "data"),
    )
    if found:
        return found, value
    return _find_nested_value(
        payload,
        ("cursor",),
        containers=(*_TOTAL_CONTAINER_KEYS, "data"),
    )


def _extract_page(
    payload: Any,
) -> tuple[list[Any], int | None, int | None, int | None, tuple[bool, Any]]:
    """Extract records and pagination metadata from common response envelopes."""
    if isinstance(payload, Mapping):
        total = _find_total(payload)
        total_pages = _find_total_pages(payload)
        page_number = _find_page_number(payload)
        next_cursor = _find_next_cursor(payload)
        for key in _ITEM_KEYS:
            if key not in payload:
                continue
            value = payload[key]
            items = _as_items(value)
            if items is not None:
                return items, total, total_pages, page_number, next_cursor
            if isinstance(value, Mapping):
                (
                    nested_items,
                    nested_total,
                    nested_total_pages,
                    nested_page_number,
                    nested_next_cursor,
                ) = _extract_page(value)
                return (
                    nested_items,
                    total if total is not None else nested_total,
                    total_pages if total_pages is not None else nested_total_pages,
                    page_number if page_number is not None else nested_page_number,
                    next_cursor if next_cursor[0] else nested_next_cursor,
                )
            if value is None:
                return [], total, total_pages, page_number, next_cursor

        # A few clients put the page envelope below ``response`` or ``result``
        # rather than directly below ``data``.  Do not treat arbitrary mapping
        # values as records: an error envelope must not become a fake item.
        for key in _ENVELOPE_KEYS:
            nested = payload.get(key)
            if not isinstance(nested, Mapping):
                continue
            (
                nested_items,
                nested_total,
                nested_total_pages,
                nested_page_number,
                nested_next_cursor,
            ) = _extract_page(nested)
            if (
                nested_items
                or nested_total is not None
                or nested_total_pages is not None
                or nested_page_number is not None
            ):
                return (
                    nested_items,
                    total if total is not None else nested_total,
                    total_pages if total_pages is not None else nested_total_pages,
                    page_number if page_number is not None else nested_page_number,
                    next_cursor if next_cursor[0] else nested_next_cursor,
                )
        raise PaginationError("unrecognized paginated response mapping")

    items = _as_items(payload)
    if items is not None:
        return items, None, None, None, (False, None)
    if payload is None:
        return [], None, None, None, (False, None)
    return [payload], None, None, None, (False, None)


def _cursor_parameter_style(fetch: PageFetcher) -> str:
    """Return the cursor callback shape inferred from its parameter names."""
    try:
        parameters = list(inspect.signature(fetch).parameters.values())
    except (TypeError, ValueError):
        return "optional"

    names = [parameter.name for parameter in parameters]
    if names and names[0] in _CURSOR_PARAMETER_NAMES:
        return "first"
    cursor_parameter = next(
        (
            parameter
            for parameter in parameters
            if parameter.name in _CURSOR_PARAMETER_NAMES
        ),
        None,
    )
    if cursor_parameter is not None:
        if cursor_parameter.default is cursor_parameter.empty:
            return "required"
        return "optional"
    if any(parameter.kind is parameter.VAR_KEYWORD for parameter in parameters):
        return "optional"
    return "none"


def _invoke_fetch(
    fetch: PageFetcher,
    page: int,
    page_size: int,
    cursor: Any,
    *,
    cursor_mode: bool,
) -> Any:
    """Call page- or cursor-shaped callbacks without masking callback errors."""
    if not cursor_mode:
        return fetch(page, page_size)

    try:
        parameters = list(inspect.signature(fetch).parameters.values())
    except (TypeError, ValueError):
        return fetch(page, page_size, cursor)

    positional = [
        parameter
        for parameter in parameters
        if parameter.kind
        in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
    ]
    first_name = positional[0].name if positional else ""
    if first_name in _CURSOR_PARAMETER_NAMES:
        args: list[Any] = [cursor]
        if len(positional) >= 2 or any(
            parameter.kind is parameter.VAR_POSITIONAL for parameter in parameters
        ):
            args.append(page_size)
        return fetch(*args)

    cursor_parameter = next(
        (
            parameter
            for parameter in parameters
            if parameter.name in _CURSOR_PARAMETER_NAMES
        ),
        None,
    )
    if (
        cursor_parameter is not None
        and cursor_parameter.kind is cursor_parameter.KEYWORD_ONLY
    ):
        return fetch(page, page_size, **{cursor_parameter.name: cursor})
    if cursor_parameter is not None:
        position = positional.index(cursor_parameter)
        if position == 1:
            return fetch(page, cursor)
        if position >= 2:
            return fetch(page, page_size, cursor)
    if any(parameter.kind is parameter.VAR_KEYWORD for parameter in parameters):
        return fetch(page, page_size, cursor=cursor)
    raise PaginationError(
        "pagination response supplied a cursor but the page fetcher does not accept one"
    )


def _same_cursor(left: Any, right: Any) -> bool:
    try:
        return left == right
    except Exception:
        return repr(left) == repr(right)


def _validate_page_metadata(
    *,
    current_page: int,
    items: Sequence[Any],
    provider_total: int | None,
    total_pages: int | None,
    page_number: int | None,
    cursor_mode: bool,
) -> None:
    """Reject page metadata that cannot describe the requested page safely."""
    if cursor_mode:
        return
    if page_number is not None and page_number != current_page:
        raise PaginationError(
            "provider page does not match the requested page "
            f"({page_number} != {current_page})"
        )
    if total_pages is None:
        return
    if total_pages == 0:
        # A zero-page response is a valid empty result when the first page was
        # requested.  Any records, positive total, or later requested page is
        # contradictory.
        if (
            current_page != 1
            or items
            or (provider_total is not None and provider_total != 0)
        ):
            raise PaginationError(
                "impossible page and total-pages metadata "
                f"(page {current_page}, total pages {total_pages})"
            )
        return
    if current_page > total_pages:
        raise PaginationError(
            "requested page exceeds provider total pages "
            f"({current_page} > {total_pages})"
        )


def collect_paginated(
    fetch: PageFetcher,
    *,
    page: int = 1,
    page_size: int = 100,
    require_total: bool = False,
    cursor: Any | None = None,
    max_pages: int = 10_000,
) -> PaginationResult[Any]:
    """Collect every page and reconcile provider pagination metadata.

    The callback normally receives ``(page, page_size)``.  Cursor endpoints can
    use ``(page, page_size, cursor)``, ``(cursor, page_size)``, or a callback
    with a named cursor keyword.  The helper recognizes common ``items``/``rows``/
    ``data`` envelopes and totals at the root or below pagination metadata.

    A missing total is allowed unless ``require_total`` is true; in that case a
    page with no declared total is unsafe and raises :class:`PaginationError`.
    """
    if page < 1:
        raise ValueError("page must be at least 1")
    if page_size < 1:
        raise ValueError("page_size must be at least 1")
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    if page != 1:
        raise PaginationError("complete collection must start at page 1")

    cursor_style = _cursor_parameter_style(fetch)
    cursor_mode = cursor is not None or cursor_style in {"first", "required"}
    current_cursor = cursor
    current_page = page
    collected: list[Any] = []
    declared_total: int | None = None
    declared_total_pages: int | None = None
    seen_pages: list[list[Any]] = []
    seen_page_numbers: list[int] = []
    seen_cursors: list[Any] = []
    seen_response_cursors: list[Any] = []

    for _ in range(max_pages):
        response = _invoke_fetch(
            fetch,
            current_page,
            page_size,
            current_cursor,
            cursor_mode=cursor_mode,
        )
        (
            items,
            provider_total,
            total_pages,
            page_number,
            next_cursor_info,
        ) = _extract_page(response)

        _validate_page_metadata(
            current_page=current_page,
            items=items,
            provider_total=provider_total,
            total_pages=total_pages,
            page_number=page_number,
            cursor_mode=cursor_mode,
        )

        if require_total and provider_total is None:
            raise PaginationError(
                f"provider total missing on page {current_page}; "
                "cannot reconcile paginated response"
            )
        if declared_total is None:
            declared_total = provider_total
        elif provider_total is None or provider_total != declared_total:
            raise PaginationError(
                "provider total drifted while collecting paginated response"
            )

        if declared_total_pages is None:
            declared_total_pages = total_pages
        elif total_pages is None or total_pages != declared_total_pages:
            raise PaginationError(
                "provider total pages drifted while collecting paginated response"
            )

        if page_number is not None and not cursor_mode:
            if page_number in seen_page_numbers:
                raise PaginationError(
                    "repeated page detected while collecting paginated response"
                )
            seen_page_numbers.append(page_number)

        if not items:
            if declared_total_pages is not None and current_page < declared_total_pages:
                raise PaginationError(
                    "empty page received before provider total pages were exhausted"
                )
            if declared_total is not None and len(collected) < declared_total:
                raise PaginationError(
                    "empty page received before provider total was reconciled"
                )
            return PaginationResult(
                items=collected,
                declared_total=declared_total,
                collected_total=len(collected),
            )

        if any(items == previous for previous in seen_pages):
            raise PaginationError(
                f"repeated page detected while collecting page {current_page}"
            )
        seen_pages.append(list(items))
        collected.extend(items)

        if declared_total is not None:
            if len(collected) > declared_total:
                raise PaginationError(
                    "provider total cannot reconcile with collected records "
                    f"({len(collected)} > {declared_total})"
                )
            if len(collected) == declared_total:
                if (
                    declared_total_pages is not None
                    and current_page < declared_total_pages
                ):
                    raise PaginationError(
                        "contradictory pagination metadata: declared total was "
                        "collected before declared total pages were exhausted"
                    )
                return PaginationResult(
                    items=collected,
                    declared_total=declared_total,
                    collected_total=len(collected),
                )

        has_next_cursor, next_cursor = next_cursor_info
        if has_next_cursor and next_cursor not in (None, ""):
            if any(_same_cursor(next_cursor, seen) for seen in seen_response_cursors):
                raise PaginationError(
                    "repeated cursor detected while collecting paginated response"
                )
            seen_response_cursors.append(next_cursor)
        if not cursor_mode and has_next_cursor and cursor_style != "none":
            cursor_mode = True

        if cursor_mode:
            if not has_next_cursor or next_cursor in (None, ""):
                if declared_total is not None:
                    raise PaginationError(
                        "pagination ended before provider total was reconciled"
                    )
                return PaginationResult(
                    items=collected,
                    declared_total=declared_total,
                    collected_total=len(collected),
                )
            if any(_same_cursor(next_cursor, seen) for seen in seen_cursors) or (
                current_cursor is not None and _same_cursor(next_cursor, current_cursor)
            ):
                raise PaginationError(
                    "repeated cursor detected while collecting paginated response"
                )
            seen_cursors.append(next_cursor)
            current_cursor = next_cursor
            current_page += 1
            continue

        if declared_total_pages is not None and current_page >= declared_total_pages:
            if declared_total is not None:
                raise PaginationError(
                    "pagination ended before provider total was reconciled"
                )
            return PaginationResult(
                items=collected,
                declared_total=declared_total,
                collected_total=len(collected),
            )
        current_page += 1

    raise PaginationError(f"pagination exceeded the safety limit of {max_pages} pages")
