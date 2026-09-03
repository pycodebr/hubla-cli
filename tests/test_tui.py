from __future__ import annotations

import os
import sys
from io import StringIO
from typing import Any

import pytest
from rich.console import Console

from hubla_cli import prompts
from hubla_cli.tui import READ_ONLY_MENU, render_banner, render_data


def test_password_prompt_enables_masking(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def fake_prompt(message: str, **kwargs: Any) -> str:
        captured["message"] = message
        captured.update(kwargs)
        return "secret"

    monkeypatch.setattr(prompts, "prompt", fake_prompt)

    assert prompts.prompt_password() == "secret"
    assert captured["is_password"] is True
    assert captured["message"] == "Senha: "


@pytest.mark.skipif(os.name == "nt", reason="PTY smoke test uses pexpect")
def test_password_prompt_renders_asterisks_without_echoing_plaintext() -> None:
    import pexpect

    child = pexpect.spawn(
        sys.executable,
        [
            "-c",
            "from hubla_cli.prompts import prompt_password; prompt_password()",
        ],
        encoding="utf-8",
        timeout=10,
    )
    child.expect("Senha:")
    child.sendline("s3cret")
    child.expect(pexpect.EOF)
    rendered = child.before

    assert isinstance(rendered, str)
    assert "s3cret" not in rendered
    assert rendered.count("*") >= 6


def test_tui_banner_identifies_read_only_safety_mode() -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=100)

    render_banner(console)

    rendered = output.getvalue()
    assert "HUBLA CLI" in rendered
    assert "somente leitura" in rendered


def test_tui_primary_menu_contains_no_mutation_action() -> None:
    values = {value for value, _label in READ_ONLY_MENU}

    assert values == {
        "account",
        "sales",
        "products",
        "subscriptions",
        "finance",
        "exit",
    }


def test_tui_renders_list_payload_as_a_table() -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=100)

    render_data(
        console,
        {"items": [{"id": "sale-1", "status": "paid", "value": 1000}]},
        title="Vendas recentes",
    )

    rendered = output.getvalue()
    assert "Vendas recentes" in rendered
    assert "sale-1" in rendered
    assert "paid" in rendered


def test_tui_handles_rows_without_scalar_columns() -> None:
    output = StringIO()
    console = Console(file=output, force_terminal=False, width=100)

    render_data(console, {"items": [{}]}, title="Resultado vazio")

    assert "vazio" in output.getvalue()
    assert "{}" in output.getvalue()
