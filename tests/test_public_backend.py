from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from hubla_cli.client import HublaClient, resolve_backend
from hubla_cli.errors import (
    AmbiguousMemberError,
    ConfirmationRequired,
    CredentialError,
    HublaAuthError,
    HublaHttpError,
    PublicApiUnsupported,
)
from hubla_cli.legacy import (
    invoice_to_legacy,
    participant_to_member,
    summarize_invoices,
)
from hubla_cli.public_transport import PublicApiTransport, is_read_request

Handler = Callable[[str, str, dict[str, Any]], Any]


class FakePublic:
    """Public API double that records calls and answers through a handler."""

    def __init__(self, handler: Handler | None = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.handler = handler or (lambda method, path, kwargs: {})

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append((method, path, kwargs))
        return self.handler(method, path, kwargs)


class FakePortal:
    def __init__(self, answer: Any = None) -> None:
        self.calls: list[tuple[str, str, str, dict[str, Any]]] = []
        self.answer = answer

    def request(self, service: str, method: str, path: str, **kwargs: Any) -> Any:
        self.calls.append((service, method, path, kwargs))
        if callable(self.answer):
            return self.answer(service, method, path, kwargs)
        return self.answer


def invoice(**overrides: Any) -> dict[str, Any]:
    base = {
        "id": "inv-1",
        "status": "paid",
        "paidAt": "2026-11-05T12:00:00.000Z",
        "modifiedAt": "2026-11-05T12:01:00.000Z",
        "currency": "BRL",
        "payerId": "user-1",
        "payer": {
            "id": "user-1",
            "name": "Aluno",
            "email": "aluno@example.com",
            "phone": "+5511999999999",
            "document": "000",
        },
        "subscriptionId": "sub-1",
        "subscriptionIds": ["sub-1"],
        "items": [{"id": "offer-1", "name": "IA Master"}],
        "amount": {
            "subtotalCents": 1000,
            "discountCents": 0,
            "installmentFeeCents": 100,
            "totalCents": 1100,
        },
        "firstPaymentSession": {
            "utm": {"source": "meta", "medium": "ads", "campaign": "c1"},
            "cookies": {"fbp": "fb.1"},
        },
        "receivers": [],
        "version": 3,
    }
    base.update(overrides)
    return base


def public_client(
    handler: Handler, *, portal: Any = None, backend: str = "public"
) -> HublaClient:
    client = HublaClient(
        backend=backend,
        public_transport=FakePublic(handler),
        transport=portal,
    )
    client._public_cache["product_ids"] = {
        "to_public": {"legacy-1": "public-1"},
        "to_legacy": {"public-1": "legacy-1"},
    }
    return client


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HUBLA_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("HUBLA_BACKEND", raising=False)
    monkeypatch.delenv("HUBLA_API_TOKEN", raising=False)


# ------------------------------------------------------------- transport


class Response:
    def __init__(
        self, status: int, payload: Any = None, headers: dict[str, str] | None = None
    ):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}
        self.content = b"x" if payload is not None else b""

    def json(self) -> Any:
        return self._payload


class Session:
    def __init__(self, responses: list[Response]) -> None:
        self.responses = responses
        self.sent: list[dict[str, Any]] = []

    def request(self, **kwargs: Any) -> Response:
        self.sent.append(kwargs)
        return self.responses.pop(0)


def test_transport_sends_raw_token_and_retries_reads_on_429() -> None:
    session = Session(
        [Response(429, {}, {"Retry-After": "1"}), Response(200, {"ok": 1})]
    )
    waits: list[float] = []
    transport = PublicApiTransport("tok123", session=session, sleep=waits.append)
    assert transport.request("POST", "/v1/invoices/list", json={}) == {"ok": 1}
    assert session.sent[0]["headers"]["Authorization"] == "tok123"
    assert session.sent[0]["url"].startswith(
        "https://backend-bff-public-api.platform.hub.la/v1/"
    )
    assert waits == [2.0]


def test_transport_never_retries_writes() -> None:
    session = Session([Response(429, {})])
    transport = PublicApiTransport("tok", session=session, sleep=lambda _: None)
    with pytest.raises(HublaHttpError):
        transport.request("PATCH", "/v1/subscriptions/x/deactivate")
    assert len(session.sent) == 1


@pytest.mark.parametrize("token", ["", "Bearer abc", " abc", "a b"])
def test_transport_rejects_bad_tokens(token: str) -> None:
    with pytest.raises(HublaAuthError):
        PublicApiTransport(token)


