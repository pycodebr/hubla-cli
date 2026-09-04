from __future__ import annotations

from datetime import date
from typing import Any

import pytest

import hubla_cli.resources.finance as finance_resource
from hubla_cli.catalog import build_catalog
from hubla_cli.client import HublaClient
from hubla_cli.errors import HublaContractError
from hubla_cli.finance_forecast import (
    build_forecast_rows,
    build_receivable_schedule,
    build_reserve_schedule,
    default_target_dates,
)


class PaginatedMovementsTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        service: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(
            {"service": service, "method": method, "path": path, **kwargs}
        )
        if kwargs["params"].get("after") == "next-page":
            return {
                "movements": [
                    {
                        "date": "2026-09-03",
                        "movements": [
                            {"id": "duplicate"},
                            {"id": "movement-2"},
                        ],
                    }
                ]
            }
        return {
            "movements": [
                {
                    "date": "2026-09-04",
                    "movements": [
                        {"id": "movement-1"},
                        {"id": "duplicate"},
                    ],
                }
            ],
            "after": "next-page",
        }


class StaticMovementsTransport:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def request(
        self,
        service: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        return self.payload


class ForecastTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        service: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(
            {"service": service, "method": method, "path": path, **kwargs}
        )
        if path == "/financial-statement/balance":
            return {
                "availableInCents": 1_000,
                "receivableInCents": 250,
                "transferableInCents": 0,
                "contestedInCents": 0,
                "reservedInCents": 101,
                "currency": "BRL",
            }
        if path == "/financial-statement/movements":
            return {
                "movements": [
                    {
                        "date": "2026-09-01",
                        "movements": [
                            {
                                "id": "movement-1",
                                "externalId": "invoice-1",
                                "amountInCents": 100,
                                "transactionSource": "SALE",
                                "createdAt": "2026-08-25",
                                "releaseDate": "2026-09-10",
                            },
                            {
                                "id": "movement-2",
                                "externalId": "invoice-2",
                                "amountInCents": 150,
                                "transactionSource": "RENEWAL",
                                "createdAt": "2026-09-01",
                                "releaseDate": "2026-09-16",
                            },
                        ],
                    }
                ]
            }
        raise AssertionError(f"unexpected request: {method} {path}")


class FractionalBalanceTransport(ForecastTransport):
    def request(
        self,
        service: str,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        result = super().request(service, method, path, **kwargs)
        if path == "/financial-statement/balance":
            result["receivableInCents"] = 250.5
        return result


def test_contract_error_is_part_of_the_public_library_api() -> None:
    from hubla_cli import HublaContractError as exported_error

    assert exported_error is HublaContractError


def test_forecast_catalog_does_not_allow_forging_snapshot_or_reserve_policy() -> None:
    operation = build_catalog()["resources"]["finance"]["operations"][
        "availability_forecast"
    ]

    assert set(operation["parameters"]) == {
        "target_dates",
        "currency",
        "timezone",
    }


def test_default_target_dates_returns_current_and_next_month_end() -> None:
    assert default_target_dates(date(2026, 9, 4)) == [
        date(2026, 9, 30),
        date(2026, 10, 31),
    ]


def test_all_movements_follows_cursor_and_deduplicates_ids() -> None:
    transport = PaginatedMovementsTransport()
    client = HublaClient(transport=transport)

    movements = client.finance.all_movements(
        account_type="receivable",
        start_date="2026-08-01T00:00:00-03:00",
        end_date="2026-09-04T23:59:59-03:00",
        currency="BRL",
    )

    assert [movement["id"] for movement in movements] == [
        "movement-1",
        "duplicate",
        "movement-2",
    ]
    assert len(transport.calls) == 2
    assert transport.calls[0]["params"] == {
        "accountType": "receivable",
        "startDate": "2026-08-01T00:00:00-03:00",
        "endDate": "2026-09-04T23:59:59-03:00",
        "limit": 100,
        "currency": "BRL",
    }
    assert transport.calls[1]["params"]["after"] == "next-page"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"movements": [None]},
        {"movements": [{}]},
        {"movements": [{"movements": "invalid"}]},
        {"movements": [{"movements": [None]}]},
    ],
)
def test_all_movements_fails_closed_on_malformed_payload(payload: Any) -> None:
    client = HublaClient(transport=StaticMovementsTransport(payload))

    with pytest.raises(HublaContractError, match="formato inválido"):
        client.finance.all_movements(
            account_type="receivable",
            start_date="2026-08-01T00:00:00-03:00",
            end_date="2026-09-04T23:59:59-03:00",
        )


