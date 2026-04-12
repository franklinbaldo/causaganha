from __future__ import annotations

from datetime import date

import httpx
import pytest

from djen_backup import archive as archive_module
from djen_backup import engine as engine_module
from djen_backup.archive import fetch_ia_existing, get_ia_item_id, get_ia_item_tribunal
from djen_backup.manifest import SyncManifest


@pytest.mark.asyncio
async def test_fetch_ia_existing_reads_tribunal_year_bucket(mock_api) -> None:
    mock_api.get("https://archive.org/metadata/djen-tre-sp-2024/files").respond(
        200,
        json={
            "result": [
                {"name": "djen-2024-03-15-TRE-SP.zip"},
                {"name": "README.txt"},
            ]
        },
    )

    async with httpx.AsyncClient() as client:
        existing = await fetch_ia_existing(client, "TRE-SP", 2024)

    assert existing == {date(2024, 3, 15): "uploaded"}


def test_manifest_url_matches_ia_contract_for_hyphenated_tribunal() -> None:
    assert SyncManifest._ia_url("TRE-SP", date(2024, 3, 15)) == (
        "https://archive.org/download/djen-tre-sp-2024/djen-2024-03-15-TRE-SP.zip"
    )


def test_item_id_round_trip_preserves_hyphenated_tribunal() -> None:
    item_id = get_ia_item_id("TRE-SP", date(2024, 1, 2))
    assert item_id == "djen-tre-sp-2024"
    assert get_ia_item_tribunal(item_id) == "TRE-SP"


def test_item_id_parser_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="Invalid IA item id"):
        get_ia_item_tribunal("backup-djen-2024-01-01")


def test_manifest_build_and_counts() -> None:
    m = SyncManifest()
    added = m.build(["TJSP", "TJBA"], date(2024, 1, 1), date(2024, 1, 3))
    assert added == 6  # 2 tribunals x 3 days
    counts = m.counts()
    assert counts.total == 6
    assert counts.unknown == 6
    assert counts.uploaded == 0


@pytest.mark.asyncio
async def test_manifest_mark_ia_uploaded() -> None:
    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 3))
    changed = await m.mark_ia_uploaded("TJSP", {date(2024, 1, 1), date(2024, 1, 2)})
    assert changed == 2
    counts = m.counts()
    assert counts.uploaded == 2
    assert counts.unknown == 1


@pytest.mark.asyncio
async def test_manifest_mark_djen_statuses() -> None:
    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 3))
    await m.mark_djen_available("TJSP", date(2024, 1, 1))
    await m.mark_djen_absent("TJSP", date(2024, 1, 2))
    counts = m.counts()
    assert counts.available == 1
    assert counts.absent == 1
    assert counts.unknown == 1


def test_manifest_csv_round_trip() -> None:
    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 2))
    csv = m.to_csv()

    m2 = SyncManifest()
    loaded = m2.load_from_csv(csv)
    assert loaded == 2
    assert m2.counts().total == 2


def test_manifest_legacy_csv_import() -> None:
    legacy = (
        "timestamp,tribunal,date,status,url\n"
        "2024-01-20T10:00:00,TJSP,2024-01-15,uploaded,https://archive.org/download/djen-tjsp-2024/djen-2024-01-15-TJSP.zip\n"
        "2024-01-20T10:01:00,TJSP,2024-01-16,absent,\n"
    )
    m = SyncManifest()
    loaded = m.load_from_csv(legacy)
    assert loaded == 1  # only uploaded is trusted from legacy
    counts = m.counts()
    assert counts.uploaded == 1
    assert counts.absent == 0  # absent from legacy is ignored


def test_manifest_entries_needing_upload() -> None:
    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 3))
    # Manually set statuses
    e1 = m._entries["TJSP/2024-01-01"]
    e1.djen_status = "available"

    e2 = m._entries["TJSP/2024-01-02"]
    e2.ia_status = "uploaded"

    entries = m.entries_needing_upload()
    assert len(entries) == 1
    assert entries[0].date == date(2024, 1, 1)


@pytest.mark.asyncio
async def test_run_sync_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dry run should build manifest and check availability but not download."""

    async def _load_from_ia(self: SyncManifest) -> int:
        return 0

    async def _fetch_ia_existing(
        client: httpx.AsyncClient,
        tribunal: str,
        year: int,
    ) -> dict[date, str]:
        return {date(2024, 1, 1): "uploaded", date(2024, 1, 2): "uploaded"}

    async def _get_tribunal_list(client: httpx.AsyncClient, url: str) -> list[str]:
        return ["TJSP"]

    async def _get_caderno_url(client, base_url, tribunal, d):
        from djen_backup.djen import DJENNotFoundError

        raise DJENNotFoundError(status_code=404, reason="Not Found")

    async def _upload_to_ia(self: SyncManifest, auth: str) -> bool:
        return True

    monkeypatch.setattr(SyncManifest, "load_from_ia", _load_from_ia)
    monkeypatch.setattr(SyncManifest, "upload_to_ia", _upload_to_ia)
    monkeypatch.setattr(engine_module, "get_tribunal_list", _get_tribunal_list)
    monkeypatch.setattr(archive_module, "fetch_ia_existing", _fetch_ia_existing)
    monkeypatch.setattr(engine_module, "get_caderno_url", _get_caderno_url)

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "test-manifest.csv"

        config = engine_module.SyncConfig(
            start_date=date(2024, 1, 3),
            lower_bound=date(2024, 1, 1),
            tribunal="TJSP",
            deadline_minutes=1,
            max_items=0,
            workers=1,
            manifest_file=manifest_path,
            djen_proxy_url="https://example.invalid",
            ia_auth="LOW dry-run:dry-run",
            dry_run=True,
        )

        exit_code = await engine_module.run_sync(config)
        assert exit_code == 0
