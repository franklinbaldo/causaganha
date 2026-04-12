"""Sync engine: download DJEN ZIPs and upload to Internet Archive."""

from __future__ import annotations

import asyncio
import contextlib
import json
import math
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Protocol

import httpx
import structlog

from causaganha.pipeline.ia_s3 import create_upload_client
from djen_backup.archive import (
    CircuitBreaker,
    fetch_ia_existing,
    get_ia_item_id,
    put_ia_bytes,
    upload_zip,
)
from djen_backup.credentials import get_ia_s3_auth
from djen_backup.djen import DJENNotFoundError, download_zip, get_caderno_url
from djen_backup.inventory import ZipInventory
from djen_backup.tribunais import get_tribunal_list


if TYPE_CHECKING:
    from pathlib import Path

    from httpx import AsyncClient

log = structlog.get_logger()

# ── Constants ──────────────────────────────────────────────────────

VERSION_EXPECTED = 2
STOP_THRESHOLD = 60
IA_BACKFILL_STATE_FILENAME = "backfill-state.json"

DJEN_PROXY_FALLBACK_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"

# ── Protocols ──────────────────────────────────────────────────────


class SyncObserver(Protocol):
    """Interface for reporting sync progress to the UI."""

    def on_metadata_sync_start(self, tribunal: str, year: int) -> None: ...
    def on_metadata_sync_complete(self, tribunal: str, year: int, _found: int) -> None: ...
    def on_gaps_discovered(self, tribunal: str, year: int, count: int) -> None: ...
    def on_item_start(self, tribunal: str, d: date) -> None: ...
    def on_item_complete(
        self, tribunal: str, d: date, status: str, url: str | None = None
    ) -> None: ...
    def on_retry(
        self,
        tribunal: str,
        d: date,
        attempt: int,
        status: int,
        wait_s: float,
        body: str | None = None,
    ) -> None: ...
    def on_periodic_sync_start(self) -> None: ...
    def on_periodic_sync_complete(self) -> None: ...
    def on_batch_upload_start(self, item_id: str, count: int) -> None: ...
    def on_batch_upload_complete(self, item_id: str, count: int) -> None: ...


# ── State Management ───────────────────────────────────────────────


