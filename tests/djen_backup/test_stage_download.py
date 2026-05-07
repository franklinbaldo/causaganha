"""Unit tests for ``_stage_download``.

Covers happy path (download → move), DJENNotFoundError exhaustion after 3
retries, and the fact that non-retryable transport errors propagate without
being looped on.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import httpx
import pytest
from aiolimiter import AsyncLimiter

from djen_backup import engine as engine_module
from djen_backup.djen import DJENNotFoundError
from djen_backup.engine import _stage_download
from djen_backup.manifest import ManifestEntry


if TYPE_CHECKING:
    from pathlib import Path


def _entry(d: date = date(2024, 1, 2)) -> ManifestEntry:
    return ManifestEntry(tribunal="TJSP", date=d)


def _limiter() -> AsyncLimiter:
    return AsyncLimiter(max_rate=100, time_period=1)


@pytest.mark.asyncio
async def test_stage_download_moves_to_per_item_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_zip = tmp_path / "raw.zip"
    raw_zip.write_bytes(b"PK\x03\x04")

    async def _url(*_args: object, **_kwargs: object) -> str:
        return "https://example/zip"

    async def _dl(*_args: object, **_kwargs: object) -> Path:
        return raw_zip

    monkeypatch.setattr(engine_module, "get_caderno_url", _url)
    monkeypatch.setattr(engine_module, "download_zip", _dl)

    staging = tmp_path / "staging"

    staged = await _stage_download(
        _entry(),
        client=object(),  # type: ignore[arg-type]
        proxy_url="https://djen.example",
        djen_limiter=_limiter(),
        staging_dir=staging,
    )

    assert staged.item_id == "djen-tjsp-2024"
    assert staged.tribunal == "TJSP"
    assert staged.path == staging / "djen-tjsp-2024" / "djen-2024-01-02-TJSP.zip"
    assert staged.path.exists()
    assert not raw_zip.exists()  # moved, not copied


@pytest.mark.asyncio
async def test_stage_download_retries_djen_not_found_then_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    async def _url_flaky(*_args: object, **_kwargs: object) -> str:
        calls.append(1)
        if len(calls) < 2:
            raise DJENNotFoundError(status_code=404, reason="transient")
        return "https://example/zip"

    raw_zip = tmp_path / "raw.zip"
    raw_zip.write_bytes(b"PK\x03\x04")

    async def _dl(*_args: object, **_kwargs: object) -> Path:
        return raw_zip

    monkeypatch.setattr(engine_module, "get_caderno_url", _url_flaky)
    monkeypatch.setattr(engine_module, "download_zip", _dl)

    staged = await _stage_download(
        _entry(),
        client=object(),  # type: ignore[arg-type]
        proxy_url="https://djen.example",
        djen_limiter=_limiter(),
        staging_dir=tmp_path / "staging",
    )

    assert len(calls) == 2  # one retry
    assert staged.path.exists()


@pytest.mark.asyncio
async def test_stage_download_propagates_after_retry_exhaustion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _url_404(*_args: object, **_kwargs: object) -> str:
        raise DJENNotFoundError(status_code=404, reason="permanent")

    monkeypatch.setattr(engine_module, "get_caderno_url", _url_404)
    monkeypatch.setattr(engine_module, "download_zip", _async_unreachable_download_zip)

    with pytest.raises(DJENNotFoundError):
        await _stage_download(
            _entry(),
            client=object(),  # type: ignore[arg-type]
            proxy_url="https://djen.example",
            djen_limiter=_limiter(),
            staging_dir=tmp_path / "staging",
        )


@pytest.mark.asyncio
async def test_stage_download_does_not_retry_transport_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    async def _url_boom(*_args: object, **_kwargs: object) -> str:
        calls.append(1)
        raise httpx.HTTPError("502")  # noqa: EM101

    monkeypatch.setattr(engine_module, "get_caderno_url", _url_boom)
    monkeypatch.setattr(engine_module, "download_zip", _async_unreachable_download_zip)

    with pytest.raises(httpx.HTTPError):
        await _stage_download(
            _entry(),
            client=object(),  # type: ignore[arg-type]
            proxy_url="https://djen.example",
            djen_limiter=_limiter(),
            staging_dir=tmp_path / "staging",
        )

    assert len(calls) == 1  # tenacity only retries DJENNotFoundError


# ── helpers ──────────────────────────────────────────────────────────


async def _async_unreachable_download_zip(*_args: object, **_kwargs: object) -> object:
    msg = "download_zip should not be reached"
    raise AssertionError(msg)
