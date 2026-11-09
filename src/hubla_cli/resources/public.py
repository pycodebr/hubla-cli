"""Public API implementations of the portal resource methods.

With ``backend="public"`` or ``backend="auto"`` the client swaps the portal
resources for these subclasses. Each overridden method calls Hubla's official
Public API (integration token) and returns the same shape as the portal method,
using :mod:`hubla_cli.legacy`. Methods that are not overridden keep the portal
implementation: the client refuses them in ``public`` mode and sends them to
the portal in ``auto`` mode.
"""

from __future__ import annotations

import builtins
import json
import math
import os
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from platformdirs import user_cache_path

from hubla_cli.errors import (
    AmbiguousMemberError,
    HublaContractError,
    HublaHttpError,
    MemberNotFoundError,
    PublicApiUnsupported,
)
from hubla_cli.legacy import (
    invoice_to_legacy,
    participant_to_member,
    summarize_invoices,
)
from hubla_cli.pagination import collect_paginated
from hubla_cli.public_transport import quote_id
from hubla_cli.resources.coupons import CouponsResource
from hubla_cli.resources.members import MembersResource
from hubla_cli.resources.products import ProductsResource
from hubla_cli.resources.refunds import RefundsResource
from hubla_cli.resources.sales import SalesResource
from hubla_cli.resources.subscriptions import SubscriptionsResource

PUBLIC_PAGE_SIZE = 200
ALL_TIME_START = "2015-01-01T00:00:00-03:00"
PARTICIPANTS_PAGE_SIZE = 1000
CACHE_TTL_ENV = "HUBLA_PUBLIC_CACHE_TTL"
CACHE_DIR_ENV = "HUBLA_CACHE_DIR"

# Portal invoice statuses that have another name in the Public API.
_STATUS_ALIASES = {"in_dispute": "in_protest", "disputed": "in_protest"}

# Public methods per resource (documentation and the migration report).
PUBLIC_METHODS: dict[str, tuple[str, ...]] = {
    "sales": (
        "list",
        "filter",
        "iter_all",
        "all",
        "get",
        "detail",
        "summaries",
        "net_cents",
    ),
    "products": (
        "list",
        "list_products",
        "get",
        "detail",
        "list_offers",
        "iter_offers",
        "all_offers",
        "get_offer",
        "global_offers",
    ),
    "members": (
        "active",
        "list_active",
        "iter_all",
        "all",
        "find_exact_by_email",
        "get_current_cohort_ids",
        "get_member_cohort_ids",
        "readback_cohort_ids",
        "deactivated",
        "list_deactivated",
        "create_free_subscription (sem offer_id/quantity)",
        "add (sem offer_id/quantity)",
    ),
    "subscriptions": (
        "get",
        "list (com search)",
        "filter (com search)",
        "deactivate",
        "disable_auto_renew",
        "list_smart_installments",
    ),
    "refunds": ("list_seller", "list"),
    "coupons": ("list", "get", "delete"),
}


# ----------------------------------------------------------------- helpers


def _page(
    items: builtins.list[Any], total: int, page: int, page_size: int
) -> dict[str, Any]:
    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "lastPage": max(1, math.ceil(total / page_size)) if page_size else 1,
        "_source": "public-api",
    }


def _slice(rows: builtins.list[Any], page: int, page_size: int) -> dict[str, Any]:
    start = (page - 1) * page_size
    return _page(rows[start : start + page_size], len(rows), page, page_size)


def _statuses(statuses: Sequence[str] | None) -> builtins.list[str]:
    if statuses is None:
        return ["paid"]
    return [_STATUS_ALIASES.get(str(value), str(value)) for value in statuses]


def _archived_param(archived: Any) -> str | None:
    if archived is None:
        return None
    if isinstance(archived, str):
        return "true" if archived.strip().lower() == "true" else "false"
    return "true" if archived else "false"


