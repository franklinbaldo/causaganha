"""Tests for the batched-drain mode (``djen_backup.drain``).

Covers ``SegmentWriter`` (append-only segment CSV), ``_drain_one`` (single-pair
flow: already-on-IA short-circuit, happy path, DJEN 404 skip, transport
error skip, ``ItemBusyError`` retry loop), and ``drain`` deadline behaviour.
"""

from __future__ import annotations

import asyncio
import time
from datetime import date
from typing import TYPE_CHECKING

import httpx
import pytest

from djen_backup import drain as drain_module
from djen_backup.archive import CircuitBreaker, ItemBusyError
from djen_backup.djen import DJENNotFoundError
from djen_backup.drain import _drain_one, drain
from djen_backup.segments import SEGMENT_HEADER, SegmentWriter


if TYPE_CHECKING:
    from pathlib import Path


# ── SegmentWriter ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delta_writer_appends_rows(tmp_path: Path) -> None:
    path = tmp_path / "delta.csv"
    writer = SegmentWriter(path)
    await writer.mark_uploaded("TJSP", date(2024, 1, 2))
    await writer.mark_uploaded("TJBA", date(2024, 1, 3))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == SEGMENT_HEADER
    assert len(lines) == 3
    assert lines[1].startswith("TJSP,2024-01-02,uploaded,")
    assert lines[2].startswith("TJBA,2024-01-03,uploaded,")
    assert writer.count == 2


# ── _drain_one ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_drain_one_skips_when_already_on_ia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(drain_module, "check_ia_file_exists", _ia_hit)
    monkeypatch.setattr(
        drain_module, "get_caderno_url", _async_raise(AssertionError("must not call"))
    )
    monkeypatch.setattr(drain_module, "download_zip", _async_raise(AssertionError("must not call")))
    monkeypatch.setattr(drain_module, "upload_zip", _async_raise(AssertionError("must not call")))

    writer = SegmentWriter(tmp_path / "delta.csv")
    await _drain_one(
        "TJSP",
        date(2024, 1, 2),
        dl_client=_FakeClient(),
        upload_client=_FakeClient(),
        djen_proxy_url="https://djen.example",
        breaker=CircuitBreaker(),
        delta_writer=writer,
    )

    assert writer.count == 1


