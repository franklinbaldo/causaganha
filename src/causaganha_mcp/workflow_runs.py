"""Bounded factual observation of GitHub Actions workflow clocks.

The health contract in #892 distinguishes *attempt*, *successful execution* and
*publication*.  This module observes only the first two clocks.  It deliberately
does not derive freshness or a healthy/stale verdict, and it does not use a
GitHub token: the repository and workflows are public.
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal

import httpx
from pydantic import BaseModel, Field


_REPOSITORY = "franklinbaldo/causaganha"
_ELIGIBLE_EVENTS = frozenset({"schedule", "workflow_dispatch"})
_DEFAULT_LIMIT = 100
_DEFAULT_TIMEOUT = 5.0


class WorkflowRunObservation(BaseModel):
    """Factual clocks observed in a bounded GitHub Actions run window."""

    workflow: str = Field(description="Workflow path declared by the Pipeline relation.")
    observacao: Literal["present", "absent", "unknown", "unavailable"] = Field(
        description=(
            "present when an eligible schedule/workflow_dispatch run was observed; absent only "
            "when GitHub reports no runs at all; unknown when the bounded window cannot establish "
            "whether an eligible run exists; unavailable when GitHub could not be verified."
        )
    )
    ultima_tentativa: str | None = Field(
        default=None,
        description="Start/creation timestamp of the newest observed eligible run.",
    )
    ultimo_sucesso: str | None = Field(
        default=None,
        description="Completion timestamp of the newest observed eligible run with conclusion=success.",
    )
    runs_observados: int = Field(ge=0, description="Number of runs inspected in the bounded window.")
    total_runs_reportado: int | None = Field(
        default=None,
        ge=0,
        description="GitHub total_count when the response exposes it.",
    )
    janela_completa: bool = Field(
        description="True only when the inspected page covers every run GitHub reports for the workflow."
    )
    aviso: str | None = Field(default=None, description="Boundary/transport caveat, when needed.")


def _run_timestamp(run: dict[str, object], *fields: str) -> str | None:
    for field in fields:
        value = run.get(field)
        if isinstance(value, str) and value:
            return value
    return None


def _newest_timestamp(runs: list[dict[str, object]], *fields: str) -> str | None:
    values = [value for run in runs if (value := _run_timestamp(run, *fields))]
    return max(values, default=None)


def observe_workflow_runs(
    workflow: str,
    *,
    client: httpx.Client | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> WorkflowRunObservation:
    """Observe attempt/success clocks without turning them into a health verdict.

    One bounded request is used per workflow.  ``schedule`` and
    ``workflow_dispatch`` are the only events that count because that is the
    semantics frozen by #927.  If the first ``limit`` runs contain no eligible
    event while older runs exist, the answer is ``unknown`` rather than a false
    ``absent``.
    """
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    workflow_name = PurePosixPath(workflow).name
    url = f"https://api.github.com/repos/{_REPOSITORY}/actions/workflows/{workflow_name}/runs"
    owned_client = client is None
    resolved = client or httpx.Client(timeout=_DEFAULT_TIMEOUT, follow_redirects=True)
    try:
        response = resolved.get(
            url,
            params={"per_page": limit, "page": 1},
            headers={"Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return WorkflowRunObservation(
            workflow=workflow,
            observacao="unavailable",
            runs_observados=0,
            janela_completa=False,
            aviso=f"Não foi possível verificar os runs públicos do workflow: {exc}",
        )
    finally:
        if owned_client:
            resolved.close()

    raw_runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(raw_runs, list):
        return WorkflowRunObservation(
            workflow=workflow,
            observacao="unavailable",
            runs_observados=0,
            janela_completa=False,
            aviso="GitHub respondeu sem a lista workflow_runs esperada.",
        )

    runs = [run for run in raw_runs if isinstance(run, dict)]
    total_raw = payload.get("total_count") if isinstance(payload, dict) else None
    total = total_raw if isinstance(total_raw, int) and total_raw >= 0 else None
    complete = total is not None and total <= len(runs)

    if total == 0 and not runs:
        return WorkflowRunObservation(
            workflow=workflow,
            observacao="absent",
            runs_observados=0,
            total_runs_reportado=0,
            janela_completa=True,
            aviso="GitHub não registra runs para este workflow.",
        )

    eligible = [run for run in runs if run.get("event") in _ELIGIBLE_EVENTS]
    if not eligible:
        caveat = (
            "Nenhum run schedule/workflow_dispatch apareceu na janela completa."
            if complete
            else "Nenhum run schedule/workflow_dispatch apareceu na janela limitada; runs mais antigos podem existir."
        )
        return WorkflowRunObservation(
            workflow=workflow,
            observacao="unknown",
            runs_observados=len(runs),
            total_runs_reportado=total,
            janela_completa=complete,
            aviso=caveat,
        )

    successful = [run for run in eligible if run.get("conclusion") == "success"]
    last_attempt = _newest_timestamp(eligible, "run_started_at", "created_at")
    last_success = _newest_timestamp(successful, "updated_at", "run_started_at", "created_at")
    warning = None
    if last_success is None and not complete:
        warning = (
            "Há tentativa elegível na janela, mas nenhum sucesso nela; um sucesso anterior pode existir fora da janela limitada."
        )

    return WorkflowRunObservation(
        workflow=workflow,
        observacao="present",
        ultima_tentativa=last_attempt,
        ultimo_sucesso=last_success,
        runs_observados=len(runs),
        total_runs_reportado=total,
        janela_completa=complete,
        aviso=warning,
    )