class _DiskCache:
    """Small JSON cache shared by CLI processes (catalog data only, no PII)."""

    def __init__(self) -> None:
        base = os.getenv(CACHE_DIR_ENV)
        self._dir = Path(base) if base else user_cache_path("hubla-cli") / "public"
        try:
            self._ttl = float(os.getenv(CACHE_TTL_ENV, "10800"))
        except ValueError:
            self._ttl = 10800.0

    def get(self, key: str, ttl: float | None = None) -> Any:
        ttl = self._ttl if ttl is None else ttl
        if ttl <= 0:
            return None
        path = self._dir / f"{key}.json"
        try:
            if time.time() - path.stat().st_mtime > ttl:
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def set(self, key: str, value: Any) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = self._dir / f"{key}.json"
            temporary = path.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_text(
                json.dumps(value, ensure_ascii=False), encoding="utf-8"
            )
            os.replace(temporary, path)
        except OSError:
            pass


class _PublicMixin:
    _client: Any

    def _public(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        confirm: bool = False,
    ) -> Any:
        return self._client.public_request(
            method, path, params=params, json=json, confirm=confirm
        )

    def _portal_or_unsupported(self, reason: str) -> None:
        if self._client.backend == "public":
            raise PublicApiUnsupported(reason)

    def _cache(self) -> _DiskCache:
        cache = self._client._public_cache.get("disk")
        if cache is None:
            cache = _DiskCache()
            self._client._public_cache["disk"] = cache
        return cache

    def _product_ids(self) -> dict[str, dict[str, str]]:
        """Map legacy and public product IDs in both directions (cached)."""
        memo = self._client._public_cache.get("product_ids")
        if memo is not None:
            return memo
        cached = self._cache().get("product_ids", ttl=86400)
        if cached is None:
            products = _collect_public_products(self)
            cached = {
                "to_public": {
                    str(row["legacyId"]): str(row["id"])
                    for row in products
                    if row.get("legacyId") and row.get("id")
                },
                "to_legacy": {
                    str(row["id"]): str(row["legacyId"])
                    for row in products
                    if row.get("legacyId") and row.get("id")
                },
            }
            self._cache().set("product_ids", cached)
        self._client._public_cache["product_ids"] = cached
        return cached

    def _public_product_id(self, product_id: str) -> str:
        ids = self._product_ids()
        if str(product_id) in ids["to_public"]:
            return ids["to_public"][str(product_id)]
        return str(product_id)

    def _legacy_product_id(self, product_id: str) -> str:
        """Members and participants only accept the product's legacy ID."""
        ids = self._product_ids()
        if str(product_id) in ids["to_legacy"]:
            return ids["to_legacy"][str(product_id)]
        return str(product_id)


def _collect_public_products(resource: _PublicMixin) -> builtins.list[Any]:
    rows: builtins.list[Any] = []
    # Without timeScope the API lists current products (digital, combo and
    # upcoming events); "past" adds finished events.
    for time_scope in (None, "past"):
        page = 1
        while True:
            body: dict[str, Any] = {
                "page": page,
                "pageSize": PUBLIC_PAGE_SIZE,
                "type": ["digital", "event", "combo"],
            }
            if time_scope:
                body["timeScope"] = time_scope
            data = resource._public("POST", "/v1/products/list", json=body)
            rows.extend(data.get("items") or [])
            if page >= int(data.get("lastPage") or 1):
                break
            page += 1
    unique: dict[str, Any] = {}
    for row in rows:
        if isinstance(row, Mapping) and row.get("id"):
            unique[str(row["id"])] = row
    return builtins.list(unique.values())


# ------------------------------------------------------------------- sales


