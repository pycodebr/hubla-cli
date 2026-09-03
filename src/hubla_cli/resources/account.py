"""Account and collaborator resources."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from hubla_cli.resources.base import ResourceBase


def _id(value: Any) -> str:
    return quote(str(value), safe="")


class AccountResource(ResourceBase):
    """Inspect account settings and perform confirmed account changes."""

    def business(self) -> Any:
        return self._call("web", "GET", "/business")

    def profile(self) -> Any:
        return self._call("web", "GET", "/user/me/profile")

    def notifications(self) -> Any:
        return self._call("web", "GET", "/user/me/notifications")

    def reference(self) -> Any:
        return self._call("web", "GET", "/user/me/reference")

    def payout(self) -> Any:
        return self._call("web", "GET", "/kyc/get-payout")

    def two_factor_devices(self) -> Any:
        return self._call("web", "GET", "/two-factor/list-devices")

    def start_mfa(self, *, confirm: bool = False) -> Any:
        return self._write("web", "POST", "/mfa/start", confirm=confirm)

    def verify_mfa(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web", "POST", "/mfa/verify", json=dict(payload), confirm=confirm
        )

    def update_login_preferences(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "PUT",
            "/user/save-user-login-preferences",
            json=dict(payload),
            confirm=confirm,
        )

    def update_email(self, email: str, *, confirm: bool = False) -> Any:
        return self._write(
            "web",
            "PUT",
            "/auth/email",
            json={"newEmail": email},
            confirm=confirm,
        )

    def update_profile(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "functions",
            "POST",
            "/userInfo/setBasicInfo/pt",
            json={"data": dict(payload)},
            confirm=confirm,
        )

    def update_notifications(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "functions",
            "POST",
            "/userInfo/updateNotificationSettings/pt",
            json={"data": dict(payload)},
            confirm=confirm,
        )

    def collaborators(self) -> Any:
        return self._call("web", "GET", "/user/roleplay/collaborators")

    def add_collaborator(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "POST",
            "/user/roleplay/collaborators",
            json=dict(payload),
            confirm=confirm,
        )

    def update_collaborator(
        self,
        payload: Mapping[str, Any],
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "PUT",
            "/user/roleplay/collaborators",
            json=dict(payload),
            confirm=confirm,
        )

    def remove_collaborator(
        self,
        collaborator_id: str,
        *,
        confirm: bool = False,
    ) -> Any:
        return self._write(
            "web",
            "DELETE",
            f"/user/roleplay/collaborators/{_id(collaborator_id)}/",
            confirm=confirm,
        )
