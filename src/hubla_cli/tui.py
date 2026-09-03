"""Rich terminal rendering and the read-only interactive TUI."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.styles import Style
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

READ_ONLY_MENU = (
    ("account", "Visão geral da conta"),
    ("sales", "Vendas recentes"),
    ("products", "Produtos"),
    ("subscriptions", "Assinaturas recentes"),
    ("finance", "Saldo financeiro"),
    ("exit", "Sair"),
)

_TUI_STYLE = Style.from_dict(
    {
        "dialog": "bg:#09111f",
        "dialog frame.label": "bold #44d7ff",
        "dialog.body": "bg:#0d1728 #d7e5ff",
        "dialog shadow": "bg:#050a12",
        "button": "bg:#17243a #d7e5ff",
        "button.focused": "bg:#44d7ff #07101d bold",
        "radio": "#44d7ff",
        "radio-selected": "#ffd166 bold",
    }
)


def render_banner(console: Console) -> None:
    """Render the branded safety banner for the interactive interface."""
    title = Text("HUBLA CLI", style="bold #44d7ff")
    subtitle = Text(
        "Sua conta no terminal  •  TUI em modo somente leitura",
        style="#9fb3cc",
    )
    content = Text.assemble(title, "\n", subtitle)
    console.print(
        Panel(
            content,
            border_style="#245b78",
            box=box.ROUNDED,
            padding=(1, 3),
        )
    )


def _scalar(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "sim" if value else "não"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return str(value)


def _extract_rows(data: Any) -> list[Mapping[str, Any]] | None:
    if isinstance(data, list) and all(isinstance(item, Mapping) for item in data):
        return data
    if isinstance(data, Mapping):
        for key in ("items", "data", "results", "records"):
            candidate = data.get(key)
            if isinstance(candidate, list) and all(
                isinstance(item, Mapping) for item in candidate
            ):
                return candidate
    return None


def render_data(console: Console, data: Any, *, title: str = "Resultado") -> None:
    """Render API mappings and lists as readable Rich tables."""
    rows = _extract_rows(data)
    if rows is not None:
        table = Table(
            title=title,
            box=box.SIMPLE_HEAVY,
            header_style="bold #44d7ff",
            border_style="#245b78",
            show_lines=False,
        )
        if not rows:
            table.add_column("Resultado")
            table.add_row("Nenhum item encontrado")
            console.print(table)
            return
        keys: list[str] = []
        preferred = (
            "id",
            "name",
            "title",
            "email",
            "status",
            "value",
            "amount",
            "createdAt",
        )
        all_keys = [str(key) for row in rows for key in row]
        for key in (*preferred, *all_keys):
            if key in all_keys and key not in keys:
                keys.append(key)
            if len(keys) == 7:
                break
        if not keys:
            table.add_column("Resultado")
            for row in rows[:50]:
                table.add_row(_scalar(dict(row)))
            console.print(table)
            return
        for key in keys:
            table.add_column(key)
        for row in rows[:50]:
            table.add_row(*[_scalar(row.get(key)) for key in keys])
        console.print(table)
        if len(rows) > 50:
            console.print(f"[dim]Exibindo 50 de {len(rows)} itens.[/dim]")
        return

    if isinstance(data, Mapping):
        table = Table(
            title=title,
            box=box.SIMPLE_HEAVY,
            header_style="bold #44d7ff",
            border_style="#245b78",
        )
        table.add_column("Campo", style="bold")
        table.add_column("Valor")
        for key, value in data.items():
            table.add_row(str(key), _scalar(value))
        console.print(table)
        return

    if isinstance(data, Sequence) and not isinstance(data, (str, bytes, bytearray)):
        table = Table(title=title, box=box.SIMPLE_HEAVY)
        table.add_column("Valor")
        for value in data:
            table.add_row(_scalar(value))
        console.print(table)
        return
    console.print(Panel(_scalar(data), title=title, border_style="#245b78"))


def _select_menu() -> str | None:
    return radiolist_dialog(
        title="Hubla CLI",
        text="Escolha o que deseja consultar:",
        values=list(READ_ONLY_MENU),
        style=_TUI_STYLE,
        ok_text="Abrir",
        cancel_text="Sair",
    ).run()


def run_tui(client: Any, *, console: Console | None = None) -> None:
    """Run a safe, read-only interactive terminal menu."""
    console = console or Console()
    while True:
        console.clear()
        render_banner(console)
        choice = _select_menu()
        if choice in {None, "exit"}:
            console.print("[dim]Sessão encerrada.[/dim]")
            return
        try:
            if choice == "account":
                data = client.account.business()
                title = "Visão geral da conta"
            elif choice == "sales":
                data = client.sales.list(page=1, page_size=10)
                title = "Vendas recentes"
            elif choice == "products":
                data = client.products.list(page=1, page_size=25)
                title = "Produtos"
            elif choice == "subscriptions":
                data = client.subscriptions.list(page=1, page_size=10)
                title = "Assinaturas recentes"
            elif choice == "finance":
                data = client.finance.balance()
                title = "Saldo financeiro"
            else:  # pragma: no cover - menu values are closed
                continue
            render_data(console, data, title=title)
        except Exception as exc:
            console.print(
                Panel(
                    str(exc),
                    title="Não foi possível consultar",
                    border_style="red",
                )
            )
        input("\nPressione Enter para voltar ao menu...")
