from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_bash_installer_has_valid_syntax_and_safe_defaults() -> None:
    installer = ROOT / "install.sh"

    contents = installer.read_text(encoding="utf-8")

    if os.name != "nt":
        result = subprocess.run(
            ["bash", "-n", str(installer)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
    assert contents.startswith("#!/usr/bin/env bash\n")
    assert "set -Eeuo pipefail" in contents
    assert "https://github.com/pycodebr/hubla-cli" in contents
    assert "skill install --agent" in contents
    assert "sudo" not in contents
    assert "HUBLA_CLI_PACKAGE_URL" in contents
    assert "HUBLA_CLI_VERSION" in contents
    assert "archive/refs/tags/v${VERSION}.zip" in contents
    assert '"${HOME}/.zprofile"' in contents
    assert '"${HOME}/.bash_profile"' in contents


def test_powershell_installer_is_user_scoped_and_installs_skill() -> None:
    contents = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "https://github.com/pycodebr/hubla-cli" in contents
    assert "skill install" in contents
    assert "EnvironmentVariable" in contents
    assert "User" in contents
    assert "RunAs" not in contents
    assert "HUBLA_CLI_PACKAGE_URL" in contents
    assert "HUBLA_CLI_VERSION" in contents
    assert "archive/refs/tags/v$Version.zip" in contents
    assert contents.count("if (-not $PythonExecutable") >= 2
    assert "UTF8Encoding($false)" in contents
    assert contents.count("$LASTEXITCODE -ne 0") >= 4
    assert "hubla-cli managed wrapper" in contents
    assert "não é gerenciado pelo Hubla CLI" in contents


def test_installers_do_not_collect_or_embed_hubla_credentials() -> None:
    combined = "\n".join(
        [
            (ROOT / "install.sh").read_text(encoding="utf-8"),
            (ROOT / "install.ps1").read_text(encoding="utf-8"),
        ]
    )

    assert "HUBLA_PASSWORD=" not in combined
    assert "HUBLA_REFRESH_TOKEN=" not in combined
    assert "identitytoolkit" not in combined
