"""Sales and invoices resource."""

from __future__ import annotations

import builtins
from collections.abc import Iterator, Sequence
from typing import Any
from urllib.parse import quote

from hubla_cli.pagination import collect_paginated
from hubla_cli.payloads import invoices_body
from hubla_cli.resources.base import ResourceBase


def _id(value: Any) -> str:
    return quote(str(value), safe="")


class SalesResource(ResourceBase):
    """List invoices, inspect sales, export data, and request refunds."""

    def list(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        statuses: Sequence[str] | None = None,
        types: Sequence[str] | None = None,
        methods: Sequence[str] | None = None,
        search: str = "",
        utm_source: str = "",
        utm_medium: str = "",
        utm_campaign: str = "",
        utm_content: str = "",
        utm_term: str = "",
        date_range_by: str | None = None,
        wallet: str | None = None,
        page: int = 1,
        page_size: int = 25,
        order_by: str = "createdAt",
        order_direction: str = "DESC",
    ) -> Any:
        selection = self._offer_selection(offer_ids, has_selected_all)
        body = invoices_body(
            offer_ids=selection["offerIds"],
            has_selected_all=selection["hasSelectedAll"],
            start_date=start_date,
            end_date=end_date,
            statuses=statuses,
            types=types,
            methods=methods,
            search=search,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            date_range_by=date_range_by,
            wallet=wallet,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_direction=order_direction,
        )
        return self._call("web", "POST", "/invoices/list", json=body)

    def iter_all(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        statuses: Sequence[str] | None = None,
        types: Sequence[str] | None = None,
        methods: Sequence[str] | None = None,
        search: str = "",
        utm_source: str = "",
        utm_medium: str = "",
        utm_campaign: str = "",
        utm_content: str = "",
        utm_term: str = "",
        date_range_by: str | None = None,
        wallet: str | None = None,
        page: int = 1,
        page_size: int = 25,
        order_by: str = "createdAt",
        order_direction: str = "DESC",
    ) -> Iterator[Any]:
        """Yield every sale matching the supplied filters."""
        result = collect_paginated(
            lambda current_page, current_page_size: self.list(
                offer_ids=offer_ids,
                has_selected_all=has_selected_all,
                start_date=start_date,
                end_date=end_date,
                statuses=statuses,
                types=types,
                methods=methods,
                search=search,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_content=utm_content,
                utm_term=utm_term,
                date_range_by=date_range_by,
                wallet=wallet,
                page=current_page,
                page_size=current_page_size,
                order_by=order_by,
                order_direction=order_direction,
            ),
            page=page,
            page_size=page_size,
        )
        yield from result.items

    def all(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        statuses: Sequence[str] | None = None,
        types: Sequence[str] | None = None,
        methods: Sequence[str] | None = None,
        search: str = "",
        utm_source: str = "",
        utm_medium: str = "",
        utm_campaign: str = "",
        utm_content: str = "",
        utm_term: str = "",
        date_range_by: str | None = None,
        wallet: str | None = None,
        page: int = 1,
        page_size: int = 25,
        order_by: str = "createdAt",
        order_direction: str = "DESC",
    ) -> builtins.list[Any]:
        """Return every sale matching the supplied filters."""
        return list(
            self.iter_all(
                offer_ids=offer_ids,
                has_selected_all=has_selected_all,
                start_date=start_date,
                end_date=end_date,
                statuses=statuses,
                types=types,
                methods=methods,
                search=search,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                utm_content=utm_content,
                utm_term=utm_term,
                date_range_by=date_range_by,
                wallet=wallet,
                page=page,
                page_size=page_size,
                order_by=order_by,
                order_direction=order_direction,
            )
        )

    filter = list

    def get(self, invoice_id: Any) -> Any:
        return self._call("web", "GET", f"/invoices/{_id(invoice_id)}")

    detail = get

    def summaries(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        statuses: Sequence[str] | None = None,
        types: Sequence[str] | None = None,
        methods: Sequence[str] | None = None,
        search: str = "",
        utm_source: str = "",
        utm_medium: str = "",
        utm_campaign: str = "",
        utm_content: str = "",
        utm_term: str = "",
        date_range_by: str | None = None,
        wallet: str | None = None,
        page: int = 1,
        page_size: int = 25,
        order_by: str = "createdAt",
        order_direction: str = "DESC",
    ) -> Any:
        selection = self._offer_selection(offer_ids, has_selected_all)
        body = invoices_body(
            offer_ids=selection["offerIds"],
            has_selected_all=selection["hasSelectedAll"],
            start_date=start_date,
            end_date=end_date,
            statuses=statuses,
            types=types,
            methods=methods,
            search=search,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            date_range_by=date_range_by,
            wallet=wallet,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_direction=order_direction,
        )
        return self._call(
            "web",
            "POST",
            "/invoices/summaries",
            json=body,
        )

    def export(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        statuses: Sequence[str] | None = None,
        types: Sequence[str] | None = None,
        methods: Sequence[str] | None = None,
        search: str = "",
        utm_source: str = "",
        utm_medium: str = "",
        utm_campaign: str = "",
        utm_content: str = "",
        utm_term: str = "",
        date_range_by: str | None = None,
        wallet: str | None = None,
        page: int = 1,
        page_size: int = 25,
        order_by: str = "createdAt",
        order_direction: str = "DESC",
        confirm: bool = False,
    ) -> bytes:
        selection = self._offer_selection(offer_ids, has_selected_all)
        body = invoices_body(
            offer_ids=selection["offerIds"],
            has_selected_all=selection["hasSelectedAll"],
            start_date=start_date,
            end_date=end_date,
            statuses=statuses,
            types=types,
            methods=methods,
            search=search,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            date_range_by=date_range_by,
            wallet=wallet,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_direction=order_direction,
        )
        return self._write(
            "web",
            "POST",
            "/invoices/background-export",
            json=body,
            response_type="bytes",
            confirm=confirm,
        )

    def refund(self, invoice_id: Any, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "PUT",
            f"/invoices/{_id(invoice_id)}/refund",
            confirm=confirm,
        )

    reembolsar = refund
