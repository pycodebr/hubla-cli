"""Request payload builders shared by Hubla resources."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def offer_selection(
    offer_ids: Sequence[str] | None,
    has_selected_all: bool | None = None,
) -> dict[str, Any]:
    """Build Hubla's explicit offer selection object."""
    ids = list(offer_ids or [])
    if has_selected_all is None:
        has_selected_all = not ids
    return {"offerIds": ids, "hasSelectedAll": has_selected_all}


def invoices_body(
    *,
    offer_ids: Sequence[str] | None,
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
) -> dict[str, Any]:
    """Build the invoice list and summary payload used by Hubla."""
    selection = offer_selection(offer_ids, has_selected_all)
    selection.update(
        {
            "filters": {
                "startDate": start_date,
                "endDate": end_date,
                "status": list(statuses) if statuses is not None else ["paid"],
                "type": list(types or []),
                "paymentMethod": list(methods or []),
                "search": search,
                "utmSource": utm_source,
                "utmMedium": utm_medium,
                "utmCampaign": utm_campaign,
                "utmContent": utm_content,
                "utmTerm": utm_term,
                "dateRangeBy": date_range_by,
                "wallet": wallet,
            },
            "page": page,
            "pageSize": page_size,
            "orderBy": order_by,
            "orderDirection": order_direction,
        }
    )
    return selection


def subscriptions_body(
    *,
    offer_ids: Sequence[str] | None,
    has_selected_all: bool | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    statuses: Sequence[str] | None = None,
    search: str = "",
    date_range_by: str | None = None,
    plan_type: str | None = None,
    is_free_trial_active: bool | None = None,
    page: int = 1,
    page_size: int = 25,
    order_by: str = "createdAt",
    order_direction: str = "DESC",
) -> dict[str, Any]:
    """Build the subscription list payload used by Hubla."""
    selection = offer_selection(offer_ids, has_selected_all)
    selection.update(
        {
            "filters": {
                "search": search,
                "status": list(statuses or []),
                "startDate": start_date,
                "endDate": end_date,
                "dateRangeBy": date_range_by,
                "planType": plan_type,
                "isFreeTrialActive": is_free_trial_active,
            },
            "page": page,
            "pageSize": page_size,
            "orderBy": order_by,
            "orderDirection": order_direction,
        }
    )
    return selection
