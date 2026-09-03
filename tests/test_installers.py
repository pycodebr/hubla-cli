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
    assert "HUBLA_CLI_UV_VERSION" in contents
    assert "HUBLA_CLI_FORCE_MANAGED_PYTHON" in contents
    assert "UV_UNMANAGED_INSTALL" in contents
    assert "UV_PYTHON_INSTALL_DIR" in contents
    assert "UV_PYTHON_INSTALL_BIN" in contents
    assert "https://astral.sh/uv/${UV_VERSION}/install.sh" in contents
    assert 'python install "${MANAGED_PYTHON_VERSION}"' in contents
    assert 'python find --managed-python "${MANAGED_PYTHON_VERSION}"' in contents
    assert "uv_version_is_expected" in contents
    assert "command -v uv" not in contents
    assert '"${HOME}/.zprofile"' in contents
    assert '"${HOME}/.bash_profile"' in contents
    assert "terminal separado" in contents


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
    assert "HUBLA_CLI_UV_VERSION" in contents
    assert "HUBLA_CLI_FORCE_MANAGED_PYTHON" in contents
    assert "UV_UNMANAGED_INSTALL" in contents
    assert "UV_PYTHON_INSTALL_DIR" in contents
    assert "UV_PYTHON_INSTALL_BIN" in contents
    assert "https://astral.sh/uv/$UvVersion/install.ps1" in contents
    assert "python install $ManagedPythonVersion" in contents
    assert "python find --managed-python $ManagedPythonVersion" in contents
    assert "Test-UvVersion" in contents
    assert "Get-Command uv" not in contents
    assert "Invoke-Expression" not in contents
    assert "Invoke-WebRequest" in contents
    assert "ExecutionPolicy Bypass" in contents
    assert "$InstallerOutput | Out-Host" in contents
    assert "Get-Command py" in contents
    assert "Get-Command python" in contents
    assert "UTF8Encoding($false)" in contents
    assert contents.count("$LASTEXITCODE -ne 0") >= 4
    assert "hubla-cli managed wrapper" in contents
    assert "não é gerenciado pelo Hubla CLI" in contents
    assert "terminal separado" in contents


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
