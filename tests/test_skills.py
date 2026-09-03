from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hubla_cli.skills import install_skill, resolve_skill_targets, skill_status
from hubla_cli.version import __version__


def test_generic_target_uses_agent_skills_standard(tmp_path: Path) -> None:
    targets = resolve_skill_targets(
        "generic",
        home=tmp_path,
        environ={},
        command_exists=lambda _command: False,
    )

    assert [target.name for target in targets] == ["generic"]
    assert targets[0].root == tmp_path / ".agents" / "skills"


def test_named_agents_use_verified_global_skill_locations(tmp_path: Path) -> None:
    expected = {
        "claude": tmp_path / ".claude" / "skills",
        "codex": tmp_path / ".agents" / "skills",
        "hermes": tmp_path / ".hermes" / "skills",
        "openclaw": tmp_path / ".openclaw" / "skills",
        "antigravity": tmp_path / ".gemini" / "config" / "skills",
        "agy": tmp_path / ".gemini" / "config" / "skills",
        "opencode": tmp_path / ".agents" / "skills",
        "pi": tmp_path / ".agents" / "skills",
    }

    for agent, root in expected.items():
        targets = resolve_skill_targets(
            agent,
            home=tmp_path,
            environ={},
            command_exists=lambda _command: False,
        )
        assert len(targets) == 1
        assert targets[0].root == root


def test_auto_always_installs_universal_skill_and_detected_native_agents(
    tmp_path: Path,
) -> None:
    commands = {"agy", "claude", "hermes"}
    targets = resolve_skill_targets(
        "auto",
        home=tmp_path,
        environ={},
        command_exists=lambda command: command in commands,
    )

    assert {target.name for target in targets} == {
        "generic",
        "claude",
        "hermes",
        "antigravity",
    }


def test_skill_install_is_idempotent_and_marks_managed_directory(
    tmp_path: Path,
) -> None:
    first = install_skill("generic", home=tmp_path)
    second = install_skill("generic", home=tmp_path)

    target = tmp_path / ".agents" / "skills" / "hubla-cli"
    assert first[0]["status"] == "installed"
    assert second[0]["status"] == "up-to-date"
    assert (target / "SKILL.md").is_file()
    marker = json.loads((target / ".hubla-cli-managed.json").read_text())
    assert marker["version"] == __version__


def test_skill_install_does_not_overwrite_unmanaged_skill(tmp_path: Path) -> None:
    target = tmp_path / ".agents" / "skills" / "hubla-cli"
    target.mkdir(parents=True)
    original = "custom skill"
    (target / "SKILL.md").write_text(original)

    result = install_skill("generic", home=tmp_path)

    assert result[0]["status"] == "conflict"
    assert (target / "SKILL.md").read_text() == original


@pytest.mark.parametrize(
    "marker",
    [
        {},
        {"managed_by": "another-tool", "version": "0.1.0"},
        {"managed_by": "hubla-cli", "version": "0.1.0"},
    ],
)
def test_skill_install_rejects_invalid_or_foreign_markers(
    tmp_path: Path,
    marker: dict[str, str],
) -> None:
    target = tmp_path / ".agents" / "skills" / "hubla-cli"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("custom skill", encoding="utf-8")
    (target / ".hubla-cli-managed.json").write_text(
        json.dumps(marker),
        encoding="utf-8",
    )

    result = install_skill("generic", home=tmp_path)

    assert result[0]["status"] == "conflict"
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "custom skill"


def test_skill_install_does_not_overwrite_a_user_modified_managed_skill(
    tmp_path: Path,
) -> None:
    install_skill("generic", home=tmp_path)
    target = tmp_path / ".agents" / "skills" / "hubla-cli" / "SKILL.md"
    target.write_text("user customization", encoding="utf-8")

    result = install_skill("generic", home=tmp_path)

    assert result[0]["status"] == "conflict"
    assert target.read_text(encoding="utf-8") == "user customization"


@pytest.mark.skipif(os.name == "nt", reason="symlink creation is privileged on Windows")
def test_skill_install_rejects_a_symbolic_skill_directory(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text("outside skill", encoding="utf-8")
    target = tmp_path / ".agents" / "skills" / "hubla-cli"
    target.parent.mkdir(parents=True)
    target.symlink_to(outside, target_is_directory=True)

    result = install_skill("generic", home=tmp_path)

    assert result[0]["status"] == "conflict"
    assert (outside / "SKILL.md").read_text(encoding="utf-8") == "outside skill"


def test_skill_status_reports_managed_and_current(tmp_path: Path) -> None:
    install_skill("generic", home=tmp_path)

    status = skill_status("generic", home=tmp_path)

    assert status[0]["installed"] is True
    assert status[0]["managed"] is True
    assert status[0]["current"] is True


def test_repository_skill_and_packaged_skill_are_identical() -> None:
    root = Path(__file__).parents[1]
    repository_skill = root / "skills" / "hubla-cli" / "SKILL.md"
    packaged_skill = root / "src" / "hubla_cli" / "data" / "SKILL.md"

    assert repository_skill.read_text(encoding="utf-8") == packaged_skill.read_text(
        encoding="utf-8"
    )
    contents = repository_skill.read_text(encoding="utf-8").lower()
    assert "pycodebr" not in contents
    assert "hubla-cli --json schema" in contents
    assert "--confirm" in contents
    assert "senha" in contents
