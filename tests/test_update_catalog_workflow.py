"""``update-catalog.yml`` must require every source that actually publishes data.

``RECONCILE_EXPECTED_SOURCES`` in the "Reconcile processos" step controls
which sources' *unavailability* fails the catalog run (see
``scripts/reconcile_processos.py``'s module docstring). JURIS and DataJud
were deliberately excluded because, when the step was written, no
``tjro-juris-*``/``datajud-*`` IA items existed yet — requiring them would
have hard-failed every catalog run for a source that had genuinely never
published anything (see issue #924, section 3.1).

That is no longer true: ``tjro-juris-{year}`` items (e.g. ``tjro-juris-2023``)
and ``datajud-{tribunal}`` items (e.g. ``datajud-tjro``) now exist on the
Internet Archive with real, well-formed parquet data — verified live against
the schemas ``scripts/reconcile_processos.py`` actually reads. Leaving them
out of ``RECONCILE_EXPECTED_SOURCES`` means a *real* regression in either
upload pipeline would degrade ``indice_processual.parquet`` silently: the
step would keep exiting 0, only emitting a `::warning` easy to miss instead
of the `::error` that fails the run — exactly the "silent risk" issue #924
warns about.
"""

from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "update-catalog.yml"

_RECONCILE_STEP_NAME = "Reconcile processos (DJEN x JURIS x STJ x DataJud)"
_GENERATE_CATALOG_STEP_NAME = "Generate reconstructible catalog"


def _reconcile_expected_sources() -> set[str]:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["catalog"]["steps"]
    (reconcile_step,) = (step for step in steps if step.get("name") == _RECONCILE_STEP_NAME)
    raw = reconcile_step["env"]["RECONCILE_EXPECTED_SOURCES"]
    return {source.strip() for source in raw.split(",") if source.strip()}


def test_reconcile_expects_every_source_now_publishing_data() -> None:
    assert _reconcile_expected_sources() == {"djen", "juris", "stj", "datajud"}


def _generate_catalog_run_script() -> str:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["catalog"]["steps"]
    (step,) = (s for s in steps if s.get("name") == _GENERATE_CATALOG_STEP_NAME)
    return step["run"]


def test_generate_catalog_step_invokes_ia_through_uv_run() -> None:
    """``ia`` is only on PATH inside the project's uv-managed venv.

    ``./.github/actions/setup`` runs ``uv sync``, which installs the
    ``internetarchive`` package's ``ia`` console script into ``.venv/bin`` —
    it never adds that directory to ``$GITHUB_PATH``. Every run since this
    step started calling a bare ``ia upload`` (introduced by #968) has
    actually failed with ``ia: command not found`` (exit 127) — see runs
    #772-#774 of ``update-catalog.yml`` on main. The sibling step
    "Reconcile processos" and ``bootstrap-corpus.yml`` both correctly
    prefix the same binary with ``uv run``.
    """
    run_script = _generate_catalog_run_script()

    assert "uv run ia upload causaganha-catalog" in run_script


def _job_timeout_minutes() -> int:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    return workflow["jobs"]["catalog"]["timeout-minutes"]


# Evidence from run #775 (the push that landed #1040's "uv run ia upload"
# fix): https://github.com/franklinbaldo/causaganha/actions/runs/33724279016
# "Generate reconstructible catalog" alone ran 06:40:30-06:52:09 (~11m40s);
# "Reconcile processos" then started at 06:52:09 but was killed mid-run
# (conclusion "cancelled") when the job hit its 15-minute timeout at
# 06:55:15. #1040 fixed the "ia: command not found" failure that had
# prevented Reconcile from ever starting, but that only exposed the next
# blocker: the two I/O-heavy steps already exceed the job's time budget on
# their own, so Reconcile has still never completed. 45 minutes leaves ~30
# minutes of headroom beyond the observed catalog-step duration for
# Reconcile plus the remaining steps to finish.
_MIN_JOB_TIMEOUT_MINUTES = 45


def test_job_timeout_leaves_room_for_reconcile_to_finish() -> None:
    assert _job_timeout_minutes() >= _MIN_JOB_TIMEOUT_MINUTES
