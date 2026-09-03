"""Storefront resources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

from hubla_cli.resources.base import ResourceBase


def _id(value: Any) -> str:
    return quote(str(value), safe="")


class StorefrontsResource(ResourceBase):
    """Inspect and manage creator storefronts."""

    def list(self) -> Any:
        return self._call("creators", "GET", "/storefront/owned")

    def create(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "creators", "POST", "/storefront", json=dict(payload), confirm=confirm
        )

    def check_slug(self, slug: str) -> Any:
        return self._call(
            "creators",
            "GET",
            "/storefront/slug-availability",
            params={"slug": slug},
        )

    def add_products(
        self,
        storefront_id: str,
        products: Sequence[Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "creators",
            "PATCH",
            f"/storefront/{_id(storefront_id)}/products",
            json={"products": list(products)},
            confirm=confirm,
        )

    def remove_products(
        self,
        storefront_id: str,
        product_ids: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "creators",
            "DELETE",
            f"/storefront/{_id(storefront_id)}/products",
            params={"productIds": ",".join(product_ids)},
            confirm=confirm,
        )

    def select_for_product(
        self,
        product_id: str,
        storefront_id: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "product",
            "PATCH",
            f"/products/{_id(product_id)}/settings/storefront",
            json={"storefrontId": storefront_id},
            confirm=confirm,
        )

    def update(
        self,
        storefront_id: str,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        body = dict(payload)
        body.setdefault("id", storefront_id)
        return self._write(
            "creators",
            "PUT",
            f"/storefront/{_id(storefront_id)}",
            json=body,
            confirm=confirm,
        )
