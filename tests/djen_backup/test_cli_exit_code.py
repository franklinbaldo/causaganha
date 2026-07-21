"""Regression tests for the exit-code propagation fix (RFC 0013 Fase 2).

Before the fix, the bare callback, `check` and `upload` all called
`_run_pipeline(...)` without doing anything with its return value — the
process exit code was always 0 regardless of whether the sync actually
succeeded. `_run_pipeline` itself is monkeypatched here (never invokes the
real sync engine — no network, no I/O) so these tests isolate exactly the
propagation logic: does the CLI's exit code match what `_run_pipeline`
returned?
"""

from __future__ import annotations

from typer.testing import CliRunner

from djen_backup.__main__ import app


runner = CliRunner()


def test_bare_callback_propagates_nonzero_exit_code(monkeypatch) -> None:
    monkeypatch.setattr("djen_backup.__main__._run_pipeline", lambda _config: 7)
    result = runner.invoke(app, [])
    assert result.exit_code == 7


def test_check_propagates_nonzero_exit_code(monkeypatch) -> None:
    monkeypatch.setattr("djen_backup.__main__._run_pipeline", lambda _config: 5)
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 5


def test_upload_propagates_nonzero_exit_code(monkeypatch) -> None:
    monkeypatch.setattr("djen_backup.__main__._run_pipeline", lambda _config: 3)
    result = runner.invoke(app, ["upload"])
    assert result.exit_code == 3


def test_bare_callback_propagates_zero_exit_code(monkeypatch) -> None:
    """Sanity check: the success path (0) isn't accidentally turned into a failure."""
    monkeypatch.setattr("djen_backup.__main__._run_pipeline", lambda _config: 0)
    result = runner.invoke(app, [])
    assert result.exit_code == 0
