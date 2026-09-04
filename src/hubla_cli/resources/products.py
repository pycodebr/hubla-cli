"""Product, offer, cohort, and content resources."""

from __future__ import annotations

import builtins
from collections.abc import Iterator, Mapping, Sequence
from typing import Any
from urllib.parse import quote

from hubla_cli.pagination import collect_paginated
from hubla_cli.resources.base import ResourceBase


def _id(value: Any) -> str:
    return quote(str(value), safe="")


class ProductsResource(ResourceBase):
    """Inspect and manage products, offers, cohorts, settings, and resources."""

    def list(
        self,
        *,
        types: Sequence[str] | None = None,
        page: int = 1,
        page_size: int = 100,
        time_scope: str = "future",
        include_deleted: bool | None = None,
    ) -> Any:
        params: dict[str, Any] = {
            "type": list(types or ["digital", "event"]),
            "page": page,
            "pageSize": page_size,
            "timeScope": time_scope,
        }
        if include_deleted is not None:
            params["includeDeleted"] = include_deleted
        return self._call("product", "GET", "/products", params=params)

    def get(self, product_id: str) -> Any:
        return self._call("product", "GET", f"/products/{_id(product_id)}")

    detail = get

    def create(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product", "POST", "/products", json=dict(payload), confirm=confirm
        )

    def change_status(
        self,
        product_id: str,
        status: str,
        *,
        confirm: bool = False,
    ) -> Any:
        status_map = {
            "selling": "selling",
            "not_selling": "notSelling",
            "waitlist": "waitlist",
        }
        return self._write(
            "product",
            "PATCH",
            f"/products/{_id(product_id)}/status",
            json={"status": status_map.get(status, status)},
            confirm=confirm,
        )

    def delete(self, product_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "product", "DELETE", f"/products/{_id(product_id)}", confirm=confirm
        )

    def toggle_visibility(self, product_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "product",
            "PATCH",
            f"/products/{_id(product_id)}/visibility",
            confirm=confirm,
        )

    def list_offers(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        archived: bool | None = False,
    ) -> Any:
        return self._call(
            "product",
            "GET",
            f"/products/{_id(product_id)}/offers",
            params={"page": page, "pageSize": page_size, "archived": archived},
        )

    def iter_offers(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        archived: bool | None = False,
    ) -> Iterator[Any]:
        """Yield every offer for a product while reconciling pagination."""
        result = collect_paginated(
            lambda current_page, current_page_size: self.list_offers(
                product_id,
                page=current_page,
                page_size=current_page_size,
                archived=archived,
            ),
            page=page,
            page_size=page_size,
        )
        return iter(result.items)

    def all_offers(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        archived: bool | None = False,
    ) -> builtins.list[Any]:
        """Return every offer for a product."""
        return list(
            self.iter_offers(
                product_id,
                page=page,
                page_size=page_size,
                archived=archived,
            )
        )

    list_products = list

    def get_offer(self, product_id: str, offer_id: str) -> Any:
        return self._call(
            "product",
            "GET",
            f"/products/{_id(product_id)}/offers/{_id(offer_id)}/edit",
        )

    def create_offer(
        self,
        product_id: str,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "POST",
            f"/products/{_id(product_id)}/offers",
            json=dict(payload),
            confirm=confirm,
        )

    def update_offer(
        self,
        product_id: str,
        offer_id: str,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "PUT",
            f"/products/{_id(product_id)}/offers/{_id(offer_id)}/edit",
            json=dict(payload),
            confirm=confirm,
        )

    def archive_offer(
        self,
        product_id: str,
        offer_id: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "POST",
            f"/products/{_id(product_id)}/offers/{_id(offer_id)}/archive",
            confirm=confirm,
        )

    def unarchive_offers(
        self,
        product_id: str,
        offer_ids: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "POST",
            f"/products/{_id(product_id)}/offers/unarchive",
            json={"offerIds": list(offer_ids)},
            confirm=confirm,
        )

    def duplicate_offer(
        self,
        product_id: str,
        offer_id: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "POST",
            f"/products/{_id(product_id)}/offers/{_id(offer_id)}/duplicate",
            confirm=confirm,
        )

    def change_offer_status(
        self,
        product_id: str,
        offer_id: str,
        status: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "PUT",
            f"/products/{_id(product_id)}/offers/{_id(offer_id)}/status",
            json={"status": status},
            confirm=confirm,
        )

    def rename_offer(
        self,
        product_id: str,
        offer_id: str,
        name: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "PATCH",
            f"/products/{_id(product_id)}/offers/{_id(offer_id)}/name",
            json={"name": name},
            confirm=confirm,
        )

    def global_offers(self) -> Any:
        return self._call("product", "GET", "/filters/offers")

    def global_product_filters(self) -> Any:
        return self._call("product", "GET", "/filters/products")

    def list_cohorts(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        enhance_with_details: bool = False,
    ) -> Any:
        return self._call(
            "product",
            "GET",
            f"/products/{_id(product_id)}/cohorts",
            params={
                "page": page,
                "pageSize": page_size,
                "enhanceWithDetails": enhance_with_details,
            },
        )

    def get_cohort(self, product_id: str, cohort_id: str) -> Any:
        """Read one cohort belonging to a product."""
        return self._call(
            "product",
            "GET",
            f"/products/{_id(product_id)}/cohorts/{_id(cohort_id)}",
        )

    def iter_cohorts(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        enhance_with_details: bool = False,
    ) -> Iterator[Any]:
        """Yield every cohort while reconciling the provider pagination."""
        result = collect_paginated(
            lambda current_page, current_page_size: self.list_cohorts(
                product_id,
                page=current_page,
                page_size=current_page_size,
                enhance_with_details=enhance_with_details,
            ),
            page=page,
            page_size=page_size,
        )
        return iter(result.items)

    def all_cohorts(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 100,
        enhance_with_details: bool = False,
    ) -> builtins.list[Any]:
        """Return every cohort for a product."""
        return list(
            self.iter_cohorts(
                product_id,
                page=page,
                page_size=page_size,
                enhance_with_details=enhance_with_details,
            )
        )

    def create_cohort(
        self,
        product_id: str,
        name: str,
        *,
        sections: Sequence[str] = (),
        groups: Sequence[str] = (),
        tracks: Sequence[str] = (),
        confirm: bool = False,
    ) -> Any:
        resource_ids = [*sections, *groups, *tracks]
        return self._write(
            "product",
            "POST",
            f"/products/{_id(product_id)}/cohorts",
            json={"name": name, "resourceIds": resource_ids, "isDefault": False},
            confirm=confirm,
        )

    def update_cohort(
        self,
        product_id: str,
        cohort_id: str,
        name: str,
        *,
        sections: Sequence[str] = (),
        groups: Sequence[str] = (),
        tracks: Sequence[str] = (),
        confirm: bool = False,
    ) -> Any:
        resource_ids = [*sections, *groups, *tracks]
        return self._write(
            "product",
            "PUT",
            f"/products/{_id(product_id)}/cohorts/{_id(cohort_id)}",
            json={"name": name, "externalResourceIds": resource_ids},
            confirm=confirm,
        )

    def rename_cohort(
        self,
        product_id: str,
        cohort_id: str,
        name: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "PATCH",
            f"/products/{_id(product_id)}/cohorts/{_id(cohort_id)}/name",
            json={"name": name},
            confirm=confirm,
        )

    def duplicate_cohort(
        self,
        product_id: str,
        cohort_id: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "POST",
            f"/products/{_id(product_id)}/cohorts/{_id(cohort_id)}/duplicate",
            confirm=confirm,
        )

    def get_combo_cohorts(self, product_id: str) -> Any:
        return self._call(
            "product",
            "GET",
            f"/products/{_id(product_id)}/offers/combo-cohorts",
        )

    def update_combo_cohorts(
        self,
        product_id: str,
        cohort_ids: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "PUT",
            f"/products/{_id(product_id)}/offers/combo-cohorts",
            json={"cohortIds": list(cohort_ids)},
            confirm=confirm,
        )

    def get_offers_and_cohorts(self, product_id: str) -> Any:
        return self._call(
            "product",
            "GET",
            f"/products/{_id(product_id)}/offers/offers-and-cohorts",
        )

    def products_by_offer_ids(
        self,
        main_offer_ids: Sequence[str],
        *,
        page: int = 1,
        page_size: int = 25,
    ) -> Any:
        return self._call(
            "product",
            "POST",
            "/products/get-by-offer-ids",
            json={
                "mainOfferIds": list(main_offer_ids),
                "page": page,
                "pageSize": page_size,
            },
        )

    def get_settings(self, product_id: str, setting_type: str) -> Any:
        return self._call(
            "product",
            "GET",
            f"/products/{_id(product_id)}/settings/{_id(setting_type)}",
        )

    def save_settings(
        self,
        product_id: str,
        setting_type: str,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "PATCH",
            f"/products/{_id(product_id)}/settings/{_id(setting_type)}",
            json=dict(payload),
            confirm=confirm,
        )

    def ticket_counters(self, product_id: str) -> Any:
        return self._call(
            "product", "GET", f"/products/{_id(product_id)}/ticket-counters"
        )

    def external_contents(self, product_id: str) -> Any:
        return self._call(
            "product", "GET", "/external-contents", params={"productId": product_id}
        )

    def list_resources(
        self,
        resource_type: str,
        *,
        has_product_association: bool | None = None,
    ) -> Any:
        params = (
            {}
            if has_product_association is None
            else {"hasProductAssociation": has_product_association}
        )
        return self._call(
            "product",
            "GET",
            f"/resources/get-resources-by-filters/{_id(resource_type)}",
            params=params,
        )

    def associated_cohorts(
        self,
        resource_external_id: str,
        product_id: str,
    ) -> Any:
        return self._call(
            "product",
            "GET",
            "/resources/get-associated-cohorts/"
            f"{_id(resource_external_id)}/{_id(product_id)}",
        )

    def resources_by_cohort_ids(
        self,
        cohort_ids: Sequence[str],
        *,
        resource_type: str = "SECOND_BRAIN",
    ) -> Any:
        return self._call(
            "product",
            "POST",
            "/resources/get-resources-by-cohort-ids",
            json={"cohortIds": list(cohort_ids), "type": resource_type},
        )

    def update_offer_resource(
        self,
        resource_id: str,
        product_id: str,
        payload: Mapping[str, Any],
        *,
        cohort_ids: Sequence[str] = (),
        confirm: bool = False,
    ) -> Any:
        body = dict(payload)
        body["cohortsIds"] = list(cohort_ids)
        return self._write(
            "product",
            "PATCH",
            f"/resources/update-offer-resource/{_id(resource_id)}/{_id(product_id)}",
            json=body,
            confirm=confirm,
        )

    def delete_resource(self, resource_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "product", "DELETE", f"/resources/{_id(resource_id)}", confirm=confirm
        )

    def bind_resource(
        self,
        offer_id: str,
        external_resource_id: str,
        cohort_ids: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "POST",
            f"/products/bind-resource/{_id(offer_id)}",
            json={
                "externalResourceId": external_resource_id,
                "cohortIds": list(cohort_ids),
            },
            confirm=confirm,
        )

    def unbind_resource(
        self,
        offer_id: str,
        external_resource_id: str,
        cohort_ids: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "POST",
            f"/products/unbind-resource/{_id(offer_id)}",
            json={
                "externalResourceId": external_resource_id,
                "cohortIds": list(cohort_ids),
            },
            confirm=confirm,
        )

    def bind_brain(
        self,
        offer_id: str,
        brain_id: str,
        cohort_ids: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "POST",
            f"/products/bind-brain/{_id(offer_id)}",
            json={"externalResourceId": brain_id, "cohortIds": list(cohort_ids)},
            confirm=confirm,
        )

    def unbind_brain(
        self,
        offer_id: str,
        brain_id: str,
        cohort_ids: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "POST",
            f"/products/unbind-brain/{_id(offer_id)}",
            json={"externalResourceId": brain_id, "cohortIds": list(cohort_ids)},
            confirm=confirm,
        )