def test_all_movements_rejects_a_movement_without_an_id() -> None:
    client = HublaClient(
        transport=StaticMovementsTransport(
            {
                "movements": [
                    {
                        "movements": [
                            {
                                "externalId": "invoice-1",
                                "amountInCents": 100,
                            }
                        ]
                    }
                ]
            }
        )
    )

    with pytest.raises(HublaContractError, match="identificador"):
        client.finance.all_movements(
            account_type="receivable",
            start_date="2026-08-01T00:00:00-03:00",
            end_date="2026-09-04T23:59:59-03:00",
        )


@pytest.mark.parametrize("movement_id", ["", "   ", 1, True])
def test_all_movements_requires_a_non_empty_string_id(movement_id: Any) -> None:
    client = HublaClient(
        transport=StaticMovementsTransport(
            {"movements": [{"movements": [{"id": movement_id}]}]}
        )
    )

    with pytest.raises(HublaContractError, match="identificador"):
        client.finance.all_movements(
            account_type="receivable",
            start_date="2026-08-01T00:00:00-03:00",
            end_date="2026-09-04T23:59:59-03:00",
        )


def test_availability_forecast_requires_extended_iso_target_dates(
    monkeypatch: Any,
) -> None:
    transport = ForecastTransport()
    client = HublaClient(transport=transport)
    monkeypatch.setattr(
        finance_resource,
        "_current_date",
        lambda selected_timezone: date(2026, 9, 4),
    )

    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        client.finance.availability_forecast(target_dates=["20260930"])


def test_availability_forecast_rejects_fractional_balance_cents(
    monkeypatch: Any,
) -> None:
    client = HublaClient(transport=FractionalBalanceTransport())
    monkeypatch.setattr(
        finance_resource,
        "_current_date",
        lambda selected_timezone: date(2026, 9, 4),
    )

    with pytest.raises(HublaContractError, match="saldo da Hubla"):
        client.finance.availability_forecast()


def test_availability_forecast_returns_reconciled_month_end_snapshots(
    monkeypatch: Any,
) -> None:
    transport = ForecastTransport()
    client = HublaClient(transport=transport)
    monkeypatch.setattr(
        finance_resource,
        "_current_date",
        lambda selected_timezone: date(2026, 9, 4),
    )

    result = client.finance.availability_forecast(
        timezone="America/Sao_Paulo",
    )

    assert result["asOfDate"] == "2026-09-04"
    assert result["currency"] == "BRL"
    assert result["currentBalance"]["availableInCents"] == 1_000
    assert result["forecasts"] == [
        {
            "date": "2026-09-30",
            "availableNowInCents": 1_000,
            "receivableReleasingInCents": 250,
            "reserveReleasingInCents": 40,
            "projectedAvailableInCents": 1_290,
            "remainingReceivableInCents": 0,
            "remainingReservedInCents": 61,
        },
        {
            "date": "2026-10-31",
            "availableNowInCents": 1_000,
            "receivableReleasingInCents": 250,
            "reserveReleasingInCents": 101,
            "projectedAvailableInCents": 1_351,
            "remainingReceivableInCents": 0,
            "remainingReservedInCents": 0,
        },
    ]
    assert result["assumptions"] == {
        "futureSalesIncluded": False,
        "futureRefundsAndChargebacksIncluded": False,
        "withdrawalFeeIncluded": False,
        "reserveScheduleEstimated": True,
        "reserveReleaseDays": 30,
        "timezone": "America/Sao_Paulo",
    }
    movement_call = next(
        call
        for call in transport.calls
        if call["path"] == "/financial-statement/movements"
    )
    assert movement_call["params"]["accountType"] == "receivable"
    assert movement_call["params"]["startDate"] == "2026-07-06T00:00:00-03:00"
    assert movement_call["params"]["endDate"] == "2026-09-04T23:59:59-03:00"
    assert [call["path"] for call in transport.calls] == [
        "/financial-statement/movements",
        "/financial-statement/balance",
    ]