@pytest.mark.asyncio
async def test_drain_one_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_zip = tmp_path / "raw.zip"
    raw_zip.write_bytes(b"PK\x03\x04")

    monkeypatch.setattr(drain_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(drain_module, "get_caderno_url", _async_return("https://example/zip"))
    monkeypatch.setattr(drain_module, "download_zip", _async_return(raw_zip))
    monkeypatch.setattr(drain_module, "upload_zip", _ia_hit)

    writer = SegmentWriter(tmp_path / "delta.csv")
    await _drain_one(
        "TJSP",
        date(2024, 1, 2),
        dl_client=_FakeClient(),
        upload_client=_FakeClient(),
        djen_proxy_url="https://djen.example",
        breaker=CircuitBreaker(),
        delta_writer=writer,
    )

    assert writer.count == 1
    assert not raw_zip.exists()  # cleaned up by finally


@pytest.mark.asyncio
async def test_drain_one_swallows_djen_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(drain_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(
        drain_module,
        "get_caderno_url",
        _async_raise(DJENNotFoundError(status_code=404, reason="missing")),
    )

    writer = SegmentWriter(tmp_path / "delta.csv")
    await _drain_one(
        "TJSP",
        date(2024, 1, 2),
        dl_client=_FakeClient(),
        upload_client=_FakeClient(),
        djen_proxy_url="https://djen.example",
        breaker=CircuitBreaker(),
        delta_writer=writer,
    )

    assert writer.count == 0  # no upload happened
    # The verified absence is recorded as an event with the raw HTTP code —
    # never a derived category in djen_raw, never a bare 200.
    assert writer.absent_count == 1
    body = (tmp_path / "delta.csv").read_text(encoding="utf-8")
    assert "TJSP,2024-01-02,,absent,404," in body


@pytest.mark.asyncio
async def test_drain_one_swallows_transport_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(drain_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(
        drain_module,
        "get_caderno_url",
        _async_raise(httpx.ConnectError("network down")),
    )

    writer = SegmentWriter(tmp_path / "delta.csv")
    await _drain_one(
        "TJSP",
        date(2024, 1, 2),
        dl_client=_FakeClient(),
        upload_client=_FakeClient(),
        djen_proxy_url="https://djen.example",
        breaker=CircuitBreaker(),
        delta_writer=writer,
    )

    assert writer.count == 0  # silent skip


@pytest.mark.asyncio
async def test_drain_one_retries_busy_then_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_zip = tmp_path / "raw.zip"
    raw_zip.write_bytes(b"PK\x03\x04")

    attempts: list[int] = []

    async def _upload(*_args: object, **_kwargs: object) -> bool:
        attempts.append(1)
        if len(attempts) < 3:
            raise ItemBusyError("djen-tjsp-2024")  # noqa: EM101
        return True

    monkeypatch.setattr(drain_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(drain_module, "get_caderno_url", _async_return("https://example/zip"))
    monkeypatch.setattr(drain_module, "download_zip", _async_return(raw_zip))
    monkeypatch.setattr(drain_module, "upload_zip", _upload)

    writer = SegmentWriter(tmp_path / "delta.csv")
    await _drain_one(
        "TJSP",
        date(2024, 1, 2),
        dl_client=_FakeClient(),
        upload_client=_FakeClient(),
        djen_proxy_url="https://djen.example",
        breaker=CircuitBreaker(),
        delta_writer=writer,
    )

    assert len(attempts) == 3  # two busy + one success
    assert writer.count == 1


# ── drain deadline ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_drain_respects_deadline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """drain() must finish within ~deadline_seconds even when workers are slow."""

    async def _slow_download(*_a: object, **_kw: object) -> object:
        await asyncio.sleep(60)  # simulates a hung download
        return None  # unreachable in practice

    monkeypatch.setattr(drain_module, "check_ia_file_exists", _ia_miss)
    monkeypatch.setattr(drain_module, "get_caderno_url", _async_return("https://x/z"))
    monkeypatch.setattr(drain_module, "download_zip", _slow_download)
    monkeypatch.setattr(drain_module, "upload_zip", _ia_hit)
    monkeypatch.setattr(drain_module, "upload_delta", _async_return_false)

    # Patch fetch_pending_batch to return two fake entries
    def _fake_batch(*_a: object, **_kw: object) -> list[tuple[str, date]]:
        return [("TJSP", date(2024, 1, 1)), ("TJBA", date(2024, 1, 2))]

    monkeypatch.setattr(drain_module, "fetch_pending_batch", _fake_batch)

    # Patch duckdb.connect so we don't need real DuckDB httpfs
    import duckdb

    class _FakeDuck:
        def execute(self, *_a: object) -> _FakeDuck:
            return self

    monkeypatch.setattr(duckdb, "connect", _FakeDuck)

    deadline_seconds = 0.5
    t0 = time.monotonic()
    await drain(
        workers=2,
        batch_size=10,
        deadline_seconds=deadline_seconds,
        djen_proxy_url="https://djen.example",
        ia_auth="key:secret",
    )
    elapsed = time.monotonic() - t0

    # Should finish well before a hypothetical 18-minute GHA timeout;
    # give 5x margin to account for CI jitter, but definitely not 60 s.
    assert elapsed < deadline_seconds * 5 + 2, f"drain took {elapsed:.1f}s — deadline not respected"


# ── helpers ──────────────────────────────────────────────────────────


class _FakeClient:
    """Stand-in httpx.AsyncClient — drain helpers are monkeypatched."""


async def _ia_hit(*_args: object, **_kwargs: object) -> bool:
    return True


async def _ia_miss(*_args: object, **_kwargs: object) -> bool:
    return False


async def _async_return_false(*_args: object, **_kwargs: object) -> bool:
    return False


async def _upload_succeeds(*_args: object, **_kwargs: object) -> bool:
    return True


def _async_return(value: object):  # type: ignore[no-untyped-def]
    async def _fn(*_args: object, **_kwargs: object) -> object:
        return value

    return _fn


def _async_raise(exc: BaseException):  # type: ignore[no-untyped-def]
    async def _fn(*_args: object, **_kwargs: object) -> object:
        raise exc

    return _fn
