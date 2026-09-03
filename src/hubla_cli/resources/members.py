"""Member access and group resources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote

from hubla_cli.resources.base import ResourceBase


def _id(value: Any) -> str:
    return quote(str(value), safe="")


class MembersResource(ResourceBase):
    """Inspect members and manage account-authorized access changes."""

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
        params = {
            "page": page,
            "pageSize": page_size,
            "productId": product_id,
            "types": list(types or []),
            "search": search,
            "cohortIds": list(cohort_ids or []),
            "orderBy": "createdAt",
            "orderDirection": "DESC",
            "includeItemsQuantityTotal": include_items_quantity_total,
        }
        return self._call("members_area", "GET", "/members/actives/list", params=params)

    list_active = active

    def deactivated(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        product_id: str | None = None,
        search: str = "",
    ) -> Any:
        params = {
            "page": page,
            "pageSize": page_size,
            "productId": product_id,
            "search": search,
            "orderBy": "nextDueAt",
            "orderDirection": "DESC",
        }
        return self._call(
            "members_area", "GET", "/members/deactivates/list", params=params
        )

    list_deactivated = deactivated

    def pending_invites(self) -> Any:
        return self._call("members_area", "GET", "/invites/list/pending")

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
        body: dict[str, Any] = {
            "productId": product_id,
            "receiverEmails": list(emails),
            "lifetime": lifetime,
        }
        if days is not None and not lifetime:
            body["days"] = days
        if offer_id is not None:
            body["offerId"] = offer_id
        if quantity is not None:
            body["quantity"] = quantity
        return self._write(
            "members_area",
            "POST",
            "/members/create-invites-free-subscription",
            json=body,
            confirm=confirm,
        )

    add = create_free_subscription

    def remove_free_subscription(
        self,
        product_id: str,
        user_id: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "members_area",
            "PUT",
            "/members/remove-free-subscription",
            json={"productId": product_id, "userId": user_id},
            confirm=confirm,
        )

    remove = remove_free_subscription

    def transform_free_members(
        self,
        product_id: str,
        user_ids: Sequence[str],
        *,
        days: int | None,
        lifetime: bool,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "members_area",
            "POST",
            "/members/free-subscription-old-members",
            json={
                "productId": product_id,
                "userIds": list(user_ids),
                "days": days,
                "lifetime": lifetime,
            },
            confirm=confirm,
        )

    def change_cohorts_by_product(
        self,
        product_id: str,
        member_ids: Sequence[str],
        cohorts: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "access",
            "POST",
            "/access/change-member-cohorts-by-product",
            json={
                "productId": product_id,
                "memberIds": list(member_ids),
                "cohorts": list(cohorts),
            },
            confirm=confirm,
        )

    def change_cohorts(
        self,
        members: Sequence[Mapping[str, Any]],
        new_cohorts: Sequence[str],
        *,
        confirm: bool = False,
    ) -> Any:
        body = {
            "members": [
                {
                    "memberId": member.get("memberId", member.get("id")),
                    "currentCohorts": list(
                        member.get("currentCohorts", member.get("cohortIds", []))
                    ),
                    "newCohorts": list(new_cohorts),
                }
                for member in members
            ]
        }
        return self._write(
            "access",
            "POST",
            "/access/change-members-cohorts",
            json=body,
            confirm=confirm,
        )

    def cancel_invite(self, invite_id: str, *, confirm: bool = False) -> Any:
        return self._write(
            "members_area",
            "PUT",
            f"/invites/{_id(invite_id)}/cancel",
            confirm=confirm,
        )

    def export_active(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        product_id: str | None = None,
        offer_id: str | None = None,
        types: Sequence[str] | None = None,
        search: str = "",
        timezone: str = "-03:00",
        confirm: bool = False,
    ) -> bytes:
        params = {
            "page": page,
            "pageSize": page_size,
            "productId": product_id,
            "offerId": offer_id,
            "types": list(types or []),
            "search": search,
            "timezone": timezone,
            "orderBy": "createdAt",
            "orderDirection": "DESC",
        }
        return self._write(
            "members_area",
            "GET",
            "/members/actives/export",
            params=params,
            response_type="bytes",
            confirm=confirm,
        )

    def export_deactivated(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        product_id: str | None = None,
        offer_id: str | None = None,
        search: str = "",
        timezone: str = "-03:00",
        confirm: bool = False,
    ) -> bytes:
        params = {
            "page": page,
            "pageSize": page_size,
            "productId": product_id,
            "offerId": offer_id,
            "search": search,
            "timezone": timezone,
            "orderBy": "createdAt",
            "orderDirection": "DESC",
        }
        return self._write(
            "members_area",
            "GET",
            "/members/deactivates/export",
            params=params,
            response_type="bytes",
            confirm=confirm,
        )

    def send_access_link(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            "/members/send-access-link",
            json=dict(payload),
            confirm=confirm,
        )

    def recover_password(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            "/auth/recover-member-password",
            json=dict(payload),
            confirm=confirm,
        )

    def accesses_by_product(self, product_id: str) -> Any:
        return self._call(
            "members_area",
            "POST",
            "/members/get-accesses-by-product-id",
            json={"productId": product_id},
        )

    def edit_access(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "access",
            "PUT",
            "/access/member-edit-access",
            json=dict(payload),
            confirm=confirm,
        )

    def send_ticket(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "access",
            "POST",
            "/access/send-ticket",
            json=dict(payload),
            confirm=confirm,
        )

    def transfer_access(
        self,
        to_user_email: str,
        access_code: str,
        *,
        notes: str | None = None,
        confirm: bool = False,
    ) -> Any:
        body: dict[str, Any] = {
            "toUserEmail": to_user_email,
            "accessCode": access_code,
        }
        if notes is not None:
            body["notes"] = notes
        return self._write(
            "access",
            "POST",
            "/access/transfer-accesses",
            json=body,
            confirm=confirm,
        )

    def offers_and_cohorts(self, product_id: str) -> Any:
        return self._call(
            "product",
            "GET",
            f"/products/{_id(product_id)}/offers/offers-and-cohorts",
        )

    def ticket_counters(self, product_id: str) -> Any:
        return self._call(
            "product", "GET", f"/products/{_id(product_id)}/ticket-counters"
        )


class GroupsResource(ResourceBase):
    """Inspect Hubla groups and manage their resources and whitelist."""

    def group(self, group_id: str) -> Any:
        return self._call(
            "functions", "POST", "/group/get/pt", json={"data": {"id": group_id}}
        )

    def whitelist(self, group_id: str) -> Any:
        return self._call(
            "functions",
            "POST",
            "/group/getWhitelist/pt",
            json={"data": {"groupId": group_id}},
        )

    def group_resource(self, resource_id: str) -> Any:
        return self._call(
            "functions",
            "POST",
            "/groupResource/get/pt",
            json={"data": {"id": resource_id}},
        )

    def free_members(self, payload: Mapping[str, Any]) -> Any:
        return self._call(
            "functions",
            "POST",
            "/groupWhitelist/listMembersByGroupResourceId/pt",
            json={"data": dict(payload)},
        )

    def generate_whitelist_link(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "functions",
            "POST",
            "/groupWhitelist/generateLink/pt",
            json={"data": dict(payload)},
            confirm=confirm,
        )

    def remove_whitelist_member(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "functions",
            "POST",
            "/groupWhitelist/remove/pt",
            json={"data": dict(payload)},
            confirm=confirm,
        )

    def add_resource(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "functions",
            "POST",
            "/group/addResource/pt",
            json={"data": dict(payload)},
            confirm=confirm,
        )
