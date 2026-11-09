"""Convert Public API payloads into the shapes returned by the portal BFF.

Automations written against the portal (``sales.get``, ``members.all`` and
friends) read portal field names such as ``offers[].id``, ``memberRef``,
``amount.paidCents`` or ``payerSession.utmSource``. The Public API exposes the
same facts with other names. These helpers keep every Public API field and add
the portal names on top, so existing callers keep working. Fields that the
Public API does not provide are left out instead of being invented.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SOURCE = "public-api"

# Statuses whose invoice was paid at some point.
_PAID_ONCE = {"paid", "refunded", "chargeback", "in_protest"}


def _cents(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _receivers(invoice: Mapping[str, Any], role: str) -> list[Mapping[str, Any]]:
    return [
        receiver
        for receiver in invoice.get("receivers") or []
        if isinstance(receiver, Mapping) and receiver.get("role") == role
    ]


def _sum_cents(rows: Sequence[Mapping[str, Any]]) -> int | None:
    values = [_cents(row.get("totalCents")) for row in rows]
    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def invoice_to_legacy(
    invoice: Mapping[str, Any],
    *,
    refunded_cents: int | None = None,
) -> dict[str, Any]:
    """Return the invoice with portal-compatible fields added.

    ``refunded_cents`` is the refunded amount when known (from
    ``/v1/refunds/list``). Without it, a ``refunded`` invoice is treated as a
    full refund, which is how Hubla reports a refund on the invoice status.
    """
    result: dict[str, Any] = dict(invoice)
    status = invoice.get("status")
    amount = dict(invoice.get("amount") or {})
    total = _cents(amount.get("totalCents"))
    paid_once = status in _PAID_ONCE and bool(invoice.get("paidAt"))

    paid_cents: int | None = total if paid_once else 0
    if status == "paid":
        returned: int | None = 0
    elif status == "refunded":
        returned = refunded_cents if refunded_cents is not None else total
    elif status == "chargeback":
        returned = total
    elif paid_once:
        returned = None
    else:
        returned = 0
    amount["paidCents"] = paid_cents
    amount["returnedCents"] = returned
    result["amount"] = amount

    items = [item for item in invoice.get("items") or [] if isinstance(item, Mapping)]
    subscription_ids = [
        str(value) for value in invoice.get("subscriptionIds") or [] if value
    ]
    main_subscription = invoice.get("subscriptionId")

    def item_subscription(index: int) -> Any:
        if len(subscription_ids) == len(items) and subscription_ids:
            return subscription_ids[index]
        return main_subscription

    result["items"] = [
        {
            **item,
            "offerId": item.get("id"),
            "productName": item.get("name"),
        }
        for item in items
    ]
    result["offers"] = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "associatedSubscriptionId": item_subscription(index),
        }
        for index, item in enumerate(items)
    ]

    payer = dict(invoice.get("payer") or {})
    payer["identity"] = {
        "email": payer.get("email"),
        "fullName": payer.get("name"),
        "phone": payer.get("phone"),
        "document": payer.get("document"),
    }
    result["payer"] = payer
    result["memberRef"] = {
        "id": invoice.get("payerId") or payer.get("id"),
        "email": payer.get("email"),
        "fullName": payer.get("name"),
        "phone": payer.get("phone"),
    }

    session = invoice.get("firstPaymentSession") or {}
    utm = session.get("utm") or {}
    cookies = session.get("cookies") or {}
    result["payerSession"] = {
        "utmSource": utm.get("source"),
        "utmMedium": utm.get("medium"),
        "utmCampaign": utm.get("campaign"),
        "utmContent": utm.get("content"),
        "utmTerm": utm.get("term"),
        "fbp": cookies.get("fbp"),
        "fbclid": cookies.get("fbclid"),
        "gclid": cookies.get("gclid"),
    }

    if invoice.get("receivers"):
        partners = _receivers(invoice, "partner")
        result["amountDetail"] = {
            "totalCents": total,
            "netCents": _sum_cents(_receivers(invoice, "seller")),
            "platformAmountCents": _sum_cents(_receivers(invoice, "platform")),
            "installmentFeeCents": _cents(amount.get("installmentFeeCents")),
            "coProducers": [
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "netCents": _cents(row.get("totalCents")),
                }
                for row in partners
            ],
        }
    if "updatedAt" not in result and invoice.get("modifiedAt"):
        result["updatedAt"] = invoice.get("modifiedAt")
    result["_source"] = SOURCE
    return result


def participant_to_member(participant: Mapping[str, Any]) -> dict[str, Any]:
    """Return a participant row with the portal member fields used by callers."""
    result: dict[str, Any] = dict(participant)
    cohort_ids = [str(value) for value in participant.get("cohortIds") or [] if value]
    result["cohortIds"] = cohort_ids
    if "phoneNumber" not in result and participant.get("phone"):
        result["phoneNumber"] = participant.get("phone")
    # The Public API does not say which offer created each access.
    result["memberAccesses"] = [
        {"cohortId": access.get("cohortId"), "parentOfferId": None}
        for access in participant.get("accesses") or []
        if isinstance(access, Mapping)
    ]
    result["_source"] = SOURCE
    return result


def summarize_invoices(
    invoices: Sequence[Mapping[str, Any]],
    net_cents: Mapping[str, int | None] | None = None,
) -> dict[str, Any]:
    """Compute the portal ``invoices/summaries`` totals from listed invoices.

    ``sumPaid`` and ``netRevenue`` are in major units (reais), like the portal.
    The invoice listing has no receivers, so ``net_cents`` maps each invoice ID
    to the seller amount read from the invoice detail. ``netRevenue`` is None
    when any invoice has no known net value.
    """
    count = len(invoices)
    count_items = 0
    paid = 0
    net: int | None = 0
    for invoice in invoices:
        count_items += len(invoice.get("items") or [])
        total = _cents((invoice.get("amount") or {}).get("totalCents")) or 0
        paid += total
        seller = (
            _sum_cents(_receivers(invoice, "seller"))
            if invoice.get("receivers")
            else None
        )
        if seller is None and net_cents is not None:
            seller = net_cents.get(str(invoice.get("id")))
        net = None if net is None or seller is None else net + seller
    return {
        "count": count,
        "countItems": count_items,
        "sumPaid": paid / 100,
        "netRevenue": None if net is None else net / 100,
        "_source": SOURCE,
    }
