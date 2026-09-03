"""Refund request resources."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from hubla_cli.resources.base import ResourceBase


def _id(value: Any) -> str:
    return quote(str(value), safe="")


def _without_none(values: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


class RefundsResource(ResourceBase):
    """Inspect and manage seller and payer refund requests."""

    def list_seller(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        filters: Mapping[str, Any] | None = None,
    ) -> Any:
        body = {
            "page": page,
            "pageSize": page_size,
            "filters": _without_none(filters or {}),
        }
        return self._call("web", "POST", "/refunds/seller/list", json=body)

    list = list_seller

    def get(self, refund_id: Any) -> Any:
        return self._call("web", "GET", f"/refunds/{_id(refund_id)}")

    def accept(self, refund_id: Any, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "PATCH",
            f"/refunds/{_id(refund_id)}/accept",
            confirm=confirm,
        )

    def reject(self, refund_id: Any, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "PATCH",
            f"/refunds/{_id(refund_id)}/reject",
            confirm=confirm,
        )

    def background_export(
        self,
        file_type: str = "xlsx",
        *,
        filters: Mapping[str, Any] | None = None,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            "/refunds/seller/background-export",
            json={
                "fileType": file_type,
                "filters": _without_none(filters or {}),
            },
            confirm=confirm,
        )

    def export_legacy(
        self,
        file_extension: str = "xlsx",
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "functions",
            "POST",
            "/exportRequestCreate/pt",
            json={
                "data": {
                    "type": file_extension,
                    "data": "refunds",
                    "param": None,
                }
            },
            confirm=confirm,
        )

    def create_request(
        self,
        invoice_id: Any,
        *,
        description: str = "",
        feedback: str | None = None,
        refund_payer_data: Mapping[str, Any] | None = None,
        confirm: bool = False,
    ) -> Any:
        body: dict[str, Any] = {
            "invoiceId": invoice_id,
            "description": description,
            "feedback": feedback,
        }
        if refund_payer_data is not None:
            body["refundPayerData"] = dict(refund_payer_data)
        return self._write(
            "web",
            "POST",
            "/refunds/request",
            json=body,
            confirm=confirm,
        )

    request = create_request

    def list_payer(self, *, params: Mapping[str, Any] | None = None) -> Any:
        return self._call("web", "GET", "/payer/refunds", params=params)

    def get_payer(self, refund_id: Any) -> Any:
        return self._call("web", "GET", f"/payer/refunds/{_id(refund_id)}")

    def cancel_request(self, refund_id: Any, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "PATCH",
            f"/refunds/{_id(refund_id)}/cancel",
            confirm=confirm,
        )

    def reactivate_request(self, refund_id: Any, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "PATCH",
            f"/refunds/{_id(refund_id)}/reactivate",
            confirm=confirm,
        )
