"""``deployment/`` must not carry phantom infra for a runtime the project doesn't use.

GitHub Actions is the actual deployed runtime (CLAUDE.md; scheduled workflows
under ``.github/workflows/``). ``deployment/cron/causaganha-export.cron`` and
``deployment/systemd/causaganha-export.{service,timer}`` target
``/opt/causaganha`` and ``scripts/daily_export.py`` — a host layout and a
script that exist nowhere else in this repository, and are installed by no
workflow or doc. See issue #924 (Ox Alpha review, section 3.3).
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEPLOYMENT_DIR = REPO_ROOT / "deployment"

_PHANTOM_PATHS = (
    DEPLOYMENT_DIR / "cron",
    DEPLOYMENT_DIR / "systemd",
)


def test_phantom_cron_and_systemd_deploy_infra_is_removed() -> None:
    surviving = [str(p.relative_to(REPO_ROOT)) for p in _PHANTOM_PATHS if p.exists()]
    assert surviving == []


def test_daily_export_script_they_target_does_not_exist() -> None:
    assert not (REPO_ROOT / "scripts" / "daily_export.py").exists()
