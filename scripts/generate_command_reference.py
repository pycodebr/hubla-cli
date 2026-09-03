#!/usr/bin/env python3
"""Generate the complete high-level Hubla resource command reference."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hubla_cli.catalog import build_catalog  # noqa: E402

OUTPUT_PATH = ROOT / "docs" / "command-reference.md"


def _parameter_summary(parameters: dict[str, dict[str, Any]]) -> str:
    values: list[str] = []
    for name, metadata in parameters.items():
        if name == "confirm":
            continue
        suffix = "" if metadata["required"] else "?"
        values.append(f"`{name}{suffix}`")
    return ", ".join(values) if values else "—"


def render_reference() -> str:
    """Return deterministic Markdown for every public resource operation."""
    catalog = build_catalog()
    lines = [
        "# Referência completa de operações",
        "",
        "> Gerado por `scripts/generate_command_reference.py`. Não edite manualmente.",
        "> Este projeto é comunitário e não oficial; as APIs do portal podem mudar.",
        "",
        "Use qualquer operação abaixo com:",
        "",
        "```bash",
        'hubla-cli --json call RECURSO OPERAÇÃO --params \'{"parametro":"valor"}\'',
        "```",
        "",
        "Operações marcadas como **alteração** exigem autorização específica do usuário e `--confirm`.",
        "Parâmetros com `?` são opcionais. Consulte o schema executável para tipos e valores padrão:",
        "",
        "```bash",
        "hubla-cli --json schema RECURSO OPERAÇÃO",
        "```",
        "",
    ]
    for resource_name, resource in catalog["resources"].items():
        lines.extend(
            [
                f"## {resource_name}",
                "",
                str(resource["description"]),
                "",
                "| Operação | Tipo | Parâmetros |",
                "| --- | --- | --- |",
            ]
        )
        for operation_name, operation in resource["operations"].items():
            if operation["binary"] and operation["mutating"]:
                operation_type = "**exportação binária — `--confirm` e `--output`**"
            elif operation["binary"]:
                operation_type = "leitura binária — `--output`"
            else:
                operation_type = (
                    "**alteração — `--confirm`**"
                    if operation["mutating"]
                    else "leitura"
                )
            parameters = _parameter_summary(operation["parameters"])
            lines.append(
                f"| `{resource_name}.{operation_name}` | {operation_type} | {parameters} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Falha quando o arquivo versionado está desatualizado.",
    )
    args = parser.parse_args()
    expected = render_reference()
    if args.check:
        if (
            not OUTPUT_PATH.exists()
            or OUTPUT_PATH.read_text(encoding="utf-8") != expected
        ):
            print(
                "docs/command-reference.md está desatualizado; "
                "execute scripts/generate_command_reference.py"
            )
            return 1
        return 0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(expected, encoding="utf-8")
    print(OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
