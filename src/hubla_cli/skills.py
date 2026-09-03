"""Install the bundled Agent Skill into supported AI harnesses."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

from hubla_cli.errors import CommandError
from hubla_cli.version import __version__

_SKILL_NAME = "hubla-cli"
_MARKER_NAME = ".hubla-cli-managed.json"
_MARKER_FORMAT = "hubla-cli.skill-marker.v1"
_SUPPORTED_AGENTS = {
    "agy",
    "auto",
    "all",
    "generic",
    "claude",
    "codex",
    "hermes",
    "openclaw",
    "antigravity",
    "opencode",
    "pi",
}


@dataclass(frozen=True)
class SkillTarget:
    """A harness name and its global Agent Skills root."""

    name: str
    root: Path


def _default_command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def _native_roots(home: Path, environ: Mapping[str, str]) -> dict[str, Path]:
    hermes_home = Path(environ.get("HERMES_HOME", home / ".hermes")).expanduser()
    openclaw_home = Path(
        environ.get("OPENCLAW_STATE_DIR", home / ".openclaw")
    ).expanduser()
    generic = home / ".agents" / "skills"
    return {
        "generic": generic,
        "claude": home / ".claude" / "skills",
        "codex": generic,
        "hermes": hermes_home / "skills",
        "openclaw": openclaw_home / "skills",
        "antigravity": home / ".gemini" / "config" / "skills",
        "opencode": generic,
        "pi": generic,
    }


def resolve_skill_targets(
    agent: str = "auto",
    *,
    home: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    command_exists: Callable[[str], bool] = _default_command_exists,
) -> list[SkillTarget]:
    """Resolve idempotent user-level skill destinations for a harness."""
    normalized = agent.strip().lower()
    if normalized == "agy":
        normalized = "antigravity"
    if normalized not in _SUPPORTED_AGENTS:
        supported = ", ".join(sorted(_SUPPORTED_AGENTS))
        raise CommandError(f"agente desconhecido: {agent}; opções: {supported}")
    selected_home = Path(home or Path.home()).expanduser()
    selected_environment = dict(os.environ if environ is None else environ)
    roots = _native_roots(selected_home, selected_environment)

    if normalized not in {"auto", "all"}:
        return [SkillTarget(normalized, roots[normalized])]

    names = ["generic"]
    if normalized == "all":
        names.extend(["claude", "hermes", "openclaw", "antigravity"])
    else:
        detections = {
            "claude": command_exists("claude") or (selected_home / ".claude").exists(),
            "hermes": command_exists("hermes")
            or "HERMES_HOME" in selected_environment
            or (selected_home / ".hermes").exists(),
            "openclaw": command_exists("openclaw")
            or "OPENCLAW_STATE_DIR" in selected_environment
            or (selected_home / ".openclaw").exists(),
            "antigravity": command_exists("agy")
            or command_exists("antigravity")
            or (selected_home / ".gemini" / "config").exists(),
        }
        names.extend(name for name, detected in detections.items() if detected)

    targets: list[SkillTarget] = []
    seen: set[Path] = set()
    for name in names:
        root = roots[name]
        resolved = root.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        targets.append(SkillTarget(name, root))
    return targets


def _skill_content() -> str:
    return files("hubla_cli").joinpath("data/SKILL.md").read_text(encoding="utf-8")


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _read_marker(path: Path) -> dict[str, Any] | None:
    if path.is_symlink():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    if (
        data.get("format") != _MARKER_FORMAT
        or data.get("managed_by") != "hubla-cli"
        or data.get("source") != "bundled-agent-skill"
        or not isinstance(data.get("version"), str)
        or not isinstance(data.get("skill_sha256"), str)
        or len(data["skill_sha256"]) != 64
        or any(
            character not in "0123456789abcdef" for character in data["skill_sha256"]
        )
    ):
        return None
    return data


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install_skill(
    agent: str = "auto",
    *,
    home: str | Path | None = None,
    force: bool = False,
    environ: Mapping[str, str] | None = None,
    command_exists: Callable[[str], bool] = _default_command_exists,
) -> list[dict[str, Any]]:
    """Install or update the bundled skill without overwriting user-owned skills."""
    content = _skill_content()
    results: list[dict[str, Any]] = []
    for target in resolve_skill_targets(
        agent,
        home=home,
        environ=environ,
        command_exists=command_exists,
    ):
        skill_dir = target.root / _SKILL_NAME
        skill_path = skill_dir / "SKILL.md"
        marker_path = skill_dir / _MARKER_NAME
        if skill_dir.is_symlink():
            results.append(
                {
                    "agent": target.name,
                    "path": str(skill_dir),
                    "status": "conflict",
                    "message": "diretório simbólico rejeitado; revise-o manualmente",
                }
            )
            continue
        marker = _read_marker(marker_path)
        if skill_dir.exists() and marker is None and not force:
            results.append(
                {
                    "agent": target.name,
                    "path": str(skill_dir),
                    "status": "conflict",
                    "message": "skill existente não gerenciada; nada foi sobrescrito",
                }
            )
            continue
        if skill_path.is_symlink() and not force:
            results.append(
                {
                    "agent": target.name,
                    "path": str(skill_dir),
                    "status": "conflict",
                    "message": "SKILL.md simbólico rejeitado; nada foi sobrescrito",
                }
            )
            continue

        current = False
        existing_hash = None
        if marker is not None and skill_path.is_file():
            try:
                existing_content = skill_path.read_text(encoding="utf-8")
                existing_hash = _content_hash(existing_content)
                current = existing_content == content
            except OSError:
                current = False
        if (
            marker is not None
            and existing_hash is not None
            and existing_hash != marker["skill_sha256"]
            and not force
        ):
            results.append(
                {
                    "agent": target.name,
                    "path": str(skill_dir),
                    "status": "conflict",
                    "message": "skill gerenciada foi modificada; nada foi sobrescrito",
                }
            )
            continue
        if current and marker is not None and marker.get("version") == __version__:
            results.append(
                {
                    "agent": target.name,
                    "path": str(skill_dir),
                    "status": "up-to-date",
                }
            )
            continue

        skill_dir.mkdir(parents=True, exist_ok=True)
        _write_text_atomic(skill_path, content)
        _write_text_atomic(
            marker_path,
            json.dumps(
                {
                    "format": _MARKER_FORMAT,
                    "managed_by": "hubla-cli",
                    "version": __version__,
                    "source": "bundled-agent-skill",
                    "skill_sha256": _content_hash(content),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )
        results.append(
            {
                "agent": target.name,
                "path": str(skill_dir),
                "status": "updated" if marker is not None else "installed",
            }
        )
    return results


def skill_status(
    agent: str = "auto",
    *,
    home: str | Path | None = None,
    environ: Mapping[str, str] | None = None,
    command_exists: Callable[[str], bool] = _default_command_exists,
) -> list[dict[str, Any]]:
    """Report whether each resolved target has the current managed skill."""
    content = _skill_content()
    results: list[dict[str, Any]] = []
    for target in resolve_skill_targets(
        agent,
        home=home,
        environ=environ,
        command_exists=command_exists,
    ):
        skill_dir = target.root / _SKILL_NAME
        skill_path = skill_dir / "SKILL.md"
        marker = _read_marker(skill_dir / _MARKER_NAME)
        installed = skill_path.is_file()
        current = False
        if installed:
            try:
                current = skill_path.read_text(encoding="utf-8") == content
            except OSError:
                current = False
        results.append(
            {
                "agent": target.name,
                "path": str(skill_dir),
                "installed": installed,
                "managed": marker is not None,
                "current": current and marker is not None,
                "version": marker.get("version") if marker else None,
            }
        )
    return results
