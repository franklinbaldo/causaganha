"""Tests for the upload worker item handler.

Covers the extracted ``_process_upload_item`` so we exercise the re-queue,
saturated-queue drop, success, fail-fast, and already-on-IA branches without
spinning up the full pipeline.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import TYPE_CHECKING

import httpx
import pytest

from djen_backup import engine as engine_module
from djen_backup.archive import ItemBusyError
from djen_backup.circuit_breaker import CircuitBreaker
from djen_backup.engine import StagedItem, SyncSummary, _process_upload_item
from djen_backup.manifest import SyncManifest


if TYPE_CHECKING:
    from pathlib import Path


def _staged(
    tmp_path: Path,
    item_id: str = "djen-tjsp-2024",
    d: date = date(2024, 1, 2),
) -> StagedItem:
    zip_path = tmp_path / f"djen-{d.isoformat()}-{item_id.split('-')[1].upper()}.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    return StagedItem(item_id=item_id, d=d, tribunal="TJSP", path=zip_path)


@pytest.fixture
def manifest() -> SyncManifest:
    m = SyncManifest()
    m.build(["TJSP"], date(2024, 1, 1), date(2024, 1, 5))
    return m


@pytest.mark.asyncio
async def test_already_on_ia_marks_uploaded_and_skips_upload(
    manifest: SyncManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine_module, "check_ia_file_exists", _ia_hit)
    monkeypatch.setattr(
        engine_module, "upload_zip", _async_raise(AssertionError("must not be called"))
    )

    item = _staged(tmp_path)
    summary = SyncSummary()
    queue: asyncio.Queue[StagedItem | None] = asyncio.Queue(maxsize=4)

    await _process_upload_item(
        item,
        upload_client=_FakeClient(),
        upload_queue=queue,
        manifest=manifest,
        summary=summary,
        circuit_breaker=CircuitBreaker(),
        abort_event=asyncio.Event(),
        fail_fast=True,
        observer=None,
    )

    assert summary.uploads == 1
    assert manifest.get_status("TJSP", date(2024, 1, 2)).ia_status == "uploaded"
    assert not item.path.exists()


@pytest.mark.asyncio
async def test_busy_item_is_requeued(
    manifest: SyncManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(engine_module, "upload_zip", _async_raise(ItemBusyError("djen-tjsp-2024")))

    item = _staged(tmp_path)
    queue: asyncio.Queue[StagedItem | None] = asyncio.Queue(maxsize=4)
    summary = SyncSummary()

    await _process_upload_item(
        item,
        upload_client=_FakeClient(),
        upload_queue=queue,
        manifest=manifest,
        summary=summary,
        circuit_breaker=CircuitBreaker(),
        abort_event=asyncio.Event(),
        fail_fast=True,
        observer=None,
    )

    assert queue.qsize() == 1
    assert queue.get_nowait() is item
    assert summary.uploads == 0
    assert item.path.exists()  # not unlinked — still pending


@pytest.mark.asyncio
async def test_busy_item_dropped_when_queue_saturated(
    manifest: SyncManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(engine_module, "upload_zip", _async_raise(ItemBusyError("djen-tjsp-2024")))

    item = _staged(tmp_path)
    # Pre-fill a maxsize=1 queue so the requeue can't fit.
    filler_dir = tmp_path / "filler"
    filler_dir.mkdir()
    queue: asyncio.Queue[StagedItem | None] = asyncio.Queue(maxsize=1)
    queue.put_nowait(_staged(filler_dir, "djen-tjba-2024", date(2024, 1, 3)))

    await _process_upload_item(
        item,
        upload_client=_FakeClient(),
        upload_queue=queue,
        manifest=manifest,
        summary=SyncSummary(),
        circuit_breaker=CircuitBreaker(),
        abort_event=asyncio.Event(),
        fail_fast=True,
        observer=None,
    )

    # The original filler is still there; our busy item was dropped (and unlinked).
    assert queue.qsize() == 1
    assert not item.path.exists()


@pytest.mark.asyncio
async def test_successful_upload_marks_manifest_and_unlinks(
    manifest: SyncManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(engine_module, "upload_zip", _upload_succeeds)

    item = _staged(tmp_path)
    summary = SyncSummary()

    await _process_upload_item(
        item,
        upload_client=_FakeClient(),
        upload_queue=asyncio.Queue(maxsize=4),
        manifest=manifest,
        summary=summary,
        circuit_breaker=CircuitBreaker(),
        abort_event=asyncio.Event(),
        fail_fast=True,
        observer=None,
    )

    assert summary.uploads == 1
    assert manifest.get_status("TJSP", date(2024, 1, 2)).ia_status == "uploaded"
    assert not item.path.exists()


@pytest.mark.asyncio
async def test_failed_upload_with_fail_fast_sets_abort(
    manifest: SyncManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(engine_module, "upload_zip", _upload_fails)

    item = _staged(tmp_path)
    abort_event = asyncio.Event()

    await _process_upload_item(
        item,
        upload_client=_FakeClient(),
        upload_queue=asyncio.Queue(maxsize=4),
        manifest=manifest,
        summary=SyncSummary(),
        circuit_breaker=CircuitBreaker(),
        abort_event=abort_event,
        fail_fast=True,
        observer=None,
    )

    assert abort_event.is_set()
    assert manifest.get_status("TJSP", date(2024, 1, 2)).ia_status != "uploaded"
    assert not item.path.exists()


@pytest.mark.asyncio
async def test_check_ia_exception_increments_error_sets_abort_and_preserves_file(
    manifest: SyncManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        engine_module,
        "check_ia_file_exists",
        _async_raise(httpx.ConnectError("network down")),
    )
    monkeypatch.setattr(
        engine_module, "upload_zip", _async_raise(AssertionError("must not be called"))
    )

    item = _staged(tmp_path)
    summary = SyncSummary()
    abort_event = asyncio.Event()

    await _process_upload_item(
        item,
        upload_client=_FakeClient(),
        upload_queue=asyncio.Queue(maxsize=4),
        manifest=manifest,
        summary=summary,
        circuit_breaker=CircuitBreaker(),
        abort_event=abort_event,
        fail_fast=True,
        observer=None,
    )

    assert summary.errors == 1
    assert abort_event.is_set()
    assert manifest.get_status("TJSP", date(2024, 1, 2)).ia_status != "uploaded"
    assert item.path.exists()


@pytest.mark.asyncio
async def test_upload_zip_exception_increments_error_sets_abort_and_preserves_file(
    manifest: SyncManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(
        engine_module,
        "upload_zip",
        _async_raise(httpx.ReadTimeout("upload timed out")),
    )

    item = _staged(tmp_path)
    summary = SyncSummary()
    abort_event = asyncio.Event()

    await _process_upload_item(
        item,
        upload_client=_FakeClient(),
        upload_queue=asyncio.Queue(maxsize=4),
        manifest=manifest,
        summary=summary,
        circuit_breaker=CircuitBreaker(),
        abort_event=abort_event,
        fail_fast=True,
        observer=None,
    )

    assert summary.errors == 1
    assert abort_event.is_set()
    assert manifest.get_status("TJSP", date(2024, 1, 2)).ia_status != "uploaded"
    assert item.path.exists()


@pytest.mark.asyncio
async def test_upload_exception_without_fail_fast_keeps_abort_unset(
    manifest: SyncManifest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(
        engine_module,
        "upload_zip",
        _async_raise(httpx.ConnectError("temporary network issue")),
    )

    item = _staged(tmp_path)
    summary = SyncSummary()
    abort_event = asyncio.Event()

    await _process_upload_item(
        item,
        upload_client=_FakeClient(),
        upload_queue=asyncio.Queue(maxsize=4),
        manifest=manifest,
        summary=summary,
        circuit_breaker=CircuitBreaker(),
        abort_event=abort_event,
        fail_fast=False,
        observer=None,
    )

    assert summary.errors == 1
    assert not abort_event.is_set()
    assert item.path.exists()


# ── helpers ──────────────────────────────────────────────────────────


class _FakeClient:
    """Stand-in httpx.AsyncClient — we monkey-patch the only methods we touch."""


async def _ia_hit(*_args: object, **_kwargs: object) -> bool:
    return True


async def _ia_miss(*_args: object, **_kwargs: object) -> bool:
    return False


async def _upload_succeeds(*_args: object, **_kwargs: object) -> bool:
    return True


async def _upload_fails(*_args: object, **_kwargs: object) -> bool:
    return False


def _async_raise(exc: BaseException):  # type: ignore[no-untyped-def]
    async def _fn(*_args: object, **_kwargs: object) -> object:
        raise exc

    return _fn
