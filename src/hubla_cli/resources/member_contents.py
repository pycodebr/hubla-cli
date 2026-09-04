"""Members-area content resources."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from hubla_cli.pagination import collect_paginated
from hubla_cli.resources.base import ResourceBase


class MembersAreaContentsResource(ResourceBase):
    """Inspect sections exposed in a product's members area."""

    def list_sections(
        self,
        product_id: str,
        page: int = 1,
        page_size: int = 999,
        post_page_size: int = 999,
    ) -> Any:
        """List one page of members-area sections for a product."""
        return self._call(
            "members_area",
            "GET",
            "/hub/sections/v2",
            params={
                "productId": product_id,
                "page": page,
                "pageSize": page_size,
                "postPageSize": post_page_size,
            },
        )

    def iter_sections(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 999,
        post_page_size: int = 999,
    ) -> Iterator[Any]:
        """Yield every members-area section while reconciling pagination."""
        result = collect_paginated(
            lambda current_page, current_page_size: self.list_sections(
                product_id,
                page=current_page,
                page_size=current_page_size,
                post_page_size=post_page_size,
            ),
            page=page,
            page_size=page_size,
        )
        yield from result.items

    def all_sections(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 999,
        post_page_size: int = 999,
    ) -> list[Any]:
        """Return every members-area section for a product."""
        return list(
            self.iter_sections(
                product_id,
                page=page,
                page_size=page_size,
                post_page_size=post_page_size,
            )
        )

    def cohort_snapshot(
        self,
        product_id: str,
        cohort_id: str,
        *,
        page_size: int = 999,
        post_page_size: int = 999,
    ) -> Mapping[str, Any]:
        """Return a normalized snapshot of sections associated with one cohort."""
        sections = self.all_sections(
            product_id,
            page_size=page_size,
            post_page_size=post_page_size,
        )
        matching: list[Mapping[str, Any]] = []
        for section in sections:
            if not isinstance(section, Mapping):
                continue
            cohort_ids = _normalise_ids(
                section.get(
                    "cohortIds",
                    section.get("cohort_ids", section.get("cohorts", [])),
                )
            )
            if str(cohort_id) in cohort_ids:
                matching.append(section)
        section_ids: list[str] = []
        for section in matching:
            for key in ("id", "sectionId", "section_id"):
                value = section.get(key)
                if value is not None:
                    section_ids.append(str(value))
                    break
        return {
            "product_id": str(product_id),
            "cohort_id": str(cohort_id),
            "section_ids": sorted(set(section_ids)),
            "sections": matching,
        }


# Short compatibility alias for the unreleased development API.
MemberContentsResource = MembersAreaContentsResource


def _normalise_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        for key in ("id", "cohortId", "cohort_id", "externalId", "external_id"):
            if key in value and value[key] is not None:
                return _normalise_ids(value[key])
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        result: list[str] = []
        for item in value:
            result.extend(_normalise_ids(item))
        return list(dict.fromkeys(result))
    return [str(value)]
