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


def _reconcile_expected_sources() -> set[str]:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["catalog"]["steps"]
    (reconcile_step,) = (step for step in steps if step.get("name") == _RECONCILE_STEP_NAME)
    raw = reconcile_step["env"]["RECONCILE_EXPECTED_SOURCES"]
    return {source.strip() for source in raw.split(",") if source.strip()}


def test_reconcile_expects_every_source_now_publishing_data() -> None:
    assert _reconcile_expected_sources() == {"djen", "juris", "stj", "datajud"}
