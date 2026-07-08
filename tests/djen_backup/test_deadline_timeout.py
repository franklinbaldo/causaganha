from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import pytest

from djen_backup import archive as archive_module
from djen_backup import engine as engine_module
from djen_backup.manifest import SyncManifest


@pytest.mark.asyncio
async def test_run_sync_deadline_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """The sync engine should exit gracefully when the deadline has passed."""

    async def _load_from_ia(self: SyncManifest) -> int:
        return 0

    async def _fetch_ia_existing(
        client,
        tribunal: str,
        year: int,
    ) -> dict[date, str]:
        return {}

    async def _get_tribunal_list(client, url: str) -> list[str]:
        return ["TJSP"]

    async def _get_caderno_url(client, base_url, tribunal, d):
        from djen_backup.djen import DJENNotFoundError

        raise DJENNotFoundError(status_code=404, reason="Not Found")

    monkeypatch.setattr(SyncManifest, "load_from_ia", _load_from_ia)
    monkeypatch.setattr(engine_module, "get_tribunal_list", _get_tribunal_list)
    monkeypatch.setattr(archive_module, "fetch_ia_existing", _fetch_ia_existing)
    monkeypatch.setattr(engine_module, "get_caderno_url", _get_caderno_url)

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "test-manifest.csv"

        config = engine_module.SyncConfig(
            start_date=date(2024, 1, 3),
            lower_bound=date(2024, 1, 1),
            tribunal="TJSP",
            deadline_minutes=-1,  # Set deadline to negative so it times
            # out in the past
            max_items=0,
            workers=1,
            manifest_file=manifest_path,
            djen_proxy_url="https://example.invalid",
            ia_auth="LOW dry-run:dry-run",
            dry_run=True,
        )

        # It should exit gracefully and quickly without hanging
        exit_code, _summary = await engine_module.run_sync(config)
        assert exit_code == 0
