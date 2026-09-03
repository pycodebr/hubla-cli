"""Affiliate resources."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from hubla_cli.resources.base import ResourceBase


def _id(value: Any) -> str:
    return quote(str(value), safe="")


class AffiliatesResource(ResourceBase):
    """Inspect affiliates and perform confirmed commission changes."""

    def list(self, *, page: int = 1, page_size: int = 25) -> Any:
        return self._call(
            "web", "GET", "/affiliates", params={"page": page, "pageSize": page_size}
        )

    def get_program(self, product_id: str) -> Any:
        return self._call(
            "web",
            "GET",
            f"/receivers/affiliate/get-affiliation-program/{_id(product_id)}",
        )

    def list_affiliations(
        self,
        filters: Mapping[str, Any] | None = None,
    ) -> Any:
        return self._call(
            "web",
            "POST",
            "/receivers/affiliate/list-affiliations",
            json={"filters": dict(filters or {})},
        )

    def change_commission(
        self,
        *,
        affiliate_id: str,
        sell_commission: float | None = None,
        renewal_commission: float | None = None,
        use_default_commission: bool = False,
        validation_code: str | None = None,
        confirm: bool = False,
    ) -> Any:
        commission = (
            None
            if use_default_commission
            else {"sell": sell_commission, "renewal": renewal_commission}
        )
        body = {
            "receiverId": affiliate_id,
            "commission": commission,
            "validationCode": validation_code,
        }
        return self._write(
            "web",
            "POST",
            "/affiliates/change-commission",
            json=body,
            confirm=confirm,
        )

    def remove(self, affiliate_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "web", "DELETE", f"/affiliates/{_id(affiliate_id)}", confirm=confirm
        )

    def export(self, *, file_type: str = "xlsx", confirm: bool = False) -> Any:
        return self._write(
            "functions",
            "POST",
            "/exportRequestCreate/pt",
            json={
                "data": {
                    "type": file_type,
                    "data": "affiliates",
                    "param": None,
                }
            },
            confirm=confirm,
        )
