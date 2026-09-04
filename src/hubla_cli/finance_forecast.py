"""Pure helpers for projecting Hubla withdrawal availability."""

from __future__ import annotations

import re
from calendar import monthrange
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from hubla_cli.errors import HublaContractError

RECEIVABLE_SOURCES = {"SALE", "RENEWAL", "UPGRADE"}
RESERVE_REDUCTION_SOURCES = {
    "REFUND",
    "CHARGEBACK_DISPUTE_OPENED",
    "CHARGEBACK_ACCEPTED_AFTER_DISPUTE",
    "CHARGEBACK_ACCEPTED_WITHOUT_DISPUTE",
}


def _parse_cents(value: Any, error_message: str) -> int:
    if isinstance(value, bool):
        raise HublaContractError(error_message)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError as exc:
            raise HublaContractError(error_message) from exc
    raise HublaContractError(error_message)


def _movement_cents(movement: Mapping[str, Any], error_message: str) -> int:
    try:
        value = movement["amountInCents"]
    except KeyError as exc:
        raise HublaContractError(error_message) from exc
    return _parse_cents(value, error_message)


def _external_id(movement: Mapping[str, Any]) -> str:
    value = movement.get("externalId")
    if not isinstance(value, str) or not value.strip():
        raise HublaContractError(
            "movimentação da Hubla não contém identificador externo válido"
        )
    return value


def _parse_iso_date(value: Any) -> date:
    text = str(value)
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text) is None:
        raise ValueError("date must use YYYY-MM-DD")
    return date.fromisoformat(text)


