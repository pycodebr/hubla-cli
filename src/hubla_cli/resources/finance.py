"""Financial statement resources."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from hubla_cli.resources.base import ResourceBase


def _id(value: Any) -> str:
    return quote(str(value), safe="")


class FinanceResource(ResourceBase):
    """Inspect balances and movements and perform confirmed withdrawals."""

    def balance(self, currency: str | None = None) -> Any:
        params = {"currency": currency} if currency else None
        return self._call("web", "GET", "/financial-statement/balance", params=params)

    def account_statement(
        self,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return self._call(
            "web",
            "GET",
            "/financial-statement/account-statement",
            params=params,
        )

    def movements(self, *, params: Mapping[str, Any] | None = None) -> Any:
        return self._call("web", "GET", "/financial-statement/movements", params=params)

    def movements_export(
        self,
        *,
        params: Mapping[str, Any] | None = None,
        receiver_email: str | None = None,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            "/financial-statement/movements/export",
            params=params,
            json={"receiverEmail": receiver_email},
            confirm=confirm,
        )

    def invoice_details(self, invoice_id: str) -> Any:
        return self._call(
            "web", "GET", f"/dashboard/creator/invoices/{_id(invoice_id)}"
        )

    def invoice_movements(self, invoice_id: str) -> Any:
        return self._call(
            "web",
            "GET",
            f"/financial-statement/invoices/{_id(invoice_id)}/movements",
        )

    def withdrawal_details(self, withdrawal_id: str) -> Any:
        return self._call(
            "web",
            "GET",
            f"/financial-statement/withdrawals/{_id(withdrawal_id)}",
        )

    def withdraw(
        self,
        amount_in_cents: int,
        currency: str = "BRL",
        validation_code: str | None = None,
        *,
        confirm: bool = False,
    ) -> Any:
        body = {
            "amountInCents": amount_in_cents,
            "currency": currency,
            "validationCode": validation_code,
        }
        return self._write(
            "web",
            "POST",
            "/financial-statement/withdrawal/web",
            json=body,
            confirm=confirm,
        )
