"""External integration resources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

from hubla_cli.resources.base import ResourceBase


def _id(value: Any) -> str:
    return quote(str(value), safe="")


class IntegrationsResource(ResourceBase):
    """Inspect and manage integrations, rules, and event retries."""

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        provider: str | None = None,
    ) -> Any:
        if provider:
            return self.provider(provider)
        return self.overview(page=page, page_size=page_size)

    def get(self, integration_id: str) -> Any:
        return self._call("web", "GET", f"/integrations/{_id(integration_id)}")

    def create(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web", "POST", "/integrations", json=dict(payload), confirm=confirm
        )

    def delete(self, integration_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "DELETE",
            f"/integrations/{_id(integration_id)}",
            confirm=confirm,
        )

    def overview(self, page: int = 1, page_size: int = 25) -> Any:
        return self._call(
            "web",
            "GET",
            "/integrations/overview",
            params={"page": page, "pageSize": page_size},
        )

    def provider(self, provider: str) -> Any:
        return self._call("web", "GET", f"/integrations/provider/{_id(provider)}")

    def history(self, integration_id: str, payload: Mapping[str, Any]) -> Any:
        return self._call(
            "web",
            "POST",
            f"/integrations/{_id(integration_id)}/events/list",
            json=dict(payload),
        )

    def rules(
        self,
        integration_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
    ) -> Any:
        return self._call(
            "web",
            "GET",
            f"/integrations/{_id(integration_id)}/rules",
            params={"page": page, "pageSize": page_size},
        )

    def get_rule(self, integration_id: str, rule_id: str) -> Any:
        return self._call(
            "web",
            "GET",
            f"/integrations/{_id(integration_id)}/rules/{_id(rule_id)}",
        )

    def create_rule(
        self,
        integration_id: str,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            f"/integrations/{_id(integration_id)}/rules",
            json=dict(payload),
            confirm=confirm,
        )

    def update_rule(
        self,
        integration_id: str,
        rule_id: str,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "PUT",
            f"/integrations/{_id(integration_id)}/rules/{_id(rule_id)}",
            json=dict(payload),
            confirm=confirm,
        )

    def delete_rule(
        self,
        integration_id: str,
        rule_id: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "DELETE",
            f"/integrations/{_id(integration_id)}/rules/{_id(rule_id)}",
            confirm=confirm,
        )

    def provider_lists(self, integration_id: str) -> Any:
        return self._call(
            "web",
            "GET",
            f"/integrations/{_id(integration_id)}/provider/lists",
        )

    def provider_tags(self, integration_id: str) -> Any:
        return self._call(
            "web",
            "GET",
            f"/integrations/{_id(integration_id)}/provider/tags",
        )

    def retry_events(
        self,
        integration_id: str,
        event_ids: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            f"/integrations/{_id(integration_id)}/events/retry-batch",
            json={"ids": list(event_ids)},
            confirm=confirm,
        )

    def get_event(self, integration_id: str, event_id: str) -> Any:
        return self._call(
            "web",
            "GET",
            f"/integrations/{_id(integration_id)}/events/{_id(event_id)}",
        )
