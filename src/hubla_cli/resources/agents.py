"""Hubla Agents contracts observed in the portal's CRM and conversation BFFs.

Read-oriented POSTs are deliberately separate from guarded mutations. Response DTOs
are returned unchanged because the portal's internal contracts are not stable.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any
from urllib.parse import quote

from hubla_cli.resources.base import ResourceBase


def _id(value: str) -> str:
    if not value or not value.strip():
        raise ValueError("informe um identificador não vazio")
    return quote(value, safe="")


def _page(page: int, page_size: int, **filters: Any) -> dict[str, Any]:
    if page < 1 or not 1 <= page_size <= 500:
        raise ValueError("page deve ser positivo e page_size deve estar entre 1 e 500")
    return {"page": page, "pageSize": page_size, **filters}


class AgentsWorkflowsResource(ResourceBase):
    """List and manage Hubla Agents workflows (Meus agentes)."""

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        workflow_type: str | None = None,
        product_id: str | None = None,
    ) -> Any:
        params = _page(page, page_size, search=search, type=workflow_type)
        if product_id:
            params["productId"] = product_id
        return self._call("crm", "GET", "/workflows", params=params)

    def get(self, workflow_id: str) -> Any:
        return self._call("crm", "GET", f"/workflows/{_id(workflow_id)}")

    def products(self, workflow_type: str) -> Any:
        """List product IDs configured for a workflow type."""
        return self._call("crm", "GET", f"/workflows/products/{_id(workflow_type)}")

    def create(self, payload: Mapping[str, Any], *, confirm: bool = False) -> Any:
        return self._write(
            "crm", "POST", "/workflows", json=dict(payload), confirm=confirm
        )

    def update(
        self, workflow_id: str, payload: Mapping[str, Any], *, confirm: bool = False
    ) -> Any:
        return self._write(
            "crm",
            "PUT",
            f"/workflows/{_id(workflow_id)}",
            json=dict(payload),
            confirm=confirm,
        )

    def publish(self, workflow_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "crm",
            "PATCH",
            f"/workflows/{_id(workflow_id)}/publish",
            confirm=confirm,
        )

    def toggle_active(
        self, workflow_id: str, *, reason: str | None = None, confirm: bool = False
    ) -> Any:
        body = {"reason": reason} if reason else None
        return self._write(
            "crm",
            "PATCH",
            f"/workflows/{_id(workflow_id)}/toggle-active",
            json=body,
            confirm=confirm,
        )

    def delete(
        self, workflow_id: str, *, reason: str | None = None, confirm: bool = False
    ) -> Any:
        body = {"reason": reason} if reason else None
        return self._write(
            "crm",
            "DELETE",
            f"/workflows/{_id(workflow_id)}",
            json=body,
            confirm=confirm,
        )

    def sandbox(
        self,
        workflow_id: str,
        recipient: str,
        parameters: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        """Send a test workflow message; requires confirmation."""
        return self._write(
            "crm",
            "POST",
            f"/workflows/{_id(workflow_id)}/sandbox",
            json={"recipient": recipient, "parameters": dict(parameters)},
            confirm=confirm,
        )


class AgentsConversationsResource(ResourceBase):
    """Read conversations and explicitly manage messages and assignments."""

    def list(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        channel_source_id: str | None = None,
        channel_source_types: Sequence[str] | None = None,
        role: str | None = None,
        statuses: Sequence[str] | None = None,
        read_status: str | None = None,
        products: Sequence[str] | None = None,
    ) -> Any:
        body = _page(
            page,
            page_size,
            search=search,
            channelSourceId=channel_source_id,
            channelSourceTypes=list(channel_source_types)
            if channel_source_types
            else None,
            role=role,
            statuses=list(statuses) if statuses else None,
            readStatus=read_status,
            products=list(products) if products else None,
        )
        return self._call("conversations", "POST", "/conversations/list", json=body)

    def get(self, conversation_id: str) -> Any:
        return self._call(
            "conversations", "GET", f"/conversations/{_id(conversation_id)}"
        )

    def messages(
        self, conversation_id: str, *, params: Mapping[str, Any] | None = None
    ) -> Any:
        return self._call(
            "conversations",
            "GET",
            f"/conversations/{_id(conversation_id)}/messages",
            params=params,
        )

    def attendants(self, *, page: int = 1, page_size: int = 20) -> Any:
        return self._call(
            "conversations",
            "GET",
            "/conversations/attendants",
            params=_page(page, page_size),
        )

    def suggestions(self, conversation_id: str, *, confirm: bool = False) -> Any:
        """Generate suggestions remotely; may consume credits or modify state."""
        return self._write(
            "conversations",
            "POST",
            f"/conversations/{_id(conversation_id)}/suggestions",
            confirm=confirm,
        )

    def send_message(self, payload: Mapping[str, Any], *, confirm: bool = False) -> Any:
        return self._write(
            "conversations",
            "POST",
            "/conversations/messages",
            json=dict(payload),
            confirm=confirm,
        )

    def retry_message(
        self, conversation_id: str, message_id: str, *, confirm: bool = False
    ) -> Any:
        return self._write(
            "conversations",
            "POST",
            f"/conversations/{_id(conversation_id)}/messages/{_id(message_id)}/retry",
            confirm=confirm,
        )

    def edit_message(
        self,
        conversation_id: str,
        message_id: str,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "conversations",
            "PATCH",
            f"/conversations/{_id(conversation_id)}/messages/{_id(message_id)}",
            json=dict(payload),
            confirm=confirm,
        )

    def _action(
        self,
        conversation_id: str,
        action: str,
        *,
        payload: Mapping[str, Any] | None = None,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "conversations",
            "POST",
            f"/conversations/{_id(conversation_id)}/{action}",
            json=dict(payload) if payload else None,
            confirm=confirm,
        )

    def archive(self, conversation_id: str, *, confirm: bool = False) -> Any:
        return self._action(conversation_id, "archive", confirm=confirm)

    def unarchive(self, conversation_id: str, *, confirm: bool = False) -> Any:
        return self._action(conversation_id, "unarchive", confirm=confirm)

    def mark_read(
        self, conversation_id: str, message_id: str, *, confirm: bool = False
    ) -> Any:
        return self._action(
            conversation_id,
            "read",
            payload={"messageId": message_id},
            confirm=confirm,
        )

    def take_over(self, conversation_id: str, *, confirm: bool = False) -> Any:
        return self._action(conversation_id, "take-over", confirm=confirm)

    def transfer(
        self, conversation_id: str, assigned_id: str, *, confirm: bool = False
    ) -> Any:
        return self._action(
            conversation_id,
            "transfer",
            payload={"assignedId": assigned_id},
            confirm=confirm,
        )


class AgentsBrainsResource(ResourceBase):
    """Manage Second Brain records, knowledge sources and plugins."""

    def list(self, *, page: int = 1, page_size: int = 25, search: str = "") -> Any:
        return self._call(
            "crm", "GET", "/brains", params=_page(page, page_size, search=search)
        )

    def get(self, brain_id: str) -> Any:
        return self._call("crm", "GET", f"/brains/{_id(brain_id)}")

    def external_sources(
        self, *, page: int = 1, page_size: int = 25, source_type: str | None = None
    ) -> Any:
        params = _page(page, page_size)
        if source_type:
            params["type"] = source_type
        return self._call("crm", "GET", "/brains/sources/external", params=params)

    def plugins(self, brain_id: str) -> Any:
        return self._call("crm", "GET", f"/brains/{_id(brain_id)}/plugins")

    def create(self, payload: Mapping[str, Any], *, confirm: bool = False) -> Any:
        return self._write(
            "crm", "POST", "/brains", json=dict(payload), confirm=confirm
        )

    def update(
        self, brain_id: str, payload: Mapping[str, Any], *, confirm: bool = False
    ) -> Any:
        return self._write(
            "crm",
            "PUT",
            f"/brains/{_id(brain_id)}",
            json=dict(payload),
            confirm=confirm,
        )

    def publish(
        self, brain_id: str, *, force: bool = False, confirm: bool = False
    ) -> Any:
        return self._write(
            "crm",
            "POST",
            f"/brains/{_id(brain_id)}/publish",
            json={"force": force},
            confirm=confirm,
        )

    def delete(self, brain_id: str, *, confirm: bool = False) -> Any:
        return self._write("crm", "DELETE", f"/brains/{_id(brain_id)}", confirm=confirm)

    def add_source(
        self,
        brain_id: str,
        kind: str,
        source: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "crm",
            "POST",
            f"/brains/{_id(brain_id)}/sources",
            json={"kind": kind, "source": dict(source)},
            confirm=confirm,
        )

    def add_sources(
        self,
        brain_id: str,
        sources: Sequence[Mapping[str, Any]],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "crm",
            "POST",
            f"/brains/{_id(brain_id)}/sources/batch",
            json={"sources": [dict(source) for source in sources]},
            confirm=confirm,
        )

    def remove_source(
        self, brain_id: str, source_id: str, kind: str, *, confirm: bool = False
    ) -> Any:
        return self._write(
            "crm",
            "DELETE",
            f"/brains/{_id(brain_id)}/sources/{_id(source_id)}",
            params={"kind": kind},
            confirm=confirm,
        )

    def retry_source(
        self, brain_id: str, source_id: str, kind: str, *, confirm: bool = False
    ) -> Any:
        return self._write(
            "crm",
            "POST",
            f"/brains/{_id(brain_id)}/sources/{_id(source_id)}/retry",
            params={"kind": kind},
            confirm=confirm,
        )

    def set_plugin(
        self, brain_id: str, app_type: str, enabled: bool, *, confirm: bool = False
    ) -> Any:
        state = "enable" if enabled else "disable"
        return self._write(
            "crm",
            "POST",
            f"/brains/{_id(brain_id)}/plugins/{state}",
            json={"appType": app_type},
            confirm=confirm,
        )


class AgentsPersonasResource(ResourceBase):
    """List and manage agent personas."""

    def list(self, *, page: int = 1, page_size: int = 25, search: str = "") -> Any:
        return self._call(
            "crm",
            "GET",
            "/personas/tenant",
            params=_page(page, page_size, search=search),
        )

    def create(self, payload: Mapping[str, Any], *, confirm: bool = False) -> Any:
        return self._write(
            "crm", "POST", "/personas", json=dict(payload), confirm=confirm
        )

    def update(
        self, persona_id: str, payload: Mapping[str, Any], *, confirm: bool = False
    ) -> Any:
        return self._write(
            "crm",
            "PUT",
            f"/personas/{_id(persona_id)}",
            json=dict(payload),
            confirm=confirm,
        )

    def delete(self, persona_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "crm", "DELETE", f"/personas/{_id(persona_id)}", confirm=confirm
        )


class AgentsKnowledgeResource(ResourceBase):
    """List and manage CRM knowledge bases (distinct from brain sources)."""

    def list(self, payload: Mapping[str, Any]) -> Any:
        """Run the portal's read-oriented POST /knowledge/list."""
        return self._call("crm", "POST", "/knowledge/list", json=dict(payload))

    def get(self, knowledge_id: str) -> Any:
        return self._call("crm", "GET", f"/knowledge/{_id(knowledge_id)}")

    def variables(self, knowledge_id: str) -> Any:
        return self._call(
            "crm", "GET", f"/knowledge-variables/knowledge/{_id(knowledge_id)}"
        )

    def template(self, template_id: str) -> Any:
        return self._call("crm", "GET", f"/knowledge-template/{_id(template_id)}")

    def create(self, payload: Mapping[str, Any], *, confirm: bool = False) -> Any:
        return self._write(
            "crm", "POST", "/knowledge", json=dict(payload), confirm=confirm
        )

    def update(
        self, knowledge_id: str, payload: Mapping[str, Any], *, confirm: bool = False
    ) -> Any:
        return self._write(
            "crm",
            "PUT",
            f"/knowledge/{_id(knowledge_id)}",
            json=dict(payload),
            confirm=confirm,
        )

    def delete(self, knowledge_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "crm", "DELETE", f"/knowledge/{_id(knowledge_id)}", confirm=confirm
        )


