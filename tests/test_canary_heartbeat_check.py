"""Tests for the standalone canary.yml watchdog entrypoint (#924 3.4 / #892)."""

from __future__ import annotations

from causaganha_mcp.workflow_runs import WorkflowRunObservation
from scripts import canary_heartbeat_check


def _observation(**overrides: object) -> WorkflowRunObservation:
    defaults: dict[str, object] = {
        "workflow": "canary.yml",
        "observacao": "present",
        "ultima_tentativa": "2026-08-25T12:30:00Z",
        "ultimo_sucesso": "2026-08-25T12:34:00Z",
        "runs_observados": 5,
        "total_runs_reportado": 5,
        "janela_completa": True,
        "aviso": None,
    }
    defaults.update(overrides)
    return WorkflowRunObservation(**defaults)


def test_main_exits_zero_when_canary_recently_succeeded(monkeypatch) -> None:
    monkeypatch.setattr(
        canary_heartbeat_check, "observe_workflow_runs", lambda _workflow: _observation()
    )

    assert canary_heartbeat_check.main() == 0


def test_main_exits_one_when_canary_looks_dead(monkeypatch) -> None:
    monkeypatch.setattr(
        canary_heartbeat_check,
        "observe_workflow_runs",
        lambda _workflow: _observation(
            observacao="absent", ultima_tentativa=None, ultimo_sucesso=None
        ),
    )

    assert canary_heartbeat_check.main() == 1