class PublicSalesResource(_PublicMixin, SalesResource):
    """Invoices from the Public API in the portal shape."""

    def _filters(
        self,
        *,
        offer_ids: Sequence[str] | None,
        has_selected_all: bool | None,
        start_date: str | None,
        end_date: str | None,
        statuses: Sequence[str] | None,
        types: Sequence[str] | None,
        methods: Sequence[str] | None,
        search: str,
        date_range_by: str | None,
        order_by: str,
        order_direction: str,
    ) -> dict[str, Any] | None:
        filters: dict[str, Any] = {
            "orderBy": order_by,
            "orderDir": order_direction,
        }
        ids = builtins.list(offer_ids or [])
        if ids:
            filters["offerIds"] = ids
        elif has_selected_all is False:
            return None  # explicit empty selection: the portal returns nothing
        # Without dateStart the Public API answers only the last few days; the
        # portal answered the whole history. Keep the portal meaning.
        filters["dateStart"] = start_date or ALL_TIME_START
        if end_date:
            filters["dateEnd"] = end_date
        status = _statuses(statuses)
        if status:
            filters["status"] = status
        if types:
            filters["type"] = builtins.list(types)
        if methods:
            filters["paymentMethod"] = builtins.list(methods)
        if search:
            filters["search"] = search
        if date_range_by:
            filters["dateRangeBy"] = date_range_by
        return filters

    def _raw_page(self, filters: Mapping[str, Any], page: int, page_size: int) -> Any:
        return self._public(
            "POST",
            "/v1/invoices/list",
            json={
                "filters": dict(filters),
                "pagination": {"page": page, "pageSize": page_size},
            },
        )

    def _raw_all(self, filters: Mapping[str, Any]) -> builtins.list[Any]:
        rows: builtins.list[Any] = []
        page, total = 1, None
        while True:
            data = self._raw_page(filters, page, PUBLIC_PAGE_SIZE)
            pagination = data.get("pagination") or {}
            if total is not None and pagination.get("total") != total:
                raise HublaContractError("o total de faturas mudou durante a paginação")
            total = pagination.get("total")
            batch = data.get("items") or []
            rows.extend(batch)
            if not batch or page >= int(pagination.get("lastPage") or 1):
                break
            page += 1
        if total is not None and len(rows) != total:
            raise HublaContractError("paginação de faturas incompleta")
        if len({row.get("id") for row in rows}) != len(rows):
            raise HublaContractError("fatura repetida na paginação")
        return rows

    def list(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
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
    ) -> Any:
        """List invoices in the portal shape.

        The Public API lists every currency together. ``wallet="national"``
        keeps BRL invoices and ``wallet="international"`` the others, so code
        that reads both wallets still sees each invoice once. UTM filters are
        applied locally. Pages larger than 200 are assembled locally.
        """
        if wallet not in (None, "national", "international"):
            raise ValueError("wallet deve ser national ou international (minúsculas)")
        filters = self._filters(
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
            start_date=start_date,
            end_date=end_date,
            statuses=statuses,
            types=types,
            methods=methods,
            search=search,
            date_range_by=date_range_by,
            order_by=order_by,
            order_direction=order_direction,
        )
        if filters is None:
            return _page([], 0, page, page_size)
        utm = {
            "source": utm_source,
            "medium": utm_medium,
            "campaign": utm_campaign,
            "content": utm_content,
            "term": utm_term,
        }
        local = wallet is not None or any(utm.values()) or page_size > PUBLIC_PAGE_SIZE
        if not local:
            data = self._raw_page(filters, page, page_size)
            pagination = data.get("pagination") or {}
            items = [invoice_to_legacy(row) for row in data.get("items") or []]
            result = _page(items, int(pagination.get("total") or 0), page, page_size)
            result["lastPage"] = int(pagination.get("lastPage") or 1)
            return result
        key = json.dumps(filters, sort_keys=True)
        memo = self._client._public_cache.setdefault("invoices", {})
        rows = memo.get(key)
        if rows is None:
            rows = self._raw_all(filters)
            memo[key] = rows
        if wallet == "national":
            rows = [row for row in rows if (row.get("currency") or "BRL") == "BRL"]
        elif wallet == "international":
            rows = [row for row in rows if (row.get("currency") or "BRL") != "BRL"]
        for field, value in utm.items():
            if value:
                rows = [
                    row
                    for row in rows
                    if ((row.get("firstPaymentSession") or {}).get("utm") or {}).get(
                        field
                    )
                    == value
                ]
        return _slice([invoice_to_legacy(row) for row in rows], page, page_size)

    filter = list

    def get(self, invoice_id: Any) -> Any:
        data = self._public("GET", f"/v1/invoices/{quote_id(invoice_id)}")
        return invoice_to_legacy(data)

    detail = get

    def summaries(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
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
    ) -> Any:
        """Totals computed from the invoice listing (no summary route exists)."""
        del page, page_size
        data = self.list(
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
            start_date=start_date,
            end_date=end_date,
            statuses=statuses,
            types=types,
            methods=methods,
            search=search,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            date_range_by=date_range_by,
            wallet=wallet,
            page=1,
            page_size=10**6,
            order_by=order_by,
            order_direction=order_direction,
        )
        return summarize_invoices(data["items"], self.net_cents(data["items"]))

    def net_cents(self, invoices: Sequence[Mapping[str, Any]]) -> dict[str, int | None]:
        """Seller amount of each invoice, from its detail (cached per invoice version).

        The listing has no receivers; the detail does. Only amounts are cached.
        """
        result: dict[str, int | None] = {}
        for invoice in invoices:
            invoice_id = str(invoice.get("id"))
            key = f"net-{invoice_id}-{invoice.get('version') or invoice.get('modifiedAt')}"
            cached = self._cache().get(key, ttl=30 * 86400)
            if isinstance(cached, dict) and "net" in cached:
                result[invoice_id] = cached["net"]
                continue
            detail = self.get(invoice_id)
            net = (detail.get("amountDetail") or {}).get("netCents")
            result[invoice_id] = net
            if net is not None:
                self._cache().set(
                    key,
                    {
                        "net": net,
                        "platform": (detail.get("amountDetail") or {}).get(
                            "platformAmountCents"
                        ),
                        "partners": [
                            row.get("netCents")
                            for row in (detail.get("amountDetail") or {}).get(
                                "coProducers"
                            )
                            or []
                        ],
                    },
                )
        return result


