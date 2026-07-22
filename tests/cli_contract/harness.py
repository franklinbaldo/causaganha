"""Framework-neutral argv→semantic-config contract harness (RFC 0013).

Exercises each CLI through its real `App` (real argv parsing + real
dispatch) and observes what the *mocked service-layer call* actually
received. Never inspects framework internals — no Click's `get_command`,
`make_context`, `opts`/`secondary_opts`, `param.type`, and no Cyclopts
equivalent either. This harness's `check` functions only ever look at plain
Python values (dataclasses, lists, strings) captured at the service
boundary, so they survived the Fase 4 Typer→Cyclopts swap verbatim — only
`run_case`'s invocation adapter (`_invoke`, below) changed, exactly as
RFC 0013 §Fase 4 planned.
"""

from __future__ import annotations

import contextlib
import importlib
import io
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from cyclopts.exceptions import CycloptsError


if TYPE_CHECKING:
    from collections.abc import Callable

    from cyclopts import App

# Cyclopts' own default exit code for a usage error (bad option, unknown
# command, ...) is 1 — confirmed by reading `cyclopts/core.py` (`sys.exit(1)`
# is hardcoded on the parse-error path, not configurable via `App(...)`) and
# by direct experiment. This is DIFFERENT from Click/Typer's convention of
# exit code 2 for the same class of error, which the three usage-error cases
# in `test_semantic_argv_contract.py` were originally locked against in
# Fase 1. `_invoke` reports the real code Cyclopts produces (1) rather than
# forcing 2, and those three cases were updated to expect 1 — the contract
# gate's job is to catch a genuine behavior difference like this one, not
# paper over it with a harness that lies about what production does.
_USAGE_ERROR_EXIT_CODE = 1

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


def _invoke(app: App, argv: list[str]) -> tuple[int, str]:
    """Run *app* against *argv* like a real process would, without a real `sys.exit`.

    `exit_on_error=False` + `result_action="return_value"` gets the command's
    raw return value back instead of a `SystemExit` on success; a parse/usage
    error raises `CycloptsError` instead of exiting, caught here and mapped
    to the exit code Cyclopts' own default path would have produced. Output
    (both the command's own prints and Cyclopts' rich-rendered error panels)
    is captured for the assertion failure message, not inspected — this
    harness only ever asserts on exit code and mocked-call arguments.
    """
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = app(argv, exit_on_error=False, result_action="return_value")
    except CycloptsError:
        return _USAGE_ERROR_EXIT_CODE, buf.getvalue()
    except SystemExit as exc:
        # `exit_on_error`/`result_action` only govern Cyclopts' own parsing-
        # error path — a command function that raises SystemExit itself
        # (business-logic failure, not a usage error) propagates straight
        # through regardless. Migrated commands should prefer `return N`
        # (see _invoke's `isinstance(result, int)` branch below), but this
        # is a safety net, not the intended path.
        return exc.code or 0, buf.getvalue()
    if isinstance(result, int):
        return result, buf.getvalue()
    return 0, buf.getvalue()


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

    exit_code, output = _invoke(app, case.argv)

    assert exit_code == case.expected_exit_code, (
        f"{case.label}: exit_code {exit_code} != {case.expected_exit_code}\noutput:\n{output}"
    )

    if case.check is not None:
        case.check({name: r.calls for name, r in recorders.items()})
