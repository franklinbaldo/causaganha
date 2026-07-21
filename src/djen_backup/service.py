"""Config→result service layer for ``djen-backup``, free of Typer/Rich (RFC 0013 Fase 2).

``__main__.py`` owns argv parsing and Rich rendering; this module owns the
actual work — resolving runtime config from the environment and driving the
sync engine — so it can be called from a future MCP tool or a different CLI
framework without dragging Typer/Rich along.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from djen_backup.credentials import get_ia_s3_auth
from djen_backup.engine import ManifestObserver, SyncConfig, SyncSummary, run_sync


if TYPE_CHECKING:
    from datetime import date


DJEN_DIRECT_URL = "https://comunicaapi.pje.jus.br"
DJEN_PROXY_FALLBACK_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"


class MissingCredentialsError(RuntimeError):
    """Internet Archive S3 credentials could not be resolved."""


@dataclass
class PipelineRunConfig:
    """Config for a single ``run_pipeline`` invocation."""

    start_date: date
    end_date: date
    lower_bound: date | None
    tribunal: str | None
    deadline_minutes: int
    max_items: int
    workers: int
    fail_fast: bool
    publish_live_status: bool
    skip_if_mostly_complete: bool
    use_proxy: bool
    upload_only: bool = False
    check_only: bool = False
    mode_label: str = "Full Sync"


def resolve_djen_url(*, use_proxy: bool) -> str:
    """Resolve the DJEN base URL to use, direct or proxied."""
    if use_proxy:
        return os.environ.get("DJEN_PROXY_URL", "").strip() or DJEN_PROXY_FALLBACK_URL
    return os.environ.get("DJEN_DIRECT_URL", "").strip() or DJEN_DIRECT_URL


def resolve_ia_auth() -> str:
    """Resolve the Internet Archive S3 auth header, or raise ``MissingCredentialsError``."""
    try:
        return get_ia_s3_auth()
    except RuntimeError as exc:
        raise MissingCredentialsError(str(exc)) from exc


async def run_pipeline(
    config: PipelineRunConfig,
    *,
    djen_url: str,
    ia_auth: str,
    observer: ManifestObserver | None = None,
) -> tuple[int, SyncSummary]:
    """Run the sync engine for *config* and return ``(exit_code, summary)``."""
    sync_config = SyncConfig(
        start_date=config.end_date,
        lower_bound=config.lower_bound,
        tribunal=config.tribunal,
        deadline_minutes=config.deadline_minutes,
        max_items=config.max_items,
        workers=config.workers,
        manifest_file=Path("data/sync-manifest.csv"),
        djen_proxy_url=djen_url,
        ia_auth=ia_auth,
        dry_run=False,
        fail_fast=config.fail_fast,
        publish_live_status=config.publish_live_status,
        skip_if_mostly_complete=config.skip_if_mostly_complete,
        check_only=config.check_only,
        upload_only=config.upload_only,
        observer=observer,
    )
    return await run_sync(sync_config)
