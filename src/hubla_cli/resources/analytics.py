"""Read-only analytics resources."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from hubla_cli.resources.base import ResourceBase


class AnalyticsResource(ResourceBase):
    """Read account metrics from Hubla's dashboard summaries."""

    def _summary(
        self,
        path: str,
        *,
        start_date: str,
        end_date: str,
        offer_ids: Sequence[str] | None,
        has_selected_all: bool | None,
        wallet: str | None = None,
        period: str | None = None,
        payment_method: str | None = None,
    ) -> Any:
        body = self._offer_selection(offer_ids, has_selected_all)
        body.update({"startDate": start_date, "endDate": end_date, "wallet": wallet})
        if period is not None:
            body["period"] = period
        if payment_method is not None:
            body["paymentMethod"] = payment_method
        return self._call("web", "POST", path, json=body)

    def net_revenue(
        self,
        *,
        start_date: str,
        end_date: str,
        period: str,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        wallet: str | None = None,
    ) -> Any:
        return self._summary(
            "/receiver/summary/net-revenue",
            start_date=start_date,
            end_date=end_date,
            period=period,
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
            wallet=wallet,
        )

    def sales(
        self,
        *,
        start_date: str,
        end_date: str,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        wallet: str | None = None,
    ) -> Any:
        return self._summary(
            "/receiver/summary/sales",
            start_date=start_date,
            end_date=end_date,
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
            wallet=wallet,
        )

    def refunds(
        self,
        *,
        start_date: str,
        end_date: str,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        wallet: str | None = None,
    ) -> Any:
        return self._summary(
            "/receiver/summary/refunds",
            start_date=start_date,
            end_date=end_date,
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
            wallet=wallet,
        )

    def average_ticket(
        self,
        *,
        start_date: str,
        end_date: str,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        wallet: str | None = None,
    ) -> Any:
        return self._summary(
            "/receiver/summary/average-ticket",
            start_date=start_date,
            end_date=end_date,
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
            wallet=wallet,
        )

    def average_ticket_by_currency(
        self,
        *,
        start_date: str,
        end_date: str,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
    ) -> Any:
        return self._summary(
            "/receiver/summary/average-ticket-by-currency",
            start_date=start_date,
            end_date=end_date,
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
            wallet="INTERNATIONAL",
        )

    def conversion_rate(
        self,
        *,
        start_date: str,
        end_date: str,
        payment_method: str | None = None,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        wallet: str | None = None,
    ) -> Any:
        return self._summary(
            "/receiver/summary/conversion-rate",
            start_date=start_date,
            end_date=end_date,
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
            wallet=wallet,
            payment_method=payment_method,
        )

    def abandoned_checkouts(
        self,
        *,
        start_date: str,
        end_date: str,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
    ) -> Any:
        body = self._offer_selection(offer_ids, has_selected_all)
        body.update({"startDate": start_date, "endDate": end_date})
        return self._call("web", "POST", "/leads/summary/total-leads", json=body)