@pytest.mark.parametrize(
    "path", ["https://evil/v1/x", "/v1/../x", "/v2/x", "/v1/x?a=1"]
)
def test_transport_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(ValueError):
        PublicApiTransport("tok", session=Session([])).request("GET", path)


def test_read_classification() -> None:
    assert is_read_request("GET", "/v1/invoices/1")
    assert is_read_request("POST", "/v1/invoices/list")
    assert not is_read_request("POST", "/v1/products")


# ---------------------------------------------------------------- legacy


def test_paid_invoice_gets_portal_fields() -> None:
    row = invoice_to_legacy(invoice())
    assert row["offers"] == [
        {"id": "offer-1", "name": "IA Master", "associatedSubscriptionId": "sub-1"}
    ]
    assert row["items"][0]["offerId"] == "offer-1"
    assert row["memberRef"] == {
        "id": "user-1",
        "email": "aluno@example.com",
        "fullName": "Aluno",
        "phone": "+5511999999999",
    }
    assert row["payer"]["identity"]["email"] == "aluno@example.com"
    assert row["amount"]["paidCents"] == 1100
    assert row["amount"]["returnedCents"] == 0
    assert row["payerSession"]["utmSource"] == "meta"
    assert row["updatedAt"] == "2026-11-05T12:01:00.000Z"
    assert "amountDetail" not in row  # listing rows have no receivers
    assert row["_source"] == "public-api"


def test_refunded_and_chargeback_are_full_returns() -> None:
    refunded = invoice_to_legacy(invoice(status="refunded"))
    assert (
        refunded["amount"]["paidCents"] == refunded["amount"]["returnedCents"] == 1100
    )
    partial = invoice_to_legacy(invoice(status="refunded"), refunded_cents=500)
    assert partial["amount"]["returnedCents"] == 500
    chargeback = invoice_to_legacy(invoice(status="chargeback"))
    assert chargeback["amount"]["returnedCents"] == 1100


def test_unpaid_invoice_has_zero_paid_amount() -> None:
    row = invoice_to_legacy(invoice(status="expired", paidAt=None))
    assert row["amount"]["paidCents"] == 0
    assert row["amount"]["returnedCents"] == 0


def test_items_map_to_their_own_subscriptions_when_lengths_match() -> None:
    row = invoice_to_legacy(
        invoice(
            items=[{"id": "o1", "name": "A"}, {"id": "o2", "name": "B"}],
            subscriptionIds=["s1", "s2"],
        )
    )
    assert [o["associatedSubscriptionId"] for o in row["offers"]] == ["s1", "s2"]


def test_receivers_become_net_and_coproducers() -> None:
    row = invoice_to_legacy(
        invoice(
            receivers=[
                {"role": "seller", "totalCents": 700},
                {"role": "partner", "id": "p", "name": "Coprodutor", "totalCents": 250},
                {"role": "platform", "totalCents": 150},
            ]
        )
    )
    detail = row["amountDetail"]
    assert detail["netCents"] == 700
    assert detail["platformAmountCents"] == 150
    assert detail["coProducers"] == [{"id": "p", "name": "Coprodutor", "netCents": 250}]


def test_participant_rows_keep_cohorts_without_inventing_offers() -> None:
    member = participant_to_member(
        {
            "id": "m",
            "email": "a@b.c",
            "cohortIds": ["c1"],
            "accesses": [{"cohortId": "c1"}],
        }
    )
    assert member["cohortIds"] == ["c1"]
    assert member["memberAccesses"] == [{"cohortId": "c1", "parentOfferId": None}]


def test_summaries_need_known_net_for_every_invoice() -> None:
    rows = [invoice(id="a"), invoice(id="b", items=[{"id": "1"}, {"id": "2"}])]
    summary = summarize_invoices(rows, {"a": 700, "b": 300})
    assert summary["count"] == 2
    assert summary["countItems"] == 3
    assert summary["sumPaid"] == 22.0
    assert summary["netRevenue"] == 10.0
    assert summarize_invoices(rows, {"a": 700})["netRevenue"] is None


# ---------------------------------------------------------------- client


def test_backend_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    assert resolve_backend() == "portal"
    monkeypatch.setenv("HUBLA_BACKEND", "AUTO")
    assert resolve_backend() == "auto"
    assert resolve_backend("public") == "public"
    with pytest.raises(ValueError):
        resolve_backend("bff")


