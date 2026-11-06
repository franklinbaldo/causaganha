#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "google-colab-cli",
# ]
# ///
"""Run non-interactive Google Colab CLI commands on unsupported Windows hosts."""

from __future__ import annotations

import os
import sys
import types
from collections.abc import Sequence

BLOCKED_WINDOWS_COMMANDS = {"console", "ssh"}
GLOBAL_OPTIONS_WITH_VALUE = {
    "--auth",
    "--client-oauth-config",
    "--config",
    "-c",
}


def install_tty_stubs() -> None:
    """Satisfy Unix-only imports without pretending that raw TTY works."""
    if os.name != "nt":
        return

    termios = types.ModuleType("termios")
    termios.TCSANOW = 0
    termios.tcgetattr = _unsupported_tty
    termios.tcsetattr = _unsupported_tty

    tty = types.ModuleType("tty")
    tty.setraw = _unsupported_tty

    sys.modules.setdefault("termios", termios)
    sys.modules.setdefault("tty", tty)


def _unsupported_tty(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("Raw Colab TTY commands are unavailable on Windows.")


def requested_command(arguments: Sequence[str]) -> str | None:
    """Return the first non-option CLI token."""
    skip_next = False
    for argument in arguments:
        if skip_next:
            skip_next = False
            continue
        if argument in GLOBAL_OPTIONS_WITH_VALUE:
            skip_next = True
            continue
        if not argument.startswith("-"):
            return argument
    return None


def forwarded_arguments() -> list[str]:
    return sys.argv[1:]


def main() -> int:
    command = requested_command(forwarded_arguments())
    if os.name == "nt" and command in BLOCKED_WINDOWS_COMMANDS:
        print(
            f"ERROR: 'colab {command}' needs a Unix TTY. "
            "Use WSL or a non-interactive command.",
            file=sys.stderr,
        )
        return 2

    install_tty_stubs()
    try:
        from colab_cli.cli import main as colab_main
    except ImportError as error:
        print(
            "ERROR: install google-colab-cli in this environment.",
            file=sys.stderr,
        )
        raise SystemExit(2) from error

    result = colab_main()
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
