"""Contract coverage for the Cyclopts-based consolidate CLI (RFC 0013 Fase 5).

`causaganha.consolidate.cli` was migrated from Typer to Cyclopts to finish
what RFC 0013 deliberately left out of scope (neither this module nor
`segmenter_dataset` is invoked by any GitHub Actions workflow, so the
original RFC covered only the four DJEN/TJRO/STJ/DataJud sync packages).
This module previously guarded only against the import-breaking bug fixed
in PR #1350 (a stray `typer.Option` argument-order collision); it now also
locks in the argv contract that migration must preserve, following the
same conventions RFC 0013's Fase 4 established for the other four CLIs.
"""

from __future__ import annotations

from tests.cli_contract.harness import _invoke


def test_consolidate_cli_module_imports() -> None:
    import causaganha.consolidate.cli  # noqa: F401


def test_reconsolidate_command_builds_and_shows_help() -> None:
    from causaganha.consolidate.cli import app

    exit_code, output = _invoke(app, ["reconsolidate", "--help"])

    assert exit_code == 0, output


def test_reconsolidate_force_flag_is_a_boolean_option() -> None:
    from causaganha.consolidate.cli import app

    exit_code, output = _invoke(app, ["reconsolidate", "--force", "--help"])

    assert exit_code == 0, output


def test_empty_invocation_shows_help() -> None:
    """This CLI made a clean break from the old Typer app's `no_args_is_help`
    exit-2 convention: a bare invocation just shows help and exits 0,
    Cyclopts' own default -- there is no production workflow depending on
    the old exit code, so there is nothing to preserve here."""
    from causaganha.consolidate.cli import app

    exit_code, output = _invoke(app, [])

    assert exit_code == 0, output
    assert "Usage:" in output


def test_date_argument_is_positional_only() -> None:
    """`typer.Argument` fields were positional-only under Typer; Cyclopts
    derives that only from the Python signature's own `/`, not from a
    separate class marker (RFC 0013 Fase 4 review finding #855) — this
    guards against silently regaining an option alias that never existed."""
    from causaganha.consolidate.cli import app

    exit_code, _ = _invoke(app, ["date", "--target-date", "2026-01-01"])

    assert exit_code != 0


def test_tribunal_year_arguments_are_positional_only() -> None:
    from causaganha.consolidate.cli import app

    exit_code, _ = _invoke(app, ["tribunal-year", "--tribunal", "TJSP", "--year", "2026"])

    assert exit_code != 0


def test_dry_run_has_a_negatable_pair() -> None:
    """The original Typer option had no explicit name, so Typer auto-generated
    --dry-run/--no-dry-run; Cyclopts does the same for an unnamed boolean."""
    from causaganha.consolidate.cli import app

    exit_code, output = _invoke(app, ["date", "2026-01-01", "--no-dry-run", "--help"])

    assert exit_code == 0, output


def test_force_has_no_negatable_pair() -> None:
    """The original Typer option passed an explicit "--force" string, which
    suppressed the --no-force pair. Cyclopts needs `negative=[]` for the
    same effect (RFC 0013 Fase 4 finding) -- this guards against silently
    regaining --no-force."""
    from causaganha.consolidate.cli import app

    exit_code, _ = _invoke(app, ["reconsolidate", "--no-force"])

    assert exit_code != 0


def test_missing_required_argument_is_a_usage_error() -> None:
    """Cyclopts' own parse-error exit code (1) differs from Click/Typer's (2)
    for this class of error -- a real, documented framework difference (RFC
    0013 Fase 4), not a regression; this test locks in the new value rather
    than assuming the old one still applies."""
    from causaganha.consolidate.cli import app

    exit_code, _ = _invoke(app, ["date"])

    assert exit_code == 1