def _month_end(year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


def default_target_dates(as_of_date: date) -> list[date]:
    """Return the current and following month-end dates."""
    current = _month_end(as_of_date.year, as_of_date.month)
    if as_of_date.month == 12:
        following = _month_end(as_of_date.year + 1, 1)
    else:
        following = _month_end(as_of_date.year, as_of_date.month + 1)
    return [current, following]


def build_receivable_schedule(
    movements: Sequence[Mapping[str, Any]],
    *,
    expected_balance_in_cents: int,
) -> list[dict[str, Any]]:
    """Build and reconcile the current receivable release schedule."""
    totals: dict[str, int] = defaultdict(int)
    release_dates: dict[str, date] = {}

    for movement in movements:
        key = _external_id(movement)
        amount_in_cents = _movement_cents(
            movement,
            "movimentação a receber contém valor inválido",
        )
        totals[key] += amount_in_cents

        release_value = movement.get("releaseDate")
        if movement.get("transactionSource") in RECEIVABLE_SOURCES and release_value:
            try:
                parsed_release = _parse_iso_date(release_value)
            except ValueError as exc:
                raise HublaContractError(
                    "movimentação a receber contém data de liberação inválida"
                ) from exc
            previous = release_dates.get(key)
            if previous is None or parsed_release > previous:
                release_dates[key] = parsed_release

    grouped_amounts: dict[date, int] = defaultdict(int)
    grouped_transactions: dict[date, int] = defaultdict(int)
    for key, amount_in_cents in totals.items():
        if amount_in_cents <= 0:
            continue
        release_date = release_dates.get(key)
        if release_date is None:
            raise HublaContractError(
                "saldo a receber contém valor positivo sem data de liberação"
            )
        grouped_amounts[release_date] += amount_in_cents
        grouped_transactions[release_date] += 1

    scheduled_in_cents = sum(grouped_amounts.values())
    if scheduled_in_cents != expected_balance_in_cents:
        raise HublaContractError(
            "cronograma a receber não reconcilia com o saldo da Hubla: "
            f"saldo={expected_balance_in_cents}, cronograma={scheduled_in_cents}"
        )

    return [
        {
            "date": release_date.isoformat(),
            "amountInCents": grouped_amounts[release_date],
            "transactions": grouped_transactions[release_date],
        }
        for release_date in sorted(grouped_amounts)
    ]


def build_reserve_schedule(
    movements: Sequence[Mapping[str, Any]],
    *,
    expected_balance_in_cents: int,
    as_of_date: date,
    reserve_days: int = 30,
) -> list[dict[str, Any]]:
    """Allocate today's reserve over known sales and their projected release dates."""
    if reserve_days < 1:
        raise ValueError("reserve_days deve ser maior que zero")
    if expected_balance_in_cents < 0:
        raise HublaContractError("saldo da reserva não pode ser negativo")
    if expected_balance_in_cents == 0:
        return []

    weights: dict[str, int] = defaultdict(int)
    created_dates: dict[str, date] = {}
    for movement in movements:
        key = _external_id(movement)
        source = str(movement.get("transactionSource") or "")
        amount_in_cents = _movement_cents(
            movement,
            "movimentação contém valor inválido",
        )

        if source in RECEIVABLE_SOURCES and amount_in_cents > 0:
            created_value = movement.get("createdAt")
            try:
                created_date = _parse_iso_date(created_value)
            except ValueError as exc:
                raise HublaContractError(
                    "movimentação contém data de venda inválida"
                ) from exc
            weights[key] += amount_in_cents
            previous = created_dates.get(key)
            if previous is None or created_date > previous:
                created_dates[key] = created_date
        elif source in RESERVE_REDUCTION_SOURCES and amount_in_cents < 0:
            weights[key] += amount_in_cents
        elif source == "CHARGEBACK_REJECTED" and amount_in_cents > 0:
            weights[key] += amount_in_cents

    eligible: list[tuple[date, str, int]] = []
    for key, weight in weights.items():
        eligible_created_date = created_dates.get(key)
        if weight <= 0 or eligible_created_date is None:
            continue
        release_date = eligible_created_date + timedelta(days=reserve_days)
        if release_date > as_of_date:
            eligible.append((release_date, key, weight))

    total_weight = sum(weight for _, _, weight in eligible)
    if total_weight <= 0:
        raise HublaContractError(
            "não foi possível reconciliar a base de cálculo da reserva"
        )

    allocations: list[list[Any]] = []
    allocated_in_cents = 0
    for release_date, key, weight in eligible:
        numerator = expected_balance_in_cents * weight
        amount_in_cents, remainder = divmod(numerator, total_weight)
        allocated_in_cents += amount_in_cents
        allocations.append([release_date, key, amount_in_cents, remainder])

    remaining_cents = expected_balance_in_cents - allocated_in_cents
    allocations.sort(key=lambda row: (-int(row[3]), row[0], row[1]))
    for row in allocations[:remaining_cents]:
        row[2] = int(row[2]) + 1

    grouped_amounts: dict[date, int] = defaultdict(int)
    grouped_transactions: dict[date, int] = defaultdict(int)
    for release_date, _, amount_in_cents, _ in allocations:
        grouped_amounts[release_date] += int(amount_in_cents)
        grouped_transactions[release_date] += 1

    return [
        {
            "date": release_date.isoformat(),
            "amountInCents": grouped_amounts[release_date],
            "transactions": grouped_transactions[release_date],
        }
        for release_date in sorted(grouped_amounts)
        if grouped_amounts[release_date] > 0
    ]


def _schedule_rows(
    schedule: Sequence[Mapping[str, Any]],
) -> list[tuple[date, int]]:
    rows: list[tuple[date, int]] = []
    for entry in schedule:
        try:
            release_date = _parse_iso_date(entry["date"])
            amount_in_cents = _parse_cents(
                entry["amountInCents"],
                "cronograma financeiro contém dados inválidos",
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HublaContractError(
                "cronograma financeiro contém dados inválidos"
            ) from exc
        if amount_in_cents < 0:
            raise HublaContractError("cronograma financeiro contém valor negativo")
        rows.append((release_date, amount_in_cents))
    return rows


def build_forecast_rows(
    balance: Mapping[str, Any],
    receivable_schedule: Sequence[Mapping[str, Any]],
    reserve_schedule: Sequence[Mapping[str, Any]],
    *,
    target_dates: Sequence[date],
    as_of_date: date,
) -> list[dict[str, Any]]:
    """Add current available balance to releases due by each target date."""
    balance_error = "resposta de saldo da Hubla está incompleta"
    try:
        available_in_cents = _parse_cents(balance["availableInCents"], balance_error)
        receivable_in_cents = _parse_cents(balance["receivableInCents"], balance_error)
        reserved_in_cents = _parse_cents(balance["reservedInCents"], balance_error)
    except KeyError as exc:
        raise HublaContractError(balance_error) from exc

    receivable_rows = _schedule_rows(receivable_schedule)
    reserve_rows = _schedule_rows(reserve_schedule)
    if sum(amount for _, amount in receivable_rows) != receivable_in_cents:
        raise HublaContractError("cronograma a receber não reconcilia com o saldo")
    if sum(amount for _, amount in reserve_rows) != reserved_in_cents:
        raise HublaContractError("cronograma da reserva não reconcilia com o saldo")

    selected_dates = sorted(set(target_dates))
    if any(target_date < as_of_date for target_date in selected_dates):
        raise ValueError("a data da projeção não pode ser anterior à data do saldo")

    forecasts: list[dict[str, Any]] = []
    for target_date in selected_dates:
        receivable_release = sum(
            amount
            for release_date, amount in receivable_rows
            if release_date <= target_date
        )
        reserve_release = sum(
            amount
            for release_date, amount in reserve_rows
            if release_date <= target_date
        )
        forecasts.append(
            {
                "date": target_date.isoformat(),
                "availableNowInCents": available_in_cents,
                "receivableReleasingInCents": receivable_release,
                "reserveReleasingInCents": reserve_release,
                "projectedAvailableInCents": (
                    available_in_cents + receivable_release + reserve_release
                ),
                "remainingReceivableInCents": (
                    receivable_in_cents - receivable_release
                ),
                "remainingReservedInCents": reserved_in_cents - reserve_release,
            }
        )
    return forecasts