def test_receivable_schedule_nets_each_invoice_and_groups_release_dates() -> None:
    movements = [
        {
            "id": "movement-1",
            "externalId": "invoice-1",
            "amountInCents": 100,
            "transactionSource": "SALE",
            "releaseDate": "2026-09-10",
        },
        {
            "id": "movement-2",
            "externalId": "invoice-2",
            "amountInCents": 200,
            "transactionSource": "RENEWAL",
            "releaseDate": "2026-10-05",
        },
        {
            "id": "movement-3",
            "externalId": "invoice-2",
            "amountInCents": -50,
            "transactionSource": "REFUND",
        },
        {
            "id": "movement-4",
            "externalId": "invoice-released",
            "amountInCents": 300,
            "transactionSource": "SALE",
            "releaseDate": "2026-09-01",
        },
        {
            "id": "movement-5",
            "externalId": "invoice-released",
            "amountInCents": -300,
            "transactionSource": "SALE_RELEASED",
        },
    ]

    assert build_receivable_schedule(movements, expected_balance_in_cents=250) == [
        {"date": "2026-09-10", "amountInCents": 100, "transactions": 1},
        {"date": "2026-10-05", "amountInCents": 150, "transactions": 1},
    ]


@pytest.mark.parametrize(
    ("amount_in_cents", "expected_balance_in_cents"),
    [
        (True, 1),
        (100.0, 100),
        (100.5, 100),
    ],
)
def test_receivable_schedule_requires_integer_cent_amounts(
    amount_in_cents: Any,
    expected_balance_in_cents: int,
) -> None:
    movements = [
        {
            "id": "movement-1",
            "externalId": "invoice-1",
            "amountInCents": amount_in_cents,
            "transactionSource": "SALE",
            "releaseDate": "2026-09-10",
        }
    ]

    with pytest.raises(HublaContractError, match="valor inválido"):
        build_receivable_schedule(
            movements,
            expected_balance_in_cents=expected_balance_in_cents,
        )


def test_receivable_schedule_rejects_a_missing_cent_amount() -> None:
    movements = [
        {
            "id": "movement-1",
            "externalId": "invoice-1",
            "transactionSource": "SALE",
            "releaseDate": "2026-09-10",
        }
    ]

    with pytest.raises(HublaContractError, match="valor inválido"):
        build_receivable_schedule(movements, expected_balance_in_cents=0)


@pytest.mark.parametrize("external_id", ["", "   ", 1, True, None])
def test_receivable_schedule_requires_a_non_empty_string_external_id(
    external_id: Any,
) -> None:
    movements = [
        {
            "id": "movement-1",
            "externalId": external_id,
            "amountInCents": 100,
            "transactionSource": "SALE",
            "releaseDate": "2026-09-10",
        }
    ]

    with pytest.raises(HublaContractError, match="identificador externo"):
        build_receivable_schedule(movements, expected_balance_in_cents=100)


def test_receivable_schedule_requires_extended_iso_release_date() -> None:
    movements = [
        {
            "id": "movement-1",
            "externalId": "invoice-1",
            "amountInCents": 100,
            "transactionSource": "SALE",
            "releaseDate": "20260910",
        }
    ]

    with pytest.raises(HublaContractError, match="data de liberação inválida"):
        build_receivable_schedule(movements, expected_balance_in_cents=100)


def test_receivable_schedule_refuses_an_unreconciled_balance() -> None:
    movements = [
        {
            "externalId": "invoice-1",
            "amountInCents": 100,
            "transactionSource": "SALE",
            "releaseDate": "2026-09-10",
        }
    ]

    with pytest.raises(HublaContractError, match="não reconcilia"):
        build_receivable_schedule(movements, expected_balance_in_cents=101)


