"""Interactive prompts shared by login and the terminal interface."""

from __future__ import annotations

from prompt_toolkit import prompt
from prompt_toolkit.styles import Style

_PROMPT_STYLE = Style.from_dict(
    {
        "prompt": "bold #44d7ff",
    }
)


def prompt_email() -> str:
    """Prompt for a Hubla account email."""
    return prompt(
        [("class:prompt", "E-mail da conta Hubla: ")],
        style=_PROMPT_STYLE,
    ).strip()


def prompt_password() -> str:
    """Prompt for a password with one visible asterisk per character."""
    return prompt(
        "Senha: ",
        is_password=True,
        style=_PROMPT_STYLE,
    )
