"""Framework-neutral argv→semantic-config contract harness (RFC 0013).

Exercises each CLI through Typer's `CliRunner` (real argv parsing + real
dispatch) and observes what the *mocked service-layer call* actually
received. Never inspects Click internals — no `get_command`,
`make_context`, `opts`/`secondary_opts`, `param.type`. That introspection
disappears the moment the CLI moves to Cyclopts; this harness's `check`
functions do not, because they only ever look at plain Python values
(dataclasses, lists, strings) captured at the service boundary.

When Fase 4 swaps Typer for Cyclopts, only `run_case`'s `CliRunner.invoke`
call needs to change (or grow an adapter) — every `CliContractCase` and its
`check` function is reused verbatim as the acceptance gate.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from typer.testing import CliRunner


if TYPE_CHECKING:
    from collections.abc import Callable

_runner = CliRunner()

# Credential env vars read by the four packages' service layers — always
# cleared before a case runs (then re-applied from `case.env`) so a case's
# result never depends on what happens to be set in the ambient shell.
_CREDENTIAL_ENV_VARS = (
    "IA_ACCESS_KEY",
    "IA_SECRET_KEY",
    "IAS3_ACCESS_KEY",
    "IAS3_SECRET_KEY",
)


@dataclass
class RecordedCall:
    """A single recorded invocation of a mocked service function."""

    args: tuple
    kwargs: dict


class _Recorder:
    """Records calls to a service function (sync or async), returning a fixed value."""

    def __init__(self, return_value: Any) -> None:
        self.calls: list[RecordedCall] = []
        self.return_value = return_value

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(RecordedCall(args=args, kwargs=kwargs))
        return self.return_value

    async def async_call(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(RecordedCall(args=args, kwargs=kwargs))
        return self.return_value


@dataclass
class MockSpec:
    """Where to patch, and what the fake should return."""

    path: str
    return_value: Any = None
    is_async: bool = False


@dataclass
class CliContractCase:
    """One argv → semantic-config contract case.

    ``mocks`` keys are arbitrary labels used by ``check`` to find the
    relevant recorded calls — conventionally ``"main"`` for the primary
    business call the workflow cares about, plus whatever plumbing (e.g.
    proxy URL resolution) a specific case wants to inspect too.
    """

    label: str
    app_path: str
    argv: list[str]
    mocks: dict[str, MockSpec] = field(default_factory=dict)
    check: Callable[[dict[str, list[RecordedCall]]], None] | None = None
    expected_exit_code: int = 0
    env: dict[str, str] = field(default_factory=dict)


def run_case(case: CliContractCase, monkeypatch: Any) -> None:
    """Execute *case* against the real CLI and assert exit code + semantic config."""
    module = importlib.import_module(case.app_path)
    app = module.app

    for name in _CREDENTIAL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    for key, value in case.env.items():
        monkeypatch.setenv(key, value)

    recorders: dict[str, _Recorder] = {}
    for name, spec in case.mocks.items():
        recorder = _Recorder(return_value=spec.return_value)
        recorders[name] = recorder
        monkeypatch.setattr(spec.path, recorder.async_call if spec.is_async else recorder)

    result = _runner.invoke(app, case.argv)

    assert result.exit_code == case.expected_exit_code, (
        f"{case.label}: exit_code {result.exit_code} != {case.expected_exit_code}\n"
        f"output:\n{result.output}"
    )

    if case.check is not None:
        case.check({name: r.calls for name, r in recorders.items()})
