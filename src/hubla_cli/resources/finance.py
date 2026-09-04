"""Financial statement resources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timedelta
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from hubla_cli.errors import HublaContractError
from hubla_cli.finance_forecast import (
    _parse_cents,
    _parse_iso_date,
    build_forecast_rows,
    build_receivable_schedule,
    build_reserve_schedule,
    default_target_dates,
)
from hubla_cli.resources.base import ResourceBase

FINANCIAL_ACCOUNT_TYPES = {
    "available",
    "receivable",
    "transferable",
    "contested",
    "reserved",
}
FORECAST_LOOKBACK_DAYS = 60
DEFAULT_RESERVE_DAYS = 30
DEFAULT_FINANCE_TIMEZONE = "America/Sao_Paulo"


def _current_date(selected_timezone: ZoneInfo) -> date:
    return datetime.now(selected_timezone).date()


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

    def all_movements(
        self,
        *,
        account_type: str,
        start_date: str,
        end_date: str,
        currency: str = "BRL",
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Read every movement in a date window, following Hubla cursors."""
        if account_type not in FINANCIAL_ACCOUNT_TYPES:
            allowed = ", ".join(sorted(FINANCIAL_ACCOUNT_TYPES))
            raise ValueError(f"account_type deve ser um de: {allowed}")
        if not 1 <= page_size <= 100:
            raise ValueError("page_size deve estar entre 1 e 100")

        base_params: dict[str, Any] = {
            "accountType": account_type,
            "startDate": start_date,
            "endDate": end_date,
            "limit": page_size,
            "currency": currency,
        }
        result: list[dict[str, Any]] = []
        movement_ids: set[str] = set()
        seen_cursors: set[str] = set()
        cursor: str | None = None

        while True:
            params = dict(base_params)
            if cursor is not None:
                params["after"] = cursor
            page = self.movements(params=params)
            if not isinstance(page, Mapping):
                raise HublaContractError(
                    "a Hubla retornou uma página de movimentações inválida"
                )
            groups = page.get("movements")
            if not isinstance(groups, Sequence) or isinstance(groups, (str, bytes)):
                raise HublaContractError(
                    "a Hubla retornou movimentações em formato inválido"
                )
            for group in groups:
                if not isinstance(group, Mapping):
                    raise HublaContractError(
                        "a Hubla retornou movimentações em formato inválido"
                    )
                movements = group.get("movements")
                if not isinstance(movements, Sequence) or isinstance(
                    movements, (str, bytes)
                ):
                    raise HublaContractError(
                        "a Hubla retornou movimentações em formato inválido"
                    )
                for movement in movements:
                    if not isinstance(movement, Mapping):
                        raise HublaContractError(
                            "a Hubla retornou movimentações em formato inválido"
                        )
                    movement_id = movement.get("id")
                    if not isinstance(movement_id, str) or not movement_id.strip():
                        raise HublaContractError(
                            "movimentação da Hubla não contém identificador"
                        )
                    if movement_id in movement_ids:
                        continue
                    movement_ids.add(movement_id)
                    result.append(dict(movement))

            next_cursor = page.get("after")
            if not next_cursor:
                return result
            cursor = str(next_cursor)
            if cursor in seen_cursors:
                raise HublaContractError(
                    "a paginação de movimentações repetiu o mesmo cursor"
                )
            seen_cursors.add(cursor)

    def availability_forecast(
        self,
        *,
        target_dates: Sequence[str] | None = None,
        currency: str = "BRL",
        timezone: str = DEFAULT_FINANCE_TIMEZONE,
    ) -> dict[str, Any]:
        """Project withdrawable balance for dates using the current snapshot."""
        try:
            selected_timezone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"fuso horário inválido: {timezone}") from exc
        selected_as_of_date = _current_date(selected_timezone)

        if target_dates is None or len(target_dates) == 0:
            selected_target_dates = default_target_dates(selected_as_of_date)
        else:
            if isinstance(target_dates, (str, bytes)):
                raise ValueError("target_dates deve ser uma lista de datas")
            try:
                selected_target_dates = [
                    _parse_iso_date(target_date) for target_date in target_dates
                ]
            except ValueError as exc:
                raise ValueError(
                    "cada target_date deve usar o formato YYYY-MM-DD"
                ) from exc

        start_date = selected_as_of_date - timedelta(days=FORECAST_LOOKBACK_DAYS)
        start_datetime = datetime.combine(
            start_date,
            time(0, 0, 0, tzinfo=selected_timezone),
        )
        end_datetime = datetime.combine(
            selected_as_of_date,
            time(23, 59, 59, tzinfo=selected_timezone),
        )
        movements = self.all_movements(
            account_type="receivable",
            start_date=start_datetime.isoformat(),
            end_date=end_datetime.isoformat(),
            currency=currency,
        )
        balance = self.balance(currency)
        if not isinstance(balance, Mapping):
            raise HublaContractError("a Hubla retornou um saldo em formato inválido")
        balance_error = "resposta de saldo da Hubla está incompleta"
        try:
            receivable_balance = _parse_cents(
                balance["receivableInCents"], balance_error
            )
            reserve_balance = _parse_cents(balance["reservedInCents"], balance_error)
        except KeyError as exc:
            raise HublaContractError(balance_error) from exc

        receivable_schedule = build_receivable_schedule(
            movements,
            expected_balance_in_cents=receivable_balance,
        )
        reserve_schedule = build_reserve_schedule(
            movements,
            expected_balance_in_cents=reserve_balance,
            as_of_date=selected_as_of_date,
            reserve_days=DEFAULT_RESERVE_DAYS,
        )
        forecasts = build_forecast_rows(
            balance,
            receivable_schedule,
            reserve_schedule,
            target_dates=selected_target_dates,
            as_of_date=selected_as_of_date,
        )
        return {
            "asOfDate": selected_as_of_date.isoformat(),
            "currency": str(balance.get("currency") or currency),
            "currentBalance": dict(balance),
            "receivableSchedule": receivable_schedule,
            "reserveSchedule": reserve_schedule,
            "forecasts": forecasts,
            "assumptions": {
                "futureSalesIncluded": False,
                "futureRefundsAndChargebacksIncluded": False,
                "withdrawalFeeIncluded": False,
                "reserveScheduleEstimated": True,
                "reserveReleaseDays": DEFAULT_RESERVE_DAYS,
                "timezone": timezone,
            },
        }

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