def test_reserve_schedule_allocates_exact_balance_over_release_dates() -> None:
    movements = [
        {
            "externalId": "invoice-1",
            "amountInCents": 100,
            "transactionSource": "SALE",
            "createdAt": "2026-08-10",
        },
        {
            "externalId": "invoice-2",
            "amountInCents": 300,
            "transactionSource": "RENEWAL",
            "createdAt": "2026-08-20",
        },
        {
            "externalId": "invoice-2",
            "amountInCents": -100,
            "transactionSource": "REFUND",
            "createdAt": "2026-08-25",
        },
        {
            "externalId": "invoice-old",
            "amountInCents": 1_000,
            "transactionSource": "SALE",
            "createdAt": "2026-07-01",
        },
    ]

    assert build_reserve_schedule(
        movements,
        expected_balance_in_cents=101,
        as_of_date=date(2026, 9, 4),
        reserve_days=30,
    ) == [
        {"date": "2026-09-09", "amountInCents": 34, "transactions": 1},
        {"date": "2026-09-19", "amountInCents": 67, "transactions": 1},
    ]


def test_reserve_schedule_restores_a_rejected_chargeback() -> None:
    movements = [
        {
            "id": "movement-1",
            "externalId": "invoice-1",
            "amountInCents": 100,
            "transactionSource": "SALE",
            "createdAt": "2026-08-20",
        },
        {
            "id": "movement-2",
            "externalId": "invoice-1",
            "amountInCents": -100,
            "transactionSource": "CHARGEBACK_DISPUTE_OPENED",
            "createdAt": "2026-08-25",
        },
        {
            "id": "movement-3",
            "externalId": "invoice-1",
            "amountInCents": 100,
            "transactionSource": "CHARGEBACK_REJECTED",
            "createdAt": "2026-09-01",
        },
    ]

    assert build_reserve_schedule(
        movements,
        expected_balance_in_cents=100,
        as_of_date=date(2026, 9, 4),
        reserve_days=30,
    ) == [
        {"date": "2026-09-19", "amountInCents": 100, "transactions": 1},
    ]


def test_reserve_schedule_requires_extended_iso_created_date() -> None:
    movements = [
        {
            "id": "movement-1",
            "externalId": "invoice-1",
            "amountInCents": 100,
            "transactionSource": "SALE",
            "createdAt": "20260820",
        }
    ]

    with pytest.raises(HublaContractError, match="data de venda inválida"):
        build_reserve_schedule(
            movements,
            expected_balance_in_cents=100,
            as_of_date=date(2026, 9, 4),
        )


@pytest.mark.parametrize(
    ("amount_in_cents", "expected_balance_in_cents"),
    [
        (True, 1),
        (100.0, 100),
        (100.5, 100),
    ],
)
def test_reserve_schedule_requires_integer_cent_amounts(
    amount_in_cents: Any,
    expected_balance_in_cents: int,
) -> None:
    movements = [
        {
            "id": "movement-1",
            "externalId": "invoice-1",
            "amountInCents": amount_in_cents,
            "transactionSource": "SALE",
            "createdAt": "2026-08-20",
        }
    ]

    with pytest.raises(HublaContractError, match="valor inválido"):
        build_reserve_schedule(
            movements,
            expected_balance_in_cents=expected_balance_in_cents,
            as_of_date=date(2026, 9, 4),
        )


def test_reserve_schedule_refuses_positive_balance_without_a_basis() -> None:
    with pytest.raises(HublaContractError, match="base de cálculo"):
        build_reserve_schedule(
            [],
            expected_balance_in_cents=1,
            as_of_date=date(2026, 9, 4),
        )