# ---------------------------------------------------------------- products


class PublicProductsResource(_PublicMixin, ProductsResource):
    """Products and offers from the Public API."""

    def list(
        self,
        *,
        types: Sequence[str] | None = None,
        page: int = 1,
        page_size: int = 100,
        time_scope: str = "future",
        include_deleted: bool | None = None,
    ) -> Any:
        del include_deleted
        body: dict[str, Any] = {
            "page": page,
            "pageSize": min(page_size, PUBLIC_PAGE_SIZE),
            "type": builtins.list(types or ["digital", "event"]),
            "timeScope": time_scope,
        }
        return self._public("POST", "/v1/products/list", json=body)

    list_products = list

    def get(self, product_id: str) -> Any:
        return self._public(
            "GET", f"/v1/products/{quote_id(self._public_product_id(product_id))}"
        )

    detail = get

    def _offer_cohorts(self, product_id: str, offer_id: str) -> builtins.list[str]:
        key = f"offer-{offer_id}"
        cached = self._cache().get(key)
        if isinstance(cached, dict) and isinstance(
            cached.get("cohortIds"), builtins.list
        ):
            return [str(value) for value in cached["cohortIds"]]
        detail = self._public(
            "GET",
            f"/v1/products/{quote_id(product_id)}/offers/{quote_id(offer_id)}",
        )
        cohorts = [str(value) for value in (detail or {}).get("cohortIds") or []]
        self._cache().set(key, {"cohortIds": cohorts})
        return cohorts

    def list_offers(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        archived: bool | None = False,
    ) -> Any:
        """Offers of a product; ``cohortIds`` comes from each offer's detail (cached)."""
        public_id = self._public_product_id(product_id)
        params: dict[str, Any] = {
            "page": page,
            "pageSize": min(page_size, PUBLIC_PAGE_SIZE),
        }
        flag = _archived_param(archived)
        if flag is not None:
            params["archived"] = flag
        data = self._public(
            "GET", f"/v1/products/{quote_id(public_id)}/offers", params=params
        )
        items = []
        for row in data.get("items") or []:
            offer = dict(row)
            offer.setdefault("productId", str(product_id))
            offer["cohortIds"] = self._offer_cohorts(public_id, str(row.get("id")))
            items.append(offer)
        return {**data, "items": items, "_source": "public-api"}

    def get_offer(self, product_id: str, offer_id: str) -> Any:
        public_id = self._public_product_id(product_id)
        return self._public(
            "GET", f"/v1/products/{quote_id(public_id)}/offers/{quote_id(offer_id)}"
        )

    def global_offers(self) -> Any:
        """Own offers grouped like the portal filter (affiliate/partner lists stay empty)."""
        cached = self._cache().get("global-offers")
        if isinstance(cached, dict):
            return cached
        owner = []
        for product in _collect_public_products(self):
            for archived in ("false", "true"):
                page = 1
                while True:
                    data = self._public(
                        "GET",
                        f"/v1/products/{quote_id(product['id'])}/offers",
                        params={
                            "page": page,
                            "pageSize": PUBLIC_PAGE_SIZE,
                            "archived": archived,
                        },
                    )
                    for offer in data.get("items") or []:
                        owner.append(
                            {
                                "id": offer.get("id"),
                                "name": offer.get("name"),
                                "productId": product.get("legacyId")
                                or product.get("id"),
                                "productName": product.get("name"),
                                "isArchived": offer.get("isArchived"),
                            }
                        )
                    if page >= int(data.get("lastPage") or 1):
                        break
                    page += 1
        result = {
            "owner": owner,
            "affiliates": [],
            "partners": [],
            "_source": "public-api",
        }
        self._cache().set("global-offers", result)
        return result