def test_public_profile_requires_a_token(tmp_path: Any) -> None:
    from hubla_cli.credentials import ApiTokenStore

    store = ApiTokenStore(config_dir=tmp_path, keyring_backend=False)
    with pytest.raises(CredentialError):
        HublaClient.from_profile(backend="public", token_store=store)
    store.save("tok-saved")
    client = HublaClient.from_profile(backend="public", token_store=store)
    assert client.backend == "public"
    assert store.load() == "tok-saved"
    store.delete()
    assert store.load() is None


def test_public_mode_refuses_portal_only_operations() -> None:
    client = public_client(lambda m, p, k: {})
    with pytest.raises(PublicApiUnsupported):
        client.members.pending_invites()
    with pytest.raises(PublicApiUnsupported):
        client.account.business()


def test_auto_mode_sends_uncovered_operations_to_the_portal() -> None:
    portal = FakePortal({"items": []})
    client = public_client(lambda m, p, k: {}, portal=portal, backend="auto")
    client.members.pending_invites()
    assert portal.calls[0][:3] == ("members_area", "GET", "/invites/list/pending")


def test_public_writes_require_confirmation() -> None:
    client = public_client(lambda m, p, k: {})
    with pytest.raises(ConfirmationRequired):
        client.subscriptions.deactivate("sub-1")
    client.subscriptions.deactivate("sub-1", confirm=True)
    assert client._public_transport.calls[-1][:2] == (
        "PATCH",
        "/v1/subscriptions/sub-1/deactivate",
    )


# ----------------------------------------------------------------- sales


def test_sales_list_maps_filters_and_defaults_to_paid() -> None:
    def handler(method: str, path: str, kwargs: dict[str, Any]) -> Any:
        return {"items": [invoice()], "pagination": {"total": 1, "lastPage": 1}}

    client = public_client(handler)
    page = client.sales.list(
        offer_ids=["offer-1"],
        has_selected_all=False,
        start_date="2026-11-01T00:00:00-03:00",
        search="aluno@example.com",
        page_size=50,
    )
    body = client._public_transport.calls[0][2]["json"]
    assert body["filters"]["offerIds"] == ["offer-1"]
    assert body["filters"]["status"] == ["paid"]
    assert body["filters"]["dateStart"] == "2026-11-01T00:00:00-03:00"
    assert body["pagination"] == {"page": 1, "pageSize": 50}
    assert page["total"] == 1
    assert page["items"][0]["offers"][0]["id"] == "offer-1"


def test_sales_list_all_statuses_and_explicit_empty_selection() -> None:
    client = public_client(lambda m, p, k: {"items": [], "pagination": {"total": 0}})
    client.sales.list(statuses=[])
    filters = client._public_transport.calls[0][2]["json"]["filters"]
    assert "status" not in filters
    assert filters["dateStart"] == "2015-01-01T00:00:00-03:00"  # whole history
    assert client.sales.list(offer_ids=[], has_selected_all=False)["total"] == 0
    assert len(client._public_transport.calls) == 1


def test_sales_wallets_split_currencies_locally() -> None:
    rows = [invoice(id="brl"), invoice(id="usd", currency="USD")]

    def handler(method: str, path: str, kwargs: dict[str, Any]) -> Any:
        return {"items": rows, "pagination": {"total": 2, "lastPage": 1}}

    client = public_client(handler)
    national = client.sales.list(wallet="national", page_size=100)
    international = client.sales.list(wallet="international", page_size=100)
    assert [r["id"] for r in national["items"]] == ["brl"]
    assert [r["id"] for r in international["items"]] == ["usd"]
    assert len(client._public_transport.calls) == 1  # cached per client


def test_sales_large_page_collects_every_public_page() -> None:
    pages = {
        1: [invoice(id=f"a{i}") for i in range(200)],
        2: [invoice(id="b0")],
    }

    def handler(method: str, path: str, kwargs: dict[str, Any]) -> Any:
        page = kwargs["json"]["pagination"]["page"]
        return {"items": pages[page], "pagination": {"total": 201, "lastPage": 2}}

    client = public_client(handler)
    result = client.sales.list(page_size=10**6)
    assert result["total"] == 201
    assert len(result["items"]) == 201


def test_sales_summaries_read_net_from_details_once() -> None:
    def handler(method: str, path: str, kwargs: dict[str, Any]) -> Any:
        if path == "/v1/invoices/list":
            return {"items": [invoice()], "pagination": {"total": 1, "lastPage": 1}}
        return invoice(
            receivers=[
                {"role": "seller", "totalCents": 800},
                {"role": "platform", "totalCents": 300},
            ]
        )

    client = public_client(handler)
    first = client.sales.summaries()
    assert first["netRevenue"] == 8.0
    calls = len(client._public_transport.calls)
    client._public_cache.pop("invoices", None)
    client.sales.summaries()
    assert len(client._public_transport.calls) == calls + 1  # detail came from cache


