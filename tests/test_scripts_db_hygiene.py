"""``scripts/db/`` must not carry phantom dbt tooling for a project that doesn't exist.

RFC 0006 (``docs/rfc/0006-poda-codigo-morto.md`` §3) records that
``dbt-duckdb`` left the dev dependency group because "não há projeto dbt no
repo" — yet ``scripts/db/reset_dbt_database.sh`` and
``scripts/db/monitor_dbt_run.py`` still target a ``dbt/`` project directory
that has never existed in this repository. See issue #924 (Ox Alpha review,
section 3.3).
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_phantom_dbt_scripts_directory_is_removed() -> None:
    assert not (REPO_ROOT / "scripts" / "db").exists()


def test_dbt_project_directory_they_target_does_not_exist() -> None:
    assert not (REPO_ROOT / "dbt").exists()
