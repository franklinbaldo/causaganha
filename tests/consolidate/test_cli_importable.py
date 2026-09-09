"""The consolidate CLI module must be importable and every command must build.

``force: bool = typer.Option("--force", default=False, ...)`` passes the
option's declared name (``"--force"``) as Typer's positional ``default``
argument *and* repeats ``default=False`` as a keyword — Typer raises
``TypeError: Option() got multiple values for argument 'default'`` while
building the ``reconsolidate`` command, at *module import time*. That takes
down every subcommand in the file (``date``, ``tribunal-year``, ``backfill``,
``reconsolidate``), not just the one with the mistake: `python -m
causaganha.consolidate ...` cannot run at all.
"""

from __future__ import annotations

from typer.testing import CliRunner


def test_consolidate_cli_module_imports() -> None:
    import causaganha.consolidate.cli  # noqa: F401


def test_reconsolidate_command_builds_and_shows_help() -> None:
    from causaganha.consolidate.cli import app

    result = CliRunner().invoke(app, ["reconsolidate", "--help"])

    assert result.exit_code == 0, result.output


def test_reconsolidate_force_flag_is_a_boolean_option() -> None:
    from causaganha.consolidate.cli import app

    result = CliRunner().invoke(app, ["reconsolidate", "--force", "--help"])

    assert result.exit_code == 0, result.output