@pytest.mark.parametrize(
    ("balance_field", "receivable_schedule", "reserve_schedule"),
    [
        ("availableInCents", [], []),
        (
            "receivableInCents",
            [{"date": "2026-09-10", "amountInCents": 1}],
            [],
        ),
        (
            "reservedInCents",
            [],
            [{"date": "2026-09-10", "amountInCents": 1}],
        ),
    ],
)
def test_forecast_rows_requires_integer_balance_cent_amounts(
    balance_field: str,
    receivable_schedule: list[dict[str, Any]],
    reserve_schedule: list[dict[str, Any]],
) -> None:
    balance: dict[str, Any] = {
        "availableInCents": 0,
        "receivableInCents": 0,
        "reservedInCents": 0,
    }
    balance[balance_field] = 1.5

    with pytest.raises(HublaContractError, match="saldo da Hubla"):
        build_forecast_rows(
            balance,
            receivable_schedule,
            reserve_schedule,
            target_dates=[date(2026, 9, 30)],
            as_of_date=date(2026, 9, 4),
        )


@pytest.mark.parametrize(
    ("balance", "receivable_schedule", "reserve_schedule"),
    [
        (
            {
                "availableInCents": 0,
                "receivableInCents": 1,
                "reservedInCents": 0,
            },
            [{"date": "2026-09-10", "amountInCents": 1.5}],
            [],
        ),
        (
            {
                "availableInCents": 0,
                "receivableInCents": 0,
                "reservedInCents": 1,
            },
            [],
            [{"date": "2026-09-10", "amountInCents": 1.5}],
        ),
    ],
)
def test_forecast_rows_requires_integer_schedule_cent_amounts(
    balance: dict[str, Any],
    receivable_schedule: list[dict[str, Any]],
    reserve_schedule: list[dict[str, Any]],
) -> None:
    with pytest.raises(HublaContractError, match="cronograma financeiro"):
        build_forecast_rows(
            balance,
            receivable_schedule,
            reserve_schedule,
            target_dates=[date(2026, 9, 30)],
            as_of_date=date(2026, 9, 4),
        )


def test_forecast_rows_requires_extended_iso_schedule_date() -> None:
    balance = {
        "availableInCents": 0,
        "receivableInCents": 1,
        "reservedInCents": 0,
    }
    receivable_schedule = [{"date": "20260910", "amountInCents": 1}]

    with pytest.raises(HublaContractError, match="cronograma financeiro"):
        build_forecast_rows(
            balance,
            receivable_schedule,
            [],
            target_dates=[date(2026, 9, 30)],
            as_of_date=date(2026, 9, 4),
        )


def test_forecast_rows_add_only_releases_through_each_target() -> None:
    balance = {
        "availableInCents": 1_000,
        "receivableInCents": 250,
        "reservedInCents": 101,
    }
    receivable_schedule = [
        {"date": "2026-09-10", "amountInCents": 100},
        {"date": "2026-10-05", "amountInCents": 150},
    ]
    reserve_schedule = [
        {"date": "2026-09-09", "amountInCents": 34},
        {"date": "2026-09-19", "amountInCents": 67},
    ]

    assert build_forecast_rows(
        balance,
        receivable_schedule,
        reserve_schedule,
        target_dates=[
            date(2026, 10, 31),
            date(2026, 9, 15),
            date(2026, 9, 30),
        ],
        as_of_date=date(2026, 9, 4),
    ) == [
        {
            "date": "2026-09-15",
            "availableNowInCents": 1_000,
            "receivableReleasingInCents": 100,
            "reserveReleasingInCents": 34,
            "projectedAvailableInCents": 1_134,
            "remainingReceivableInCents": 150,
            "remainingReservedInCents": 67,
        },
        {
            "date": "2026-09-30",
            "availableNowInCents": 1_000,
            "receivableReleasingInCents": 100,
            "reserveReleasingInCents": 101,
            "projectedAvailableInCents": 1_201,
            "remainingReceivableInCents": 150,
            "remainingReservedInCents": 0,
        },
        {
            "date": "2026-10-31",
            "availableNowInCents": 1_000,
            "receivableReleasingInCents": 250,
            "reserveReleasingInCents": 101,
            "projectedAvailableInCents": 1_351,
            "remainingReceivableInCents": 0,
            "remainingReservedInCents": 0,
        },
    ]
