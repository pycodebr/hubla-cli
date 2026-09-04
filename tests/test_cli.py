from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from hubla_cli import cli
from hubla_cli.credentials import StoredCredentials

runner = CliRunner()


class FakeResource:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def list(self, **kwargs: Any) -> Any:
        self.calls.append(("list", kwargs))
        return self.result

    def get(self, resource_id: str) -> Any:
        self.calls.append(("get", {"resource_id": resource_id}))
        return self.result

    def business(self) -> Any:
        self.calls.append(("business", {}))
        return self.result

    def refund(self, invoice_id: str, *, confirm: bool = False) -> Any:
        self.calls.append(("refund", {"invoice_id": invoice_id, "confirm": confirm}))
        return self.result

    def availability_forecast(
        self,
        *,
        target_dates: list[str] | None = None,
        currency: str = "BRL",
        timezone: str = "America/Sao_Paulo",
    ) -> Any:
        self.calls.append(
            (
                "availability_forecast",
                {
                    "target_dates": target_dates,
                    "currency": currency,
                    "timezone": timezone,
                },
            )
        )
        return self.result


class FakeClient:
    def __init__(self, result: Any = None) -> None:
        self.sales = FakeResource(result or {"items": [{"id": "sale-1"}]})
        self.products = FakeResource(result or {"items": [{"id": "product-1"}]})
        self.subscriptions = FakeResource(result or {"items": []})
        self.refunds = FakeResource(result or {"items": []})
        self.members = FakeResource(result or {"items": []})
        self.analytics = FakeResource(result or {})
        self.finance = FakeResource(result or {})
        self.account = FakeResource(result or {})


class FakeStore:
    def __init__(self) -> None:
        self.saved: tuple[str, str] | None = None

    def save(self, email: str, refresh_token: str) -> str:
        self.saved = (email, refresh_token)
        return "file"

    def load(self) -> StoredCredentials | None:
        return None

    def delete(self) -> None:
        return None


class FakeTokens:
    refresh_token = "refresh-token"


class FakeAuth:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def login(self) -> FakeTokens:
        return FakeTokens()


