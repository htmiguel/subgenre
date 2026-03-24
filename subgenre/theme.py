"""Semantic Rich styles and Console factory — no ad-hoc color codes in handlers."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from rich.console import Console
from rich.theme import Theme

# Theme keys: success, warning, error, info, muted, accent — use markup: [success]…[/success]
DEFAULT_THEME = Theme(
    {
        "success": "green",
        "warning": "yellow",
        "error": "bold red",
        "info": "cyan",
        "muted": "dim",
        "accent": "bold",
    }
)


@dataclass(frozen=True)
class Symbols:
    ok: str
    warn: str
    err: str
    info: str
    bullet: str


def get_symbols(*, prefer_unicode: bool) -> Symbols:
    if prefer_unicode:
        return Symbols(ok="✓", warn="⚠", err="✗", info="ℹ", bullet="•")
    return Symbols(ok="[ok]", warn="[!]", err="[x]", info="[i]", bullet="-")


def stderr_is_tty() -> bool:
    return sys.stderr.isatty()


def should_use_color(*, no_color_flag: bool, force_terminal: bool | None = None) -> bool:
    if no_color_flag or os.environ.get("NO_COLOR"):
        return False
    if force_terminal is False:
        return False
    return stderr_is_tty()


def make_console(
    *,
    no_color: bool = False,
    force_terminal: bool | None = None,
) -> Console:
    """Rich Console that respects NO_COLOR, --no-color, and non-TTY output."""
    color = should_use_color(no_color_flag=no_color, force_terminal=force_terminal)
    return Console(
        stderr=True,
        theme=DEFAULT_THEME,
        no_color=not color,
        force_terminal=force_terminal,
        highlight=False,
    )
