"""Subscription resources."""

from __future__ import annotations

import builtins
import uuid
from collections.abc import Iterator, Mapping, Sequence
from typing import Any
from urllib.parse import quote

from hubla_cli.pagination import collect_paginated
from hubla_cli.payloads import subscriptions_body
from hubla_cli.resources.base import ResourceBase


def _id(value: Any) -> str:
    return quote(str(value), safe="")


class SubscriptionsResource(ResourceBase):
    """Inspect subscriptions, renewals, trials, upgrades, and installments."""

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
        selection = self._offer_selection(offer_ids, has_selected_all)
        body = subscriptions_body(
            offer_ids=selection["offerIds"],
            has_selected_all=selection["hasSelectedAll"],
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
        return self._call("web", "POST", "/subscriptions/list", json=body)

    def iter_all(
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
    ) -> Iterator[Any]:
        """Yield every subscription matching the supplied filters."""
        result = collect_paginated(
            lambda current_page, current_page_size: self.list(
                offer_ids=offer_ids,
                has_selected_all=has_selected_all,
                start_date=start_date,
                end_date=end_date,
                statuses=statuses,
                search=search,
                date_range_by=date_range_by,
                plan_type=plan_type,
                is_free_trial_active=is_free_trial_active,
                page=current_page,
                page_size=current_page_size,
                order_by=order_by,
                order_direction=order_direction,
            ),
            page=page,
            page_size=page_size,
        )
        yield from result.items

    def all(
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
    ) -> builtins.list[Any]:
        """Return every subscription matching the supplied filters."""
        return list(
            self.iter_all(
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
        )

    filter = list

    def get(self, subscription_id: Any) -> Any:
        return self._call("web", "GET", f"/subscriptions/{_id(subscription_id)}")

    def invoices(
        self,
        subscription_id: Any,
        *,
        page: int = 1,
        page_size: int = 25,
    ) -> Any:
        return self._call(
            "web",
            "GET",
            f"/subscriptions/{_id(subscription_id)}/invoices",
            params={"page": page, "pageSize": page_size},
        )

    def deactivate(self, subscription_id: Any, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "PUT",
            f"/subscriptions/{_id(subscription_id)}/deactivate",
            confirm=confirm,
        )

    def add_daily_credits(
        self,
        subscription_id: Any,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        body = dict(payload)
        body.setdefault("id", subscription_id)
        return self._write(
            "web",
            "PUT",
            f"/subscriptions/{_id(subscription_id)}/add-daily-credits",
            json=body,
            confirm=confirm,
        )

    def _summary(
        self,
        path: str,
        *,
        start_date: str,
        end_date: str,
        offer_ids: Sequence[str] | None,
        has_selected_all: bool | None,
        period: str | None = None,
    ) -> Any:
        body = self._offer_selection(offer_ids, has_selected_all)
        body.update({"startDate": start_date, "endDate": end_date})
        if period is not None:
            body["period"] = period
        return self._call("web", "POST", path, json=body)

    def active_summary(
        self,
        *,
        start_date: str,
        end_date: str,
        period: str | None = None,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
    ) -> Any:
        return self._summary(
            "/receiver/summary/subscriptions/activated",
            start_date=start_date,
            end_date=end_date,
            period=period,
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
        )

    def canceled_summary(
        self,
        *,
        start_date: str,
        end_date: str,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
    ) -> Any:
        return self._summary(
            "/receiver/summary/subscriptions/canceled",
            start_date=start_date,
            end_date=end_date,
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
        )

    def inactive_summary(
        self,
        *,
        start_date: str,
        end_date: str,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
    ) -> Any:
        return self._summary(
            "/receiver/summary/subscriptions/inactivated",
            start_date=start_date,
            end_date=end_date,
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
        )

    def new_summary(
        self,
        *,
        start_date: str,
        end_date: str,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
    ) -> Any:
        return self._summary(
            "/receiver/summary/subscriptions/newers",
            start_date=start_date,
            end_date=end_date,
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
        )

    def export(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        statuses: Sequence[str] | None = None,
        plan_type: str | None = None,
        date_range_by: str | None = None,
        is_free_trial_active: bool | None = None,
        timezone: str = "-03:00",
        confirm: bool = False,
    ) -> bytes:
        body = self._offer_selection(offer_ids, has_selected_all)
        body.update(
            {
                "timezone": timezone,
                "filters": {
                    "status": list(statuses or []),
                    "planType": plan_type,
                    "startDate": start_date,
                    "endDate": end_date,
                    "dateRangeBy": date_range_by,
                    "isFreeTrialActive": is_free_trial_active,
                },
            }
        )
        return self._write(
            "web",
            "POST",
            "/subscriptions/export",
            json=body,
            response_type="bytes",
            confirm=confirm,
        )

    def enable_auto_renew(
        self,
        subscription_id: Any,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            "/pay/enable-subscription-auto-renew",
            json={"subscriptionId": subscription_id},
            confirm=confirm,
        )

    def disable_auto_renew(
        self,
        subscription_id: Any,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            "/pay/disable-subscription-auto-renew",
            json={"subscriptionId": subscription_id},
            confirm=confirm,
        )

    def pending_invoice(self, subscription_id: Any) -> Any:
        return self._call(
            "web",
            "GET",
            "/pay/get-pending-invoice-for-subscription",
            params={"subscriptionId": subscription_id},
        )

    def value(self, subscription_id: Any) -> Any:
        return self._call(
            "web",
            "GET",
            "/pay/get-subscription-value",
            params={"subscriptionId": subscription_id},
        )

    def upgrade_state(self, subscription_id: Any) -> Any:
        return self._call(
            "web",
            "GET",
            "/pay/upgrade-state",
            params={"subscriptionId": subscription_id},
        )

    def init_upgrade(self, subscription_id: Any, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "POST",
            "/pay/init-upgrade",
            json={"id": str(uuid.uuid4()), "subscriptionId": subscription_id},
            confirm=confirm,
        )

    def submit_upgrade(
        self,
        subscription_id: Any,
        selected_option_id: Any,
        installments: Any,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            "/pay/submit-upgrade",
            json={
                "id": str(uuid.uuid4()),
                "subscriptionId": subscription_id,
                "selectedOptionId": selected_option_id,
                "installments": installments,
            },
            confirm=confirm,
        )

    def cancel_upgrade(self, subscription_id: Any, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "POST",
            "/pay/cancel-upgrade",
            json={"subscriptionId": subscription_id},
            confirm=confirm,
        )

    def init_change_payment_method(
        self,
        subscription_id: Any,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            "/pay/init-change-payment-method",
            json={"subscriptionId": subscription_id},
            confirm=confirm,
        )

    def submit_change_payment_method(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "pay",
            "POST",
            "/change-subscription-funding",
            json=dict(payload),
            confirm=confirm,
        )

    def list_smart_installments(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        statuses: Sequence[str] | None = None,
        methods: Sequence[str] | None = None,
        types: Sequence[str] | None = None,
        search: str = "",
        date_range_by: str | None = None,
        page: int = 1,
        page_size: int = 25,
        order_by: str = "createdAt",
        order_direction: str = "DESC",
    ) -> Any:
        body = self._smart_installments_body(
            offer_ids=offer_ids,
            has_selected_all=has_selected_all,
            start_date=start_date,
            end_date=end_date,
            statuses=statuses,
            methods=methods,
            types=types,
            search=search,
            date_range_by=date_range_by,
            page=page,
            page_size=page_size,
            order_by=order_by,
            order_direction=order_direction,
        )
        return self._call("web", "POST", "/smart-installments/list", json=body)

    def smart_installments_summaries(self, **kwargs: Any) -> Any:
        return self._call(
            "web",
            "POST",
            "/smart-installments/summaries",
            json=self._smart_installments_body(**kwargs),
        )

    def all_installments(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        order_by: str = "createdAt",
        order_direction: str = "DESC",
        **filters: Any,
    ) -> Any:
        body = {
            "page": page,
            "pageSize": page_size,
            "orderBy": order_by,
            "orderDirection": order_direction,
        }
        body.update({key: value for key, value in filters.items() if value})
        return self._call(
            "web",
            "POST",
            "/smart-installments/all-installments",
            json=body,
        )

    def cancel_smart_installment(
        self,
        installment_id: Any,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "PUT",
            f"/smart-installments/{_id(installment_id)}/cancel",
            confirm=confirm,
        )

    def _smart_installments_body(self, **kwargs: Any) -> dict[str, Any]:
        body = self._offer_selection(
            kwargs.pop("offer_ids", None),
            kwargs.pop("has_selected_all", None),
        )
        body.update(
            {
                "filters": {
                    "search": kwargs.pop("search", ""),
                    "startDate": kwargs.pop("start_date", None),
                    "endDate": kwargs.pop("end_date", None),
                    "dateRangeBy": kwargs.pop("date_range_by", None),
                    "status": list(kwargs.pop("statuses", []) or []),
                    "paymentMethods": list(kwargs.pop("methods", []) or []),
                    "types": list(kwargs.pop("types", []) or []),
                },
                "page": kwargs.pop("page", 1),
                "pageSize": kwargs.pop("page_size", 25),
                "orderBy": kwargs.pop("order_by", "createdAt"),
                "orderDirection": kwargs.pop("order_direction", "DESC"),
            }
        )
        return body

    def free_trials(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        search: str = "",
        start_date: str | None = None,
        end_date: str | None = None,
        date_range_by: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> Any:
        body = self._offer_selection(offer_ids, has_selected_all)
        body.update(
            {
                "filters": {
                    "isFreeTrialActive": True,
                    "search": search,
                    "startDate": start_date,
                    "endDate": end_date,
                    "dateRangeBy": date_range_by,
                },
                "page": page,
                "pageSize": page_size,
                "orderBy": "createdAt",
                "orderDirection": "DESC",
            }
        )
        return self._call("web", "POST", "/subscriptions/list", json=body)

    def free_trial_summaries(
        self,
        *,
        offer_ids: Sequence[str] | None = None,
        has_selected_all: bool | None = None,
        search: str = "",
        start_date: str | None = None,
        end_date: str | None = None,
        date_range_by: str | None = None,
    ) -> Any:
        body = self._offer_selection(offer_ids, has_selected_all)
        body["filters"] = {
            "search": search,
            "dateStart": start_date,
            "dateEnd": end_date,
            "dateRangeBy": date_range_by,
        }
        return self._call("web", "POST", "/free-trial/summaries", json=body)