def test_schema_is_available_without_login_as_stable_json() -> None:
    result = runner.invoke(cli.app, ["--json", "schema", "sales", "refund"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["mutating"] is True
    assert "invoice_id" in payload["data"]["parameters"]


def test_sales_list_has_agent_friendly_json_output(monkeypatch: Any) -> None:
    client = FakeClient()
    monkeypatch.setattr(cli, "get_client", lambda profile: client)

    result = runner.invoke(
        cli.app,
        [
            "--json",
            "sales",
            "list",
            "--status",
            "paid",
            "--offer-id",
            "offer-1",
            "--page-size",
            "5",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == {"ok": True, "data": {"items": [{"id": "sale-1"}]}}
    assert client.sales.calls[0][1]["statuses"] == ["paid"]
    assert client.sales.calls[0][1]["offer_ids"] == ["offer-1"]
    assert client.sales.calls[0][1]["page_size"] == 5


def test_finance_forecast_accepts_repeated_target_dates(monkeypatch: Any) -> None:
    expected = {"forecasts": [{"date": "2026-09-30"}]}
    client = FakeClient(expected)
    monkeypatch.setattr(cli, "get_client", lambda profile: client)

    result = runner.invoke(
        cli.app,
        [
            "--json",
            "finance",
            "forecast",
            "--date",
            "2026-09-30",
            "--date",
            "2026-10-31",
            "--currency",
            "BRL",
            "--timezone",
            "America/Sao_Paulo",
        ],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["data"] == expected
    assert client.finance.calls == [
        (
            "availability_forecast",
            {
                "target_dates": ["2026-09-30", "2026-10-31"],
                "currency": "BRL",
                "timezone": "America/Sao_Paulo",
            },
        )
    ]


def test_dynamic_call_rejects_non_object_json_before_authentication() -> None:
    result = runner.invoke(
        cli.app,
        ["--json", "call", "sales", "list", "--params", "[]"],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "CommandError"


def test_doctor_returns_nonzero_json_when_no_credentials_exist(
    monkeypatch: Any,
) -> None:
    class PublicConfig:
        def get_api_key(self) -> str:
            return "public-key"

    monkeypatch.delenv("HUBLA_EMAIL", raising=False)
    monkeypatch.delenv("HUBLA_PASSWORD", raising=False)
    monkeypatch.delenv("HUBLA_REFRESH_TOKEN", raising=False)
    monkeypatch.setattr(cli, "FirebaseConfigResolver", lambda: PublicConfig())
    monkeypatch.setattr(cli, "CredentialStore", lambda profile: FakeStore())

    result = runner.invoke(cli.app, ["--json", "doctor"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["type"] == "DoctorError"
    assert payload["error"]["checks"]["credentials"]["ok"] is False


def test_doctor_accepts_refresh_token_from_environment(monkeypatch: Any) -> None:
    class PublicConfig:
        def get_api_key(self) -> str:
            return "public-key"

    monkeypatch.setenv("HUBLA_REFRESH_TOKEN", "environment-refresh")
    monkeypatch.delenv("HUBLA_PASSWORD", raising=False)
    monkeypatch.setattr(cli, "FirebaseConfigResolver", lambda: PublicConfig())
    monkeypatch.setattr(
        cli, "get_client", lambda profile: FakeClient({"id": "account"})
    )
    monkeypatch.setattr(
        cli,
        "CredentialStore",
        lambda profile: (_ for _ in ()).throw(
            AssertionError("saved profile must not be read")
        ),
    )

    result = runner.invoke(cli.app, ["--json", "doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["ok"] is True
    assert payload["data"]["credentials"]["source"] == "environment"
    assert payload["data"]["account"]["ok"] is True


def test_status_accepts_refresh_token_from_environment(monkeypatch: Any) -> None:
    monkeypatch.setenv("HUBLA_REFRESH_TOKEN", "environment-refresh")
    monkeypatch.setenv("HUBLA_EMAIL", "environment@example.com")
    monkeypatch.setattr(
        cli, "get_client", lambda profile: FakeClient({"id": "account"})
    )
    monkeypatch.setattr(
        cli,
        "CredentialStore",
        lambda profile: (_ for _ in ()).throw(
            AssertionError("saved profile must not be read")
        ),
    )

    result = runner.invoke(cli.app, ["--json", "status"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["email"] == "environment@example.com"
    assert payload["data"]["source"] == "environment"


def test_logout_does_not_claim_to_remove_environment_credentials(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("HUBLA_REFRESH_TOKEN", "environment-refresh")
    monkeypatch.setattr(
        cli,
        "CredentialStore",
        lambda profile: (_ for _ in ()).throw(
            AssertionError("saved profile must not be changed")
        ),
    )

    result = runner.invoke(cli.app, ["--json", "logout"])

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["type"] == "CommandError"
    assert "ambiente" in payload["error"]["message"]


def test_login_prompts_for_password_and_persists_only_refresh_token(
    monkeypatch: Any,
) -> None:
    store = FakeStore()
    monkeypatch.setattr(cli, "prompt_email", lambda: "owner@example.com")
    monkeypatch.setattr(cli, "prompt_password", lambda: "typed-password")
    monkeypatch.setattr(cli, "HublaAuth", FakeAuth)
    monkeypatch.setattr(cli, "CredentialStore", lambda profile: store)
    monkeypatch.setattr(cli, "verify_login", lambda auth: {"name": "Conta"})

    result = runner.invoke(cli.app, ["--json", "login"])

    assert result.exit_code == 0
    assert store.saved == ("owner@example.com", "refresh-token")
    assert "typed-password" not in result.stdout
    assert json.loads(result.stdout)["data"]["storage"] == "file"


def test_binary_call_can_be_written_to_an_explicit_output_file(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "export.xlsx"
    monkeypatch.setattr(cli, "get_client", lambda profile: FakeClient(result=b"xlsx"))
    monkeypatch.setattr(
        cli,
        "invoke_resource",
        lambda *args, **kwargs: b"xlsx",
    )

    result = runner.invoke(
        cli.app,
        [
            "--json",
            "call",
            "sales",
            "export",
            "--params",
            "{}",
            "--confirm",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert output.read_bytes() == b"xlsx"
    assert json.loads(result.stdout)["data"]["bytes_written"] == 4
    if os.name != "nt":
        assert output.stat().st_mode & 0o777 == 0o600


def test_binary_call_requires_an_explicit_output_file(monkeypatch: Any) -> None:
    calls = {"count": 0}

    def return_binary(*args: Any, **kwargs: Any) -> bytes:
        calls["count"] += 1
        return b"sensitive-export"

    monkeypatch.setattr(cli, "get_client", lambda profile: FakeClient())
    monkeypatch.setattr(cli, "invoke_resource", return_binary)

    result = runner.invoke(
        cli.app,
        [
            "--json",
            "call",
            "sales",
            "export",
            "--params",
            "{}",
            "--confirm",
        ],
    )

    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload["error"]["type"] == "CommandError"
    assert "--output" in payload["error"]["message"]
    assert calls["count"] == 0


def test_binary_call_does_not_replace_existing_output_without_force(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    calls = {"count": 0}

    def return_binary(*args: Any, **kwargs: Any) -> bytes:
        calls["count"] += 1
        return b"new"

    output = tmp_path / "export.xlsx"
    output.write_bytes(b"existing")
    monkeypatch.setattr(cli, "get_client", lambda profile: FakeClient())
    monkeypatch.setattr(cli, "invoke_resource", return_binary)

    result = runner.invoke(
        cli.app,
        [
            "--json",
            "call",
            "sales",
            "export",
            "--params",
            "{}",
            "--confirm",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 2
    assert output.read_bytes() == b"existing"
    assert calls["count"] == 0


def test_raw_binary_call_requires_output_before_authentication(
    monkeypatch: Any,
) -> None:
    def fail_if_authenticated(_profile: str) -> FakeClient:
        raise AssertionError("must not authenticate")

    monkeypatch.setattr(cli, "get_client", fail_if_authenticated)

    result = runner.invoke(
        cli.app,
        ["--json", "api", "web", "GET", "/export", "--bytes"],
    )

    assert result.exit_code == 2
    assert "--output" in json.loads(result.stdout)["error"]["message"]


def test_binary_call_replaces_existing_output_atomically_with_force(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "export.xlsx"
    output.write_bytes(b"existing")
    monkeypatch.setattr(cli, "get_client", lambda profile: FakeClient())
    monkeypatch.setattr(cli, "invoke_resource", lambda *args, **kwargs: b"new")

    result = runner.invoke(
        cli.app,
        [
            "--json",
            "call",
            "sales",
            "export",
            "--params",
            "{}",
            "--confirm",
            "--output",
            str(output),
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert output.read_bytes() == b"new"
    assert not list(tmp_path.glob("*.tmp"))
    if os.name != "nt":
        assert output.stat().st_mode & 0o777 == 0o600


def test_skill_install_command_reports_every_target(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        cli,
        "install_skill",
        lambda agent, force=False: [
            {
                "agent": agent,
                "path": "/tmp/skills/hubla-cli",
                "status": "installed",
            }
        ],
    )

    result = runner.invoke(
        cli.app,
        ["--json", "skill", "install", "--agent", "generic"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"][0]["agent"] == "generic"
    assert payload["data"][0]["status"] == "installed"


def test_skill_status_command_is_available_without_hubla_login(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        cli,
        "skill_status",
        lambda agent: [{"agent": agent, "installed": True, "current": True}],
    )

    result = runner.invoke(
        cli.app,
        ["--json", "skill", "status", "--agent", "auto"],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["data"][0]["current"] is True


def test_skill_install_command_fails_when_an_unmanaged_skill_conflicts(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        cli,
        "install_skill",
        lambda agent, force=False: [
            {
                "agent": agent,
                "path": "/tmp/skills/hubla-cli",
                "status": "conflict",
            }
        ],
    )

    result = runner.invoke(
        cli.app,
        ["--json", "skill", "install", "--agent", "generic"],
    )

    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["type"] == "CommandError"
