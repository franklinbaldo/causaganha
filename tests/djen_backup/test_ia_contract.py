from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx
import pytest

from djen_backup import archive as archive_module
from djen_backup import engine as engine_module
from djen_backup.archive import fetch_ia_existing, get_ia_item_id, get_ia_item_tribunal
from djen_backup.inventory import ZipInventory


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


def test_inventory_url_matches_ia_contract_for_hyphenated_tribunal() -> None:
    assert ZipInventory._url("TRE-SP", date(2024, 3, 15)) == (
        "https://archive.org/download/djen-tre-sp-2024/djen-2024-03-15-TRE-SP.zip"
    )


def test_item_id_round_trip_preserves_hyphenated_tribunal() -> None:
    item_id = get_ia_item_id("TRE-SP", date(2024, 1, 2))
    assert item_id == "djen-tre-sp-2024"
    assert get_ia_item_tribunal(item_id) == "TRE-SP"


def test_item_id_parser_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        get_ia_item_tribunal("backup-djen-2024-01-01")


@pytest.mark.asyncio
async def test_run_sync_respects_max_items_per_tribunal(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[date] = []

    async def _load_from_ia(self: ZipInventory) -> int:
        return 0

    async def _load_from_snapshot(self: ZipInventory) -> int:
        return 0

    async def _fetch_ia_existing(
        client: httpx.AsyncClient,
        tribunal: str,
        year: int,
    ) -> dict[date, str]:
        return {}

    async def _download_state_from_ia(filename: str) -> dict | None:
        return None

    async def _get_tribunal_list(client: httpx.AsyncClient, url: str) -> list[str]:
        return ["TJSP"]

    async def _download_to_staging(
        client: httpx.AsyncClient,
        tribunal: str,
        d: date,
        config: engine_module.SyncConfig,
        state: engine_module.SyncState,
        inventory: ZipInventory,
        summary: engine_module.SyncSummary,
    ) -> str:
        calls.append(d)
        await summary.inc_hit()
        return "hit"

    monkeypatch.setattr(ZipInventory, "load_from_ia", _load_from_ia)
    monkeypatch.setattr(ZipInventory, "load_from_disk", lambda self: 0)
    monkeypatch.setattr(ZipInventory, "load_from_snapshot", _load_from_snapshot)
    monkeypatch.setattr(engine_module, "download_state_from_ia", _download_state_from_ia)
    monkeypatch.setattr(engine_module, "get_tribunal_list", _get_tribunal_list)
    monkeypatch.setattr(archive_module, "fetch_ia_existing", _fetch_ia_existing)
    monkeypatch.setattr(engine_module, "download_to_staging", _download_to_staging)

    config = engine_module.SyncConfig(
        start_date=date(2024, 1, 3),
        lower_bound=date(2024, 1, 1),
        tribunal="TJSP",
        deadline_minutes=1,
        max_items=1,
        workers=1,
        state_file=None,
        djen_proxy_url="https://example.invalid",
        ia_auth="LOW dry-run:dry-run",
        dry_run=True,
    )

    exit_code = await engine_module.run_sync(config)

    assert exit_code == 0
    assert calls == [date(2024, 1, 3)]


@pytest.mark.asyncio
async def test_single_day_targeted_run_ignores_absent_inventory(monkeypatch: pytest.MonkeyPatch) -> None:
    inventory = ZipInventory()
    await inventory.add_absent("TRF3", date(2024, 12, 26))
    state = engine_module.SyncState()
    await state.get_or_init("TRF3", date(2024, 12, 26))
    summary = engine_module.SyncSummary()

    calls: list[date] = []

    async def _get_caderno_url(
        client: httpx.AsyncClient,
        base_url: str,
        tribunal: str,
        d: date,
    ) -> str:
        calls.append(d)
        return "https://example.invalid/fake.zip"

    async def _download_zip(client: httpx.AsyncClient, url: str) -> str:
        return str(Path("C:/tmp/fake.zip"))

    async def _to_thread(fn, *args):
        return fn(*args)

    monkeypatch.setattr(engine_module, "get_caderno_url", _get_caderno_url)
    monkeypatch.setattr(engine_module, "download_zip", _download_zip)
    monkeypatch.setattr(engine_module.shutil, "move", lambda src, dst: None)
    monkeypatch.setattr(engine_module.asyncio, "to_thread", _to_thread)

    config = engine_module.SyncConfig(
        start_date=date(2024, 12, 26),
        lower_bound=date(2024, 12, 26),
        tribunal="TRF3",
        deadline_minutes=1,
        max_items=1,
        workers=1,
        state_file=None,
        djen_proxy_url="https://example.invalid",
        ia_auth="LOW dry-run:dry-run",
        dry_run=False,
    )

    async with httpx.AsyncClient() as client:
        result = await engine_module.download_to_staging(
            client, "TRF3", date(2024, 12, 26), config, state, inventory, summary
        )

    assert result == "staged"
    assert calls == [date(2024, 12, 26)]