class AgentsChannelsResource(ResourceBase):
    """List and manage the channels and templates connected to agents."""

    def list(self, *, page: int = 1, page_size: int = 25, search: str = "") -> Any:
        return self._call(
            "crm", "GET", "/channels", params=_page(page, page_size, search=search)
        )

    def get(self, channel_id: str) -> Any:
        return self._call("crm", "GET", f"/channels/{_id(channel_id)}")

    def templates(self, channel_id: str, *, page: int = 1, page_size: int = 25) -> Any:
        return self._call(
            "crm",
            "GET",
            f"/channels/{_id(channel_id)}/templates",
            params=_page(page, page_size),
        )

    def create(self, payload: Mapping[str, Any], *, confirm: bool = False) -> Any:
        return self._write(
            "crm", "POST", "/channels", json=dict(payload), confirm=confirm
        )

    def delete(self, channel_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "crm", "DELETE", f"/channels/{_id(channel_id)}", confirm=confirm
        )

    def create_template(
        self, channel_id: str, payload: Mapping[str, Any], *, confirm: bool = False
    ) -> Any:
        return self._write(
            "crm",
            "POST",
            f"/channels/{_id(channel_id)}/templates",
            json=dict(payload),
            confirm=confirm,
        )

    def update_template(
        self,
        channel_id: str,
        template_id: str,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "crm",
            "PATCH",
            f"/channels/{_id(channel_id)}/templates/{_id(template_id)}",
            json=dict(payload),
            confirm=confirm,
        )

    def delete_template(
        self, channel_id: str, template_id: str, *, confirm: bool = False
    ) -> Any:
        return self._write(
            "crm",
            "DELETE",
            f"/channels/{_id(channel_id)}/templates/{_id(template_id)}",
            confirm=confirm,
        )

    def sandbox_template(
        self,
        channel_id: str,
        template_id: str,
        recipient: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "crm",
            "POST",
            f"/channels/{_id(channel_id)}/templates/{_id(template_id)}/sandbox",
            json={"to": recipient},
            confirm=confirm,
        )


