from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from hubla_cli.version import __version__

ROOT = Path(__file__).parents[1]


def test_readme_contains_both_installers_and_ai_agent_prompt() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert (
        "curl -fsSL https://raw.githubusercontent.com/pycodebr/hubla-cli/main/install.sh | bash"
        in readme
    )
    assert (
        "irm https://raw.githubusercontent.com/pycodebr/hubla-cli/main/install.ps1 | iex"
        in readme
    )
    assert "## Instalação em agentes de IA" in readme
    assert "Prompt para copiar" in readme
    for agent in (
        "Claude Code",
        "Codex",
        "Hermes",
        "OpenClaw",
        "Antigravity",
        "OpenCode",
        "Pi",
    ):
        assert agent in readme
    assert "hubla-cli login" in readme
    assert "skill install --agent auto" in readme
    assert "Não execute `hubla-cli login` pelo seu terminal interno" in readme
    assert "Pare e aguarde eu responder “autenticado”" in readme
    assert "Depois responda ao agente:" in readme
    assert "me deixe digitar o e-mail e a senha" not in readme
    assert "instala automaticamente um Python 3.12 gerenciado" in readme


def test_readme_documents_every_top_level_command() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for command in (
        "login",
        "logout",
        "status",
        "doctor",
        "tui",
        "schema",
        "call",
        "api",
        "sales",
        "refunds",
        "subscriptions",
        "products",
        "members",
        "analytics",
        "finance",
        "account",
        "skill",
    ):
        assert f"`{command}`" in readme


def test_public_documents_are_generic_and_mark_project_unofficial() -> None:
    paths = [
        ROOT / "README.md",
        ROOT / "SECURITY.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "docs" / "command-reference.md",
        ROOT / "docs" / "api-map.md",
        ROOT / "skills" / "hubla-cli" / "SKILL.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    lowered = combined.lower()

    assert "não oficial" in lowered
    assert "conta autorizada" in lowered
    assert "offer_id" in lowered
    assert "regras específicas de uma empresa" not in lowered


def test_mit_license_is_present() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert "MIT License" in license_text
    assert "Copyright (c) 2026" in license_text
    assert "Permission is hereby granted" in license_text


def test_generated_command_reference_is_current() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_command_reference.py"),
            "--check",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_release_version_is_consistent_across_package_installers_and_skill() -> None:
    expected_toml = f'version = "{__version__}"'
    expected_bash = f"HUBLA_CLI_VERSION:-{__version__}"
    expected_powershell = f'else {{ "{__version__}" }}'
    expected_skill = f'version: "{__version__}"'

    assert expected_toml in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert expected_bash in (ROOT / "install.sh").read_text(encoding="utf-8")
    assert expected_powershell in (ROOT / "install.ps1").read_text(encoding="utf-8")
    assert expected_skill in (ROOT / "skills" / "hubla-cli" / "SKILL.md").read_text(
        encoding="utf-8"
    )


def test_repository_enforces_lf_and_uses_current_github_actions() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    release = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "*.py text eol=lf" in attributes
    assert "*.sh text eol=lf" in attributes
    assert "actions/checkout@v7" in ci
    assert "actions/setup-python@v7" in ci
    assert "actions/upload-artifact@v7" in ci
    assert "Installer bootstrap / ${{ matrix.os }}" in ci
    assert 'HUBLA_CLI_FORCE_MANAGED_PYTHON: "1"' in ci
    assert 'HUBLA_CLI_FORCE_UV_INSTALL: "1"' in ci
    assert "actions/checkout@v7" in release
    assert "actions/setup-python@v7" in release