# --------------------------------------------------------------- members


def test_members_use_legacy_product_and_filter_cohorts() -> None:
    rows = [
        {"id": "m1", "email": "a@x.com", "cohortIds": ["c1"]},
        {"id": "m2", "email": "b@x.com", "cohortIds": ["c2"]},
    ]

    def handler(method: str, path: str, kwargs: dict[str, Any]) -> Any:
        return {"items": rows, "total": 2, "page": 1, "pageSize": 1000, "lastPage": 1}

    client = public_client(handler)
    members = client.members.all("public-1", cohort_ids=["c2"])
    assert client._public_transport.calls[0][1] == "/v1/legacy-1/participants"
    assert [m["id"] for m in members] == ["m2"]


def test_find_exact_merges_rows_of_the_same_person() -> None:
    rows = [
        {"id": "m1", "email": "A@x.com", "cohortIds": ["c1"]},
        {"id": "m1", "email": "a@x.com", "cohortIds": ["c2"]},
    ]
    client = public_client(
        lambda m, p, k: {"items": rows, "total": len(rows), "page": 1, "lastPage": 1}
    )
    member = client.members.find_exact_by_email("legacy-1", "a@x.com")
    assert member["cohortIds"] == ["c1", "c2"]
    rows.append({"id": "m9", "email": "a@x.com", "cohortIds": []})
    with pytest.raises(AmbiguousMemberError):
        client.members.find_exact_by_email("legacy-1", "a@x.com")


def test_free_access_without_offer_uses_public_invites() -> None:
    client = public_client(lambda m, p, k: {"status": [{"isCreated": True}]})
    client.members.create_free_subscription(
        product_id="legacy-1", emails=["a@x.com"], lifetime=True, confirm=True
    )
    method, path, kwargs = client._public_transport.calls[-1]
    assert (method, path) == ("POST", "/v1/legacy-1/members/invites")
    assert kwargs["json"] == {"emails": ["a@x.com"], "lifetime": True}
    with pytest.raises(PublicApiUnsupported):
        client.members.create_free_subscription(
            product_id="legacy-1",
            emails=["a@x.com"],
            lifetime=True,
            offer_id="offer-9",
            confirm=True,
        )


def test_cohort_changes_stay_in_the_portal() -> None:
    client = public_client(lambda m, p, k: {})
    with pytest.raises(PublicApiUnsupported):
        client.members.change_cohorts([{"id": "m"}], ["c"], confirm=True)
    portal = FakePortal({"ok": True})
    auto = public_client(lambda m, p, k: {}, portal=portal, backend="auto")
    auto.members.change_cohorts([{"id": "m", "cohortIds": []}], ["c"], confirm=True)
    assert portal.calls[0][:3] == ("access", "POST", "/access/change-members-cohorts")


# ------------------------------------------------- products / subscriptions


def test_offers_use_public_product_id_and_cache_cohorts() -> None:
    def handler(method: str, path: str, kwargs: dict[str, Any]) -> Any:
        if path == "/v1/products/public-1/offers":
            return {
                "items": [{"id": "o1", "name": "Oferta"}],
                "total": 1,
                "lastPage": 1,
            }
        return {"id": "o1", "cohortIds": ["c1"]}

    client = public_client(handler)
    offers = client.products.all_offers("legacy-1", archived="true")
    assert offers[0]["cohortIds"] == ["c1"]
    assert client._public_transport.calls[0][2]["params"]["archived"] == "true"
    calls = len(client._public_transport.calls)
    client.products.all_offers("legacy-1", archived="true")
    assert len(client._public_transport.calls) == calls + 1  # only the listing again


def test_subscriptions_by_buyer_come_from_invoices() -> None:
    def handler(method: str, path: str, kwargs: dict[str, Any]) -> Any:
        if path == "/v1/invoices/list":
            assert "status" not in kwargs["json"]["filters"]
            return {"items": [invoice()], "pagination": {"total": 1, "lastPage": 1}}
        return {"id": "sub-1", "status": "active", "lastInvoice": {"status": "paid"}}

    client = public_client(handler)
    result = client.subscriptions.list(search="aluno@example.com")
    assert result["total"] == 1
    row = result["items"][0]
    assert row["productName"] == "IA Master"
    assert row["lastChargeStatus"] == "paid"
    with pytest.raises(PublicApiUnsupported):
        client.subscriptions.list()