# ----------------------------------------------------------------- members


class PublicMembersResource(_PublicMixin, MembersResource):
    """Members and participants from the Public API."""

    def active(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        product_id: str | None = None,
        types: Sequence[str] | None = None,
        search: str = "",
        cohort_ids: Sequence[str] | None = None,
        include_items_quantity_total: bool = True,
    ) -> Any:
        """Participants of a product in the portal member shape.

        ``cohort_ids`` is applied locally, as the portal resource already does.
        """
        del include_items_quantity_total
        if not product_id:
            raise ValueError("product_id é obrigatório na API pública")
        params: dict[str, Any] = {
            "page": page,
            "pageSize": min(page_size, PARTICIPANTS_PAGE_SIZE),
        }
        if search:
            params["search"] = search
        if types:
            params["types"] = ",".join(types)
        data = self._public(
            "GET",
            f"/v1/{quote_id(self._legacy_product_id(product_id))}/participants",
            params=params,
        )
        rows = [participant_to_member(row) for row in data.get("items") or []]
        wanted = {str(value) for value in cohort_ids or []}
        if wanted:
            rows = [row for row in rows if wanted & set(row["cohortIds"])]
        return {**data, "items": rows, "_source": "public-api"}

    list_active = active

    def iter_all(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        types: Sequence[str] | None = None,
        search: str = "",
        cohort_ids: Sequence[str] | None = None,
    ) -> Iterator[Any]:
        del page_size
        result = collect_paginated(
            lambda current_page, current_page_size: self.active(
                page=current_page,
                page_size=current_page_size,
                product_id=product_id,
                types=types,
                search=search,
            ),
            page=page,
            page_size=PARTICIPANTS_PAGE_SIZE,
            require_total=True,
        )
        wanted = {str(value) for value in cohort_ids or []}
        for member in result.items:
            if not wanted or wanted & set(member.get("cohortIds") or []):
                yield member

    def find_exact_by_email(
        self,
        product_id: str,
        email: str,
        *,
        page_size: int = 25,
        types: Sequence[str] | None = None,
    ) -> Mapping[str, Any]:
        """One participant by exact e-mail; repeated rows of one person are merged.

        The Public API returns one row per access, so the same person can appear
        more than once with the same ID. Rows are merged (cohorts united) only
        when they share the ID; different IDs for one e-mail stay ambiguous.
        """
        del page_size
        expected = email.strip().casefold()
        rows = [
            row
            for row in self.all(product_id, types=types, search=email)
            if str(row.get("email") or "").strip().casefold() == expected
        ]
        if not rows:
            raise MemberNotFoundError(
                "nenhum membro ativo corresponde ao produto e e-mail informados"
            )
        if len({str(row.get("id")) for row in rows}) > 1:
            raise AmbiguousMemberError(
                "mais de um membro ativo corresponde ao produto e e-mail informados"
            )
        merged = dict(rows[0])
        merged["cohortIds"] = builtins.list(
            dict.fromkeys(
                cohort for row in rows for cohort in row.get("cohortIds") or []
            )
        )
        return merged

    def change_cohorts(
        self,
        members: Sequence[Mapping[str, Any]],
        new_cohorts: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        """Cohort changes exist only in the portal; reads and write stay there."""
        self._portal_or_unsupported("a API pública não troca a turma de um membro")
        return MembersResource(self._client).change_cohorts(
            members=members, new_cohorts=new_cohorts, confirm=confirm
        )

    def change_cohorts_with_readback(
        self,
        *,
        product_id: str,
        member: Mapping[str, Any],
        email: str,
        new_cohorts: Sequence[str],
        confirm: bool = False,
    ) -> Mapping[str, Any]:
        """Portal write with portal lookup and readback, so IDs come from one source.

        ``member`` may come from the Public API listing, whose IDs are not
        guaranteed to match the portal's member IDs. The member is therefore
        resolved again in the portal by exact product and e-mail, and its
        current cohorts must match the ones the caller saw.
        """
        self._portal_or_unsupported("a API pública não troca a turma de um membro")
        portal = MembersResource(self._client)
        current = portal.find_exact_by_email(product_id, email)
        seen = {str(value) for value in member.get("cohortIds") or []}
        observed = {str(value) for value in current.get("cohortIds") or []}
        if member.get("cohortIds") is not None and seen != observed:
            raise HublaContractError(
                "as turmas lidas pela API pública divergem das do portal; "
                "nenhuma alteração foi feita"
            )
        return portal.change_cohorts_with_readback(
            product_id=product_id,
            member=current,
            email=email,
            new_cohorts=new_cohorts,
            confirm=confirm,
        )

    def deactivated(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        product_id: str | None = None,
        search: str = "",
    ) -> Any:
        if search:
            self._portal_or_unsupported(
                "a API pública não busca membros desativados por e-mail"
            )
            return MembersResource.deactivated(
                self,
                page=page,
                page_size=page_size,
                product_id=product_id,
                search=search,
            )
        if not product_id:
            raise ValueError("product_id é obrigatório na API pública")
        return self._public(
            "GET",
            f"/v1/{quote_id(self._legacy_product_id(product_id))}/members",
            params={
                "page": page,
                "pageSize": min(page_size, PUBLIC_PAGE_SIZE),
                "status": "deactivate",
            },
        )

    list_deactivated = deactivated

    def create_free_subscription(
        self,
        *,
        product_id: str,
        emails: Sequence[str],
        lifetime: bool,
        days: int | None = None,
        offer_id: str | None = None,
        quantity: int | None = None,
        confirm: bool = False,
    ) -> Any:
        """Free access by invite; with ``offer_id`` or ``quantity`` it needs the portal."""
        if offer_id is not None or quantity is not None:
            self._portal_or_unsupported(
                "a API pública não convida para uma oferta ou turma específica"
            )
            return MembersResource.create_free_subscription(
                self,
                product_id=product_id,
                emails=emails,
                lifetime=lifetime,
                days=days,
                offer_id=offer_id,
                quantity=quantity,
                confirm=confirm,
            )
        body: dict[str, Any] = {"emails": builtins.list(emails), "lifetime": lifetime}
        if days is not None and not lifetime:
            body["days"] = days
        return self._public(
            "POST",
            f"/v1/{quote_id(self._legacy_product_id(product_id))}/members/invites",
            json=body,
            confirm=confirm,
        )

    add = create_free_subscription


# ----------------------------------------------------------- subscriptions


class PublicSubscriptionsResource(_PublicMixin, SubscriptionsResource):
    """Subscriptions from the Public API."""

    def get(self, subscription_id: Any) -> Any:
        return self._public("GET", f"/v1/subscriptions/{quote_id(subscription_id)}")

    def list(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
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
    ) -> Any:
        """Subscriptions of one buyer, built from invoices (the API has no listing).

        Requires ``search`` (buyer e-mail, name or document). Each subscription
        found in the buyer's invoices is read by ID and receives the product
        and offer names of its invoices.
        """
        if not search or plan_type or is_free_trial_active is not None:
            self._portal_or_unsupported(
                "a API pública não lista assinaturas; informe search para buscar "
                "pelas faturas do comprador"
            )
            return SubscriptionsResource.list(
                self,
                offer_ids=offer_ids,
                has_selected_all=has_selected_all,
                start_date=start_date,
                end_date=end_date,
                statuses=statuses,
                search=search,
                date_range_by=date_range_by,
                plan_type=plan_type,
                is_free_trial_active=is_free_trial_active,
                page=page,
                page_size=page_size,
                order_by=order_by,
                order_direction=order_direction,
            )
        sales = PublicSalesResource(self._client)
        invoices = sales.list(
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
            search=search,
            statuses=[],
            page=1,
            page_size=10**6,
        )["items"]
        names: dict[str, dict[str, Any]] = {}
        for invoice in invoices:
            for offer in invoice.get("offers") or []:
                sub_id = offer.get("associatedSubscriptionId")
                if sub_id and str(sub_id) not in names:
                    names[str(sub_id)] = {
                        "offerId": offer.get("id"),
                        "offerName": offer.get("name"),
                        "productName": offer.get("name"),
                    }
        rows = []
        wanted = {str(value) for value in statuses or []}
        for sub_id, extra in names.items():
            try:
                detail = self.get(sub_id)
            except HublaHttpError as exc:
                if exc.status_code == 404:
                    continue
                raise
            row = {**(detail or {}), **extra, "_source": "public-api"}
            last = row.get("lastInvoice") or {}
            row.setdefault("lastChargeStatus", last.get("status"))
            if wanted and row.get("status") not in wanted:
                continue
            rows.append(row)
        return _slice(rows, page, page_size)

    filter = list

    def deactivate(self, subscription_id: Any, *, confirm: bool = False) -> Any:
        return self._public(
            "PATCH",
            f"/v1/subscriptions/{quote_id(subscription_id)}/deactivate",
            confirm=confirm,
        )

    def disable_auto_renew(self, subscription_id: Any, *, confirm: bool = False) -> Any:
        return self._public(
            "PATCH",
            f"/v1/subscriptions/{quote_id(subscription_id)}/disable-auto-renew",
            confirm=confirm,
        )

    def list_smart_installments(self, **kwargs: Any) -> Any:
        page = int(kwargs.pop("page", 1))
        page_size = int(kwargs.pop("page_size", 25))
        filters: dict[str, Any] = {}
        offer_ids = kwargs.pop("offer_ids", None)
        if offer_ids:
            filters["offerIds"] = builtins.list(offer_ids)
        for source, target in (
            ("statuses", "status"),
            ("search", "search"),
            ("start_date", "dateStart"),
            ("end_date", "dateEnd"),
        ):
            value = kwargs.pop(source, None)
            if value:
                filters[target] = value
        return self._public(
            "POST",
            "/v1/smart-installments/list",
            json={
                "filters": filters,
                "pagination": {
                    "page": page,
                    "pageSize": min(page_size, PUBLIC_PAGE_SIZE),
                },
            },
        )


# ------------------------------------------------------- refunds / coupons


class PublicRefundsResource(_PublicMixin, RefundsResource):
    """Refund requests from the Public API (status filter only)."""

    def list_seller(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        filters: Mapping[str, Any] | None = None,
    ) -> Any:
        body: dict[str, Any] = {
            "pagination": {"page": page, "pageSize": min(page_size, PUBLIC_PAGE_SIZE)}
        }
        status = (filters or {}).get("status")
        if status:
            body["filters"] = {"status": status}
        return self._public("POST", "/v1/refunds/list", json=body)

    list = list_seller


class PublicCouponsResource(_PublicMixin, CouponsResource):
    """Coupons from the Public API."""

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
        del has_selected_all
        filters: dict[str, Any] = {}
        if offer_ids:
            filters["offerIds"] = builtins.list(offer_ids)
        if statuses:
            filters["states"] = builtins.list(statuses)
        if search:
            filters["code"] = search.upper()
        return self._public(
            "POST",
            "/v1/coupons/list",
            json={
                "filters": filters,
                "page": page,
                "pageSize": min(page_size, PUBLIC_PAGE_SIZE),
                "orderBy": order_by,
                "orderDirection": order_direction,
            },
        )

    def get(self, coupon_id: str) -> Any:
        return self._public("GET", f"/v1/coupons/{quote_id(coupon_id)}")

    def delete(self, coupon_id: str, *, confirm: bool = False) -> Any:
        return self._public(
            "DELETE", f"/v1/coupons/{quote_id(coupon_id)}", confirm=confirm
        )


PUBLIC_RESOURCE_CLASSES: dict[str, Callable[[Any], Any]] = {
    "sales": PublicSalesResource,
    "products": PublicProductsResource,
    "members": PublicMembersResource,
    "subscriptions": PublicSubscriptionsResource,
    "refunds": PublicRefundsResource,
    "coupons": PublicCouponsResource,
}
