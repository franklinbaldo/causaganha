"""Test isolation for aggregate status network observers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _isolate_causaganha_status_clocks(request, monkeypatch):
    """Keep legacy aggregate-status tests deterministic after clock composition."""
    if not request.module.__name__.endswith("test_causaganha_status"):
        return

    import causaganha_mcp.tools.status as status_module

    monkeypatch.setattr(
        status_module.workflow_runs,
        "observe_workflow_runs",
        lambda workflow: SimpleNamespace(
            workflow=workflow,
            observacao="unknown",
            ultima_tentativa=None,
            ultimo_sucesso=None,
            aviso=None,
        ),
    )
    monkeypatch.setattr(
        status_module,
        "_published_object_clock",
        lambda _url: ("unknown", None, None),
    )