@dataclass
class TribunalProgress:
    """Backfill progress for a single tribunal."""

    cursor_date: date
    empty_streak: int = 0
    stopped: bool = False
    stop_boundary: date | None = None
    last_hit_date: date | None = None
    last_checked_at: str | None = None
    last_result: str | None = None  # "hit" | "empty" | "error"

    def to_dict(self) -> dict[str, object]:
        return {
            "cursor_date": self.cursor_date.isoformat(),
            "empty_streak": self.empty_streak,
            "stopped": self.stopped,
            "stop_boundary": self.stop_boundary.isoformat() if self.stop_boundary else None,
            "last_hit_date": self.last_hit_date.isoformat() if self.last_hit_date else None,
            "last_checked_at": self.last_checked_at,
            "last_result": self.last_result,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> TribunalProgress:
        cursor_raw = data.get("cursor_date")
        if not isinstance(cursor_raw, str):
            msg = "missing cursor_date"
            raise TypeError(msg)

        last_hit_raw = data.get("last_hit_date")
        last_hit = date.fromisoformat(last_hit_raw) if isinstance(last_hit_raw, str) else None

        stop_boundary_raw = data.get("stop_boundary")
        stop_boundary = (
            date.fromisoformat(stop_boundary_raw) if isinstance(stop_boundary_raw, str) else None
        )

        raw_streak = data.get("empty_streak", 0)
        streak = int(raw_streak) if isinstance(raw_streak, (int, float, str)) else 0

        return cls(
            cursor_date=date.fromisoformat(cursor_raw),
            empty_streak=streak,
            stopped=bool(data.get("stopped", False)),
            stop_boundary=stop_boundary,
            last_hit_date=last_hit,
            last_checked_at=str(data.get("last_checked_at"))
            if data.get("last_checked_at")
            else None,
            last_result=str(data.get("last_result")) if data.get("last_result") else None,
        )


class SyncState:
    """Per-tribunal progress tracking with JSON persistence."""

    def __init__(self) -> None:
        self._tribunals: dict[str, TribunalProgress] = {}
        self._lock = asyncio.Lock()

    async def get_or_init(self, tribunal: str, start_date: date) -> TribunalProgress:
        async with self._lock:
            if tribunal not in self._tribunals:
                self._tribunals[tribunal] = TribunalProgress(cursor_date=start_date)
            return self._tribunals[tribunal]

    async def record_hit(self, tribunal: str, d: date) -> None:
        async with self._lock:
            prog = self._tribunals[tribunal]
            prog.empty_streak = 0
            prog.stop_boundary = None
            prog.last_hit_date = d
            prog.last_result = "hit"
            prog.last_checked_at = datetime.now(tz=UTC).isoformat()

    async def record_empty(self, tribunal: str) -> bool:
        async with self._lock:
            prog = self._tribunals[tribunal]
            prog.empty_streak += 1
            prog.last_result = "empty"
            prog.last_checked_at = datetime.now(tz=UTC).isoformat()
            if prog.empty_streak >= STOP_THRESHOLD:
                prog.stopped = True
                return True
            return False

    async def record_error(self, tribunal: str) -> None:
        async with self._lock:
            prog = self._tribunals[tribunal]
            prog.last_result = "error"
            prog.last_checked_at = datetime.now(tz=UTC).isoformat()

    async def advance_cursor(self, tribunal: str, d: date | None = None) -> None:
        async with self._lock:
            prog = self._tribunals[tribunal]
            if d:
                prog.cursor_date = min(prog.cursor_date, d)
            else:
                prog.cursor_date -= timedelta(days=1)

    async def ensure_cursor_at_least(self, tribunal: str, min_date: date) -> bool:
        async with self._lock:
            if tribunal not in self._tribunals:
                return False
            prog = self._tribunals[tribunal]
            if prog.cursor_date < min_date:
                if prog.stopped:
                    prog.stop_boundary = prog.cursor_date
                    prog.stopped = False
                    prog.empty_streak = 0
                prog.cursor_date = min_date
                return True
            return False

    def get_all_progress(self) -> dict[str, TribunalProgress]:
        return dict(self._tribunals)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": 2,
            "updated_at": datetime.now(tz=UTC).isoformat(),
            "tribunals": {k: v.to_dict() for k, v in self._tribunals.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SyncState:
        state = cls()
        if data.get("version") != VERSION_EXPECTED:
            return state
        tribunals = data.get("tribunals")
        if isinstance(tribunals, dict):
            for code, raw in tribunals.items():
                if isinstance(code, str) and isinstance(raw, dict):
                    with contextlib.suppress(ValueError, TypeError):
                        state._tribunals[code] = TribunalProgress.from_dict(raw)
        return state


# ── IA State Persistence ───────────────────────────────────────────


async def download_state_from_ia(filename: str) -> dict | None:
    item_id = "causaganha-dashboard"
    url = f"https://archive.org/download/{item_id}/{filename}"
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        log.warning("state_download_failed", filename=filename, error=str(exc))
    return None


async def upload_state_to_ia(filename: str, data: dict, auth: str) -> bool:
    item_id = "causaganha-dashboard"
    url = f"https://s3.us.archive.org/{item_id}/{filename}"
    content = json.dumps(data, indent=2).encode("utf-8")
    headers = {
        "Authorization": auth,
        "Content-Type": "application/json",
        "x-amz-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await put_ia_bytes(client, url, content, headers)
            if resp.status_code < 400:
                log.info("state_uploaded_to_ia", filename=filename)
                return True
    except Exception as exc:
        log.warning("state_upload_error", filename=filename, error=str(exc))
    return False


# ── The simple function ────────────────────────────────────────────


async def sync_date(
    tribunal: str,
    d: date,
    *,
    djen_url: str | None = None,
    ia_auth: str | None = None,
    dry_run: bool = False,
) -> str:
    """Download one DJEN ZIP and upload it to Internet Archive.

    This is the core operation, self-contained and callable standalone::

        from djen_backup.engine import sync_date
        result = await sync_date("TJSP", date(2024, 3, 15))

    Returns ``"uploaded"``, ``"empty"`` (no publication), or raises on error.
    """
    resolved_url = djen_url or DJEN_PROXY_FALLBACK_URL
    resolved_auth = ia_auth or get_ia_s3_auth()

    timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        # 1. Get ZIP URL from DJEN
        try:
            zip_url = await get_caderno_url(client, resolved_url, tribunal, d)
        except DJENNotFoundError:
            return "empty"

        # 2. Download ZIP
        zip_path = await download_zip(client, zip_url)

        try:
            if dry_run:
                log.info("dry_run", tribunal=tribunal, date=d.isoformat())
                return "uploaded"

            # 3. Upload to Internet Archive
            item_id = get_ia_item_id(tribunal, d)
            async with create_upload_client(resolved_auth) as ia_client:
                ok = await upload_zip(ia_client, item_id, zip_path)

            if not ok:
                msg = f"Upload failed for {tribunal} {d.isoformat()}"
                raise RuntimeError(msg)

            url = f"https://archive.org/download/{item_id}/{zip_path.name}"
            log.info("sync_complete", tribunal=tribunal, date=d.isoformat(), url=url)
            return "uploaded"
        finally:
            zip_path.unlink(missing_ok=True)


# ── Engine internals ───────────────────────────────────────────────


@dataclass
class SyncConfig:
    """Configuration for the batch sync engine."""

    start_date: date
    lower_bound: date | None
    tribunal: str | None
    deadline_minutes: int
    max_items: int
    workers: int
    state_file: Path | None
    djen_proxy_url: str
    ia_auth: str
    dry_run: bool
    skip_absent_markers: bool = False
    publish_live_status: bool = False
    skip_if_mostly_complete: bool = False
    genesis_dates: dict[str, date] = field(default_factory=dict)
    observer: SyncObserver | None = None


@dataclass
class SyncSummary:
    """Statistics for the current run."""

    hits: int = 0
    cache_hits: int = 0
    empties: int = 0
    errors: int = 0
    scanned: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def inc_hit(self) -> None:
        async with self._lock:
            self.hits += 1

    async def inc_cache_hit(self) -> None:
        async with self._lock:
            self.cache_hits += 1

    async def inc_empty(self) -> None:
        async with self._lock:
            self.empties += 1

    async def inc_error(self) -> None:
        async with self._lock:
            self.errors += 1


async def process_date(  # noqa: PLR0913
    client: AsyncClient,
    ia_client: AsyncClient,
    tribunal: str,
    d: date,
    config: SyncConfig,
    state: SyncState,
    inventory: ZipInventory,
    summary: SyncSummary,
    circuit: CircuitBreaker,
) -> str:
    """Download from DJEN and upload to IA in one step. No staging."""
    targeted_single_day = (
        config.tribunal is not None
        and config.lower_bound is not None
        and config.lower_bound == config.start_date
    )

    # 1. Check inventory cache
    status = inventory.get_status(tribunal, d)
    if status == "uploaded":
        await state.record_hit(tribunal, d)
        await summary.inc_cache_hit()
        if config.observer:
            item_id = get_ia_item_id(tribunal, d)
            filename = f"djen-{d.isoformat()}-{tribunal.upper()}.zip"
            url = f"https://archive.org/download/{item_id}/{filename}"
            config.observer.on_item_complete(tribunal, d, "hit", url=url)
        return "hit"

    if status == "absent" and not targeted_single_day:
        await state.record_empty(tribunal)
        await summary.inc_empty()
        return "empty"

    if config.dry_run:
        log.info("dry_run", tribunal=tribunal, date=d.isoformat())
        await summary.inc_hit()
        return "hit"

    # 2. Download from DJEN
    try:
        zip_url = await get_caderno_url(client, config.djen_proxy_url, tribunal, d)
        zip_path = await download_zip(client, zip_url)
    except DJENNotFoundError as exc:
        if exc.reason in ("Not Found", "No publications"):
            await inventory.add_absent(tribunal, d)
            await state.record_empty(tribunal)
            await summary.inc_empty()
            if config.observer:
                config.observer.on_item_complete(tribunal, d, "empty")
            return "empty"
        await summary.inc_error()
        await state.record_error(tribunal)
        return "error"
    except Exception as exc:
        log.warning("download_failed", tribunal=tribunal, date=d.isoformat(), error=str(exc))
        await summary.inc_error()
        await state.record_error(tribunal)
        return "error"

    # 3. Upload to IA
    try:
        item_id = get_ia_item_id(tribunal, d)
        ok = await upload_zip(ia_client, item_id, zip_path, circuit_breaker=circuit)
        if ok:
            await inventory.add(tribunal, d)
            await state.record_hit(tribunal, d)
            await summary.inc_hit()
            if config.observer:
                filename = f"djen-{d.isoformat()}-{tribunal.upper()}.zip"
                url = f"https://archive.org/download/{item_id}/{filename}"
                config.observer.on_item_complete(tribunal, d, "hit", url=url)
            return "hit"
        await summary.inc_error()
        return "error"
    except Exception as exc:
        log.warning("upload_failed", tribunal=tribunal, date=d.isoformat(), error=str(exc))
        await summary.inc_error()
        return "error"
    finally:
        zip_path.unlink(missing_ok=True)


# ── Batch sync entry point ─────────────────────────────────────────

async def run_sync(config: SyncConfig) -> int:
    """Batch sync: walk tribunal x year, download gaps, upload to IA."""
    deadline = time.monotonic() + config.deadline_minutes * 60

    # 0. Load inventory and backfill state
    inventory = ZipInventory()
    await inventory.load_from_ia()
    inventory.load_from_disk()
    await inventory.load_from_snapshot()

    if config.skip_if_mostly_complete and not config.tribunal:
        from causaganha.config import TRIBUNAIS

        target = config.start_date
        total = len(TRIBUNAIS)
        already_done = sum(1 for t in TRIBUNAIS if inventory.has(t, target))
        threshold = math.ceil(total * 0.9)
        if already_done >= threshold:
            log.info("skip_mostly_complete", date=target.isoformat(), done=already_done, total=total)
            return 0

    state_data = await download_state_from_ia(IA_BACKFILL_STATE_FILENAME)
    state = SyncState.from_dict(state_data) if state_data else SyncState()
    circuit = CircuitBreaker()
    summary = SyncSummary()

    upper = config.start_date
    lower = config.lower_bound or date(2020, 1, 1)
    years = sorted(range(lower.year, upper.year + 1), reverse=True)

    timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)

    year_buffer_s = min(60.0, max(10.0, config.deadline_minutes * 10.0))
    item_buffer_s = min(30.0, max(5.0, config.deadline_minutes * 5.0))

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        ia_client = create_upload_client(config.ia_auth)

        tribunals = await get_tribunal_list(client, config.djen_proxy_url)
        if config.tribunal:
            tribunals = [config.tribunal.upper()]

        for t in tribunals:
            await state.get_or_init(t, upper)
            await state.ensure_cursor_at_least(t, upper)

        items_processed: dict[str, int] = dict.fromkeys(tribunals, 0)

        for year in years:
            if time.monotonic() > deadline - year_buffer_s:
                break

            # Reconcile with IA metadata for this year
            for t in tribunals:
                if config.observer:
                    config.observer.on_metadata_sync_start(t, year)
                ia_dates = await fetch_ia_existing(client, t, year)
                if ia_dates:
                    await inventory.add_many(t, set(ia_dates.keys()))
                if config.observer:
                    config.observer.on_metadata_sync_complete(t, year, len(ia_dates))

            # Build work queue for this year
            work: asyncio.Queue[tuple[str, date]] = asyncio.Queue()
            for t in sorted(tribunals):
                if config.max_items and items_processed[t] >= config.max_items:
                    continue
                prog = state.get_all_progress().get(t)
                if prog and prog.stopped:
                    continue
                gaps = inventory.gaps_for_year(t, year, upper, lower)
                if config.observer:
                    config.observer.on_gaps_discovered(t, year, len(gaps))
                for d in sorted(gaps, reverse=True):
                    work.put_nowait((t, d))

            if work.empty():
                continue

            # Workers drain the queue with bounded concurrency
            async def worker() -> None:
                while not work.empty():
                    if time.monotonic() > deadline - item_buffer_s:
                        return
                    try:
                        t, d = work.get_nowait()
                    except asyncio.QueueEmpty:
                        return

                    if config.max_items and items_processed.get(t, 0) >= config.max_items:
                        continue

                    result = await process_date(
                        client, ia_client, t, d, config, state, inventory, summary, circuit
                    )
                    items_processed[t] = items_processed.get(t, 0) + 1

                    if result in ("hit", "empty"):
                        await state.advance_cursor(t, d)

            workers = [asyncio.create_task(worker()) for _ in range(config.workers)]
            await asyncio.gather(*workers)

        await ia_client.aclose()

    # Persist state
    if not config.dry_run:
        await inventory.upload_to_ia(config.ia_auth)
        await upload_state_to_ia(IA_BACKFILL_STATE_FILENAME, state.to_dict(), config.ia_auth)

    log.info("sync_complete", hits=summary.hits, errors=summary.errors, dry_run=config.dry_run)
    return 1 if summary.errors > 0 else 0
