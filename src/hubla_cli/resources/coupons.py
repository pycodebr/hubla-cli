"""Coupon resources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from hubla_cli.resources.base import ResourceBase


class CouponsResource(ResourceBase):
    """Inspect and manage account coupons."""

    def list(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        statuses: Sequence[str] | None = None,
        search: str = "",
        page: int = 1,
        page_size: int = 25,
        order_by: str = "createdAt",
        order_direction: str = "DESC",
    ) -> Any:
        selection = self._offer_selection(offer_ids, has_selected_all)
        body = {
            "filters": {
                "offerIds": selection["offerIds"],
                "hasSelectedAll": selection["hasSelectedAll"],
                "states": list(statuses or []),
                "code": search.upper() if search else "",
            },
            "page": page,
            "pageSize": page_size,
            "orderBy": order_by,
            "orderDirection": order_direction,
        }
        return self._call("web", "POST", "/coupons/list", json=body)

    def get(self, coupon_id: str) -> Any:
        return self._call(
            "web", "GET", "/coupons/details", params={"couponId": coupon_id}
        )

    detail = get

    def create(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web", "POST", "/coupons/create", json=dict(payload), confirm=confirm
        )

    def delete(self, coupon_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "DELETE",
            "/coupons/delete/",
            json={"couponId": coupon_id},
            confirm=confirm,
        )

    def export(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        statuses: Sequence[str] | None = None,
        confirm: bool = False,
    ) -> bytes:
        selection = self._offer_selection(offer_ids, has_selected_all)
        body = {
            "offerIds": selection["offerIds"],
            "hasSelectedAll": selection["hasSelectedAll"],
            "filters": {"states": list(statuses or [])},
        }
        return self._write(
            "web",
            "POST",
            "/coupons/export",
            json=body,
            response_type="bytes",
            confirm=confirm,
        )