class AgentsInsightsResource(ResourceBase):
    """Inspect agent opportunities, execution counts and dashboard metrics."""

    _OPPORTUNITIES_QUERY = "05bcd3c3-0e58-47b5-b0fe-9194cce6c91e"
    _QUERIES = {
        "agents_metrics_daily": "7c9e4b2a-1d3f-4a8c-9b6e-2f5a8c1d7e30",
        "agents_breakdown": "b3f8d6c1-4e2a-4d9b-8c7f-1a6e3b2d5c40",
        "agents_hours_daily": "966df7ee-b971-483d-a838-dc61beb54732",
        "off_hours_coverage_daily": "8e3b1e4a-5d6f-4c2b-9a8e-7f6d5c4b3a21",
        "conversion_rate_benchmark_daily": "73e61a94-2a8e-48b4-b6c0-5baafb0467c6",
        "engagement_metrics_daily": "d4f8b8fc-1aa1-4f9b-9d1f-0f2f2dd4c7a1",
        "engagement_breakdown": "6f5b19dd-72a0-4c2e-8ac3-918ed67284a1",
        "opportunities": _OPPORTUNITIES_QUERY,
    }

    def query(self, metric: str, payload: Mapping[str, Any]) -> Any:
        """Run a named read-only dashboard query with the portal's DTO."""
        query_id = self._QUERIES.get(metric)
        if query_id is None:
            raise ValueError("métrica de agentes desconhecida; consulte schema")
        return self._call("data", "POST", f"/query/{query_id}", json=dict(payload))

    def opportunities(self, *, timezone: str = "America/Sao_Paulo") -> Any:
        return self.query(
            "opportunities", {"order": [], "offset": 0, "timezone": timezone}
        )

    def home(
        self, *, start_date: str, end_date: str, timezone: str = "America/Sao_Paulo"
    ) -> dict[str, Any]:
        """Read the Agents home metrics and opportunities in their raw currencies."""
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        if end < start:
            raise ValueError("end_date deve ser igual ou posterior a start_date")
        date_filter = {
            "$gte": f"{start.isoformat()} 00:00:00",
            "$lte": f"{end.isoformat()} 23:59:59",
        }
        base = {
            "where": {"date": date_filter},
            "order": [],
            "offset": 0,
            "timezone": timezone,
        }
        return {
            "period": {"startDate": start_date, "endDate": end_date},
            "agentsMetricsDaily": self.query(
                "agents_metrics_daily", {"dateGrouping": "day", **base}
            ),
            "agentsBreakdown": self.query("agents_breakdown", base),
            "opportunities": self.opportunities(timezone=timezone),
        }

    def executions(self, payload: Mapping[str, Any]) -> Any:
        return self._call(
            "crm", "POST", "/workflows/executions/list", json=dict(payload)
        )

    def execution_summary(self, metric: str, payload: Mapping[str, Any]) -> Any:
        if metric not in {"errors", "success-rate", "total"}:
            raise ValueError("metric deve ser errors, success-rate ou total")
        return self._call(
            "crm",
            "POST",
            f"/workflows/executions/summary/{metric}",
            json=dict(payload),
        )
