"""Member access and group resources."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Any
from urllib.parse import quote

from hubla_cli.errors import (
    AmbiguousMemberError,
    CohortReadbackError,
    MemberFilterIgnoredError,
    MemberNotFoundError,
)
from hubla_cli.pagination import collect_paginated
from hubla_cli.resources.base import ResourceBase
from hubla_cli.resources.member_contents import MembersAreaContentsResource

__all__ = ["MembersAreaContentsResource", "MembersResource", "GroupsResource"]


def _id(value: Any) -> str:
    return quote(str(value), safe="")


def _normalise_ids(value: Any) -> list[str]:
    """Normalize scalar, mapping, and sequence IDs without splitting strings."""
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


def _member_cohort_ids(member: Mapping[str, Any]) -> list[str]:
    for key in (
        "currentCohorts",
        "current_cohorts",
        "cohortIds",
        "cohort_ids",
        "cohorts",
    ):
        if key in member:
            return _normalise_ids(member[key])
    for key in ("access", "membership", "member"):
        nested = member.get(key)
        if isinstance(nested, Mapping):
            nested_ids = _member_cohort_ids(nested)
            if nested_ids:
                return nested_ids
    return []


def _member_email(member: Mapping[str, Any]) -> str | None:
    for key in (
        "email",
        "userEmail",
        "user_email",
        "memberEmail",
        "member_email",
        "emailAddress",
        "email_address",
    ):
        value = member.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().casefold()
    for key in ("user", "member", "profile", "account"):
        nested = member.get(key)
        if isinstance(nested, Mapping):
            email = _member_email(nested)
            if email is not None:
                return email
    return None


def _member_product_id(member: Mapping[str, Any]) -> str | None:
    for key in ("productId", "product_id"):
        value = member.get(key)
        if value is not None:
            return str(value)
    for key in ("access", "membership", "member"):
        nested = member.get(key)
        if isinstance(nested, Mapping):
            product_id = _member_product_id(nested)
            if product_id is not None:
                return product_id
    return None


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
        """Yield all active members for a product before local cohort filtering.

        Hubla's cohort filter is intentionally cleared on every provider call.
        The full product result and its declared total are reconciled first, so
        a provider-side filter bug cannot hide members from the caller.
        """
        result = collect_paginated(
            lambda current_page, current_page_size: self.active(
                page=current_page,
                page_size=current_page_size,
                product_id=product_id,
                types=types,
                search=search,
                cohort_ids=(),
                include_items_quantity_total=True,
            ),
            page=page,
            page_size=page_size,
            require_total=True,
        )
        requested_cohorts = set(_normalise_ids(cohort_ids))
        if not requested_cohorts:
            yield from result.items
            return
        for member in result.items:
            if isinstance(member, Mapping) and requested_cohorts.intersection(
                _member_cohort_ids(member)
            ):
                yield member

    def all(
        self,
        product_id: str,
        *,
        page: int = 1,
        page_size: int = 25,
        types: Sequence[str] | None = None,
        search: str = "",
        cohort_ids: Sequence[str] | None = None,
    ) -> list[Any]:
        """Return all active members for a product before local cohort filtering."""
        return list(
            self.iter_all(
                product_id,
                page=page,
                page_size=page_size,
                types=types,
                search=search,
                cohort_ids=cohort_ids,
            )
        )

    def get_current_cohort_ids(
        self,
        product_id: str,
        email: str,
        *,
        page_size: int = 25,
        types: Sequence[str] | None = None,
    ) -> list[str]:
        """Read current cohort IDs for exactly one active member by e-mail."""
        member = self.find_exact_by_email(
            product_id,
            email,
            page_size=page_size,
            types=types,
        )
        return _member_cohort_ids(member)

    def find_exact_by_email(
        self,
        product_id: str,
        email: str,
        *,
        page_size: int = 25,
        types: Sequence[str] | None = None,
    ) -> Mapping[str, Any]:
        """Return exactly one product member matching an e-mail address."""
        expected_email = email.strip().casefold()
        members = self.all(
            product_id,
            page_size=page_size,
            types=types,
            search=email,
        )
        for member in members:
            if not isinstance(member, Mapping):
                continue
            observed_product_id = _member_product_id(member)
            if observed_product_id is not None and observed_product_id != str(
                product_id
            ):
                raise MemberFilterIgnoredError(
                    "a Hubla retornou membro fora do produto solicitado"
                )
        matches = [
            member
            for member in members
            if isinstance(member, Mapping) and _member_email(member) == expected_email
        ]
        if not matches:
            raise MemberNotFoundError(
                "nenhum membro ativo corresponde ao produto e e-mail informados"
            )
        if len(matches) > 1:
            raise AmbiguousMemberError(
                "mais de um membro ativo corresponde ao produto e e-mail informados"
            )
        return matches[0]

    def change_cohorts_with_readback(
        self,
        *,
        product_id: str,
        member: Mapping[str, Any],
        email: str,
        new_cohorts: Sequence[str],
        confirm: bool = False,
    ) -> Mapping[str, Any]:
        """Change one member's cohorts and verify the exact resulting set."""
        current_member = self.find_exact_by_email(product_id, email)
        supplied_member_id = member.get("memberId", member.get("id"))
        current_member_id = current_member.get("memberId", current_member.get("id"))
        if (
            supplied_member_id is None
            or current_member_id is None
            or str(supplied_member_id) != str(current_member_id)
        ):
            raise MemberFilterIgnoredError(
                "o membro informado não corresponde ao produto e e-mail verificados"
            )
        write_result = self.change_cohorts(
            members=[current_member],
            new_cohorts=new_cohorts,
            confirm=confirm,
        )
        readback_member = self.find_exact_by_email(product_id, email)
        readback_member_id = readback_member.get("memberId", readback_member.get("id"))
        if str(readback_member_id) != str(current_member_id):
            raise CohortReadbackError(
                "o readback retornou outro membro para o mesmo produto e e-mail"
            )
        observed = _member_cohort_ids(readback_member)
        expected = set(_normalise_ids(new_cohorts))
        if set(observed) != expected:
            raise CohortReadbackError(
                "as turmas observadas após a escrita divergem do estado solicitado"
            )
        return {"write_result": write_result, "cohort_ids": observed}

    # Explicit aliases keep the readback helper discoverable for callers that
    # name the returned value rather than the member lookup operation.
    get_member_cohort_ids = get_current_cohort_ids
    readback_cohort_ids = get_current_cohort_ids

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
        normalized_members = []
        for member in members:
            member_id = member.get("memberId", member.get("id"))
            if member_id is None:
                raise ValueError("memberId is required to change cohorts")
            normalized_members.append(
                {
                    "memberId": str(member_id),
                    "currentCohorts": _member_cohort_ids(member),
                    "newCohorts": _normalise_ids(new_cohorts),
                }
            )
        body = {"members": normalized_members}
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
