from __future__ import annotations

import asyncio
import contextlib
import json
import math
import shutil
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import httpx
import structlog

from djen_backup.archive import (
    get_ia_item_id,
    upload_zip,
)
from djen_backup.djen import DJENNotFoundError, download_zip, get_caderno_url
from djen_backup.inventory import ZipInventory
from djen_backup.tribunais import get_tribunal_list


if TYPE_CHECKING:
    from httpx import AsyncClient

log = structlog.get_logger()

# ── Protocols ───────────────────────────────────────────────────────


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


# Constants
VERSION_EXPECTED = 2
STOP_THRESHOLD = 60
IA_BACKFILL_STATE_FILENAME = "backfill-state.json"
STAGING_DIR = Path("data/staging")
MAX_STAGED_FILES = 30
BATCH_SIZE = 10


# ── State Management ────────────────────────────────────────────────


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


# ── IA Helpers ──────────────────────────────────────────────────────


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
            resp = await client.put(url, content=content, headers=headers)
            if resp.status_code < 400:
                log.info("state_uploaded_to_ia", filename=filename)
                return True
    except Exception as exc:
        log.warning("state_upload_error", filename=filename, error=str(exc))
    return False


# ── Sync Engine ─────────────────────────────────────────────────────


@dataclass
class SyncConfig:
    """Unified configuration for the sync engine."""

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


async def download_to_staging(
    client: AsyncClient,
    tribunal: str,
    d: date,
    config: SyncConfig,
    state: SyncState,
    inventory: ZipInventory,
    summary: SyncSummary,
) -> str:
    """Download a single ZIP from DJEN and place it in staging."""
    # 1. Check inventory
    status = inventory.get_status(tribunal, d)
    if status == "uploaded":
        await state.record_hit(tribunal, d)
        await summary.inc_cache_hit()
        if config.observer:
            item_id = get_ia_item_id(tribunal, d)
            url = f"https://archive.org/download/{item_id}"
            config.observer.on_item_complete(tribunal, d, "hit", url=url)
        return "hit"
    if status in ("absent", "staged"):
        if status == "absent":
            await state.record_empty(tribunal)
            await summary.inc_empty()
        return status

    if config.dry_run:
        log.info("sync_dry_run", tribunal=tribunal, date=d.isoformat())
        await summary.inc_hit()
        return "hit"

    # 2. Fetch from DJEN
    try:
        zip_url = await get_caderno_url(client, config.djen_proxy_url, tribunal, d)
        zip_path = await download_zip(client, zip_url)

        # Move to staging
        item_id = get_ia_item_id(tribunal, d)
        dest_dir = STAGING_DIR / item_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = f"djen-{d.isoformat()}-{tribunal.upper()}.zip"
        final_path = dest_dir / filename

        await asyncio.to_thread(shutil.move, str(zip_path), str(final_path))
        await inventory.add_staged(tribunal, d)

        log.info("staged_file", tribunal=tribunal, date=d.isoformat(), path=str(final_path))
        return "staged"

    except DJENNotFoundError as exc:
        if exc.reason in ("Not Found", "No publications"):
            await inventory.add_absent(tribunal, d)
            await state.record_empty(tribunal)
            await summary.inc_empty()
            if config.observer:
                config.observer.on_item_complete(tribunal, d, "empty")
            return "empty"
    except Exception as exc:
        log.warning("download_failed", tribunal=tribunal, date=d.isoformat(), error=str(exc))
        await summary.inc_error()
        await state.record_error(tribunal)

    return "error"


async def batch_uploader(
    config: SyncConfig,
    inventory: ZipInventory,
    state: SyncState,
    summary: SyncSummary,
    upload_client: httpx.AsyncClient,
) -> None:
    """Background consumer that uploads batches of files from staging."""
    while True:
        staged_items = inventory.get_staged_by_item()
        if not staged_items:
            await asyncio.sleep(10)
            continue

        for item_id, dates in staged_items.items():
            if len(dates) >= BATCH_SIZE or (
                len(dates) > 0 and time.monotonic() % 300 < 10
            ):  # Batch of 10 or every 5 mins
                if config.observer:
                    config.observer.on_batch_upload_start(item_id, len(dates))

                # Prepare file list
                files = []
                for d in dates:
                    filename = f"djen-{d.isoformat()}-{item_id.split('-')[1].upper()}.zip"
                    files.append(str(STAGING_DIR / item_id / filename))

                try:
                    tribunal = item_id.split("-")[1].upper()
                    for d in dates:
                        filename = f"djen-{d.isoformat()}-{tribunal}.zip"
                        path = STAGING_DIR / item_id / filename
                        if not config.dry_run:
                            resp = await upload_zip(
                                upload_client, d, tribunal, path, config.ia_auth
                            )
                            if resp.status_code != 200:
                                log.warning(
                                    "batch_upload_item_failed",
                                    item_id=item_id,
                                    date=d.isoformat(),
                                    status=resp.status_code,
                                )
                                continue  # leave file on disk for retry next tick

                        # post-upload tracking
                        await inventory.add(tribunal, d)
                        await state.record_hit(tribunal, d)
                        await summary.inc_hit()
                        if not config.dry_run:
                            path.unlink(missing_ok=True)

                    if config.observer:
                        config.observer.on_batch_upload_complete(item_id, len(dates))

                except Exception:
                    log.exception("batch_upload_failed", item_id=item_id)

        await asyncio.sleep(30)


async def run_sync(config: SyncConfig) -> int:
    """The unified sync entry point with Producer-Consumer Batching."""
    start_time = time.monotonic()
    deadline = start_time + config.deadline_minutes * 60
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    # 0. Initial state & inventory
    inventory = ZipInventory()
    await inventory.load_from_ia()
    inventory.load_from_disk()
    await inventory.load_from_snapshot()

    # Early exit: if today is already mostly collected, skip the run.
    # Skip this check for single-tribunal runs — those must always execute
    # regardless of global completion, otherwise --tribunal TJSP would exit
    # early because other courts pushed the global count above the threshold.
    if config.skip_if_mostly_complete and not config.tribunal:
        from causaganha.config import TRIBUNAIS

        target = config.start_date  # start_date holds the upper (most-recent) date
        total = len(TRIBUNAIS)
        already_done = sum(1 for t in TRIBUNAIS if inventory.has(t, target))
        threshold = math.ceil(total * 0.9)  # ceil ensures true >=90%, not floor
        if already_done >= threshold:
            log.info(
                "skip_if_mostly_complete",
                date=target.isoformat(),
                already_done=already_done,
                total=total,
            )
            return 0
        log.info(
            "skip_if_mostly_complete_not_met",
            date=target.isoformat(),
            already_done=already_done,
            total=total,
            threshold=threshold,
        )

    remote_state_data = await download_state_from_ia(IA_BACKFILL_STATE_FILENAME)
    state = SyncState.from_dict(remote_state_data) if remote_state_data else SyncState()

    upload_timeout = httpx.Timeout(connect=10.0, read=600.0, write=600.0, pool=10.0)
    upload_client = httpx.AsyncClient(timeout=upload_timeout, follow_redirects=True)

    try:
        # 1. Start Consumer (Uploader)
        summary = SyncSummary()
        uploader_task = asyncio.create_task(
            batch_uploader(config, inventory, state, summary, upload_client)
        )

        # 2. Main Scan (Producers)
        timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            tribunals = await get_tribunal_list(client, config.djen_proxy_url)
            if config.tribunal:
                tribunals = [config.tribunal.upper()]

            for t in tribunals:
                await state.ensure_cursor_at_least(t, config.start_date)

            upper = config.start_date
            lower = config.lower_bound or date(2020, 1, 1)
            years = sorted(range(lower.year, upper.year + 1), reverse=True)

            last_ia_sync = time.monotonic()
            sync_interval_s = 180

            for year in years:
                if time.monotonic() > deadline - 60:
                    break
                log.info("sync_year_starting", year=year)

                tribunal_queue = asyncio.Queue()
                for t in sorted(tribunals):
                    if not inventory.is_year_complete(t, year, upper, lower):
                        tribunal_queue.put_nowait(t)

                synced_metadata: set[str] = set()
                pending_gaps: dict[str, list[date]] = {}

                async def downloader_task() -> None:
                    nonlocal last_ia_sync
                    while not tribunal_queue.empty():
                        if time.monotonic() > deadline - 30:
                            break

                        # Back-pressure: if staging is too full, wait
                        while inventory.count_staged() >= MAX_STAGED_FILES:
                            await asyncio.sleep(30)
                            if time.monotonic() > deadline - 30:
                                return

                        t = await tribunal_queue.get()
                        try:
                            if t not in synced_metadata:
                                from djen_backup.archive import fetch_ia_existing

                                ia_dates = await fetch_ia_existing(client, t, year)
                                if ia_dates:
                                    await inventory.add_many(t, set(ia_dates.keys()))
                                gaps = inventory.gaps_for_year(t, year, upper, lower)
                                pending_gaps[t] = sorted(gaps, reverse=True)
                                synced_metadata.add(t)

                            if pending_gaps.get(t):
                                d = pending_gaps[t].pop(0)
                                res = await download_to_staging(
                                    client, t, d, config, state, inventory, summary
                                )

                                if res in ("hit", "empty"):
                                    await state.advance_cursor(t, d)

                                if pending_gaps[t]:
                                    tribunal_queue.put_nowait(t)

                            # Periodic sync
                            if (
                                not config.dry_run
                                and time.monotonic() - last_ia_sync > sync_interval_s
                            ):
                                last_ia_sync = time.monotonic()
                                await inventory.upload_to_ia(config.ia_auth)
                                await upload_state_to_ia(
                                    IA_BACKFILL_STATE_FILENAME, state.to_dict(), config.ia_auth
                                )
                        finally:
                            tribunal_queue.task_done()

                # Start downloaders
                downloaders = [
                    asyncio.create_task(downloader_task()) for _ in range(config.workers)
                ]
                await asyncio.gather(*downloaders)

        # 3. Finalize
        uploader_task.cancel()  # Stop monitoring, but we need a final flush
        log.info("final_flush_starting")
        if not config.dry_run:
            # Final upload of anything left in staging
            staged_items = inventory.get_staged_by_item()
            for item_id, dates in staged_items.items():
                tribunal = item_id.split("-")[1].upper()
                try:
                    for d in dates:
                        filename = f"djen-{d.isoformat()}-{tribunal}.zip"
                        path = STAGING_DIR / item_id / filename
                        resp = await upload_zip(upload_client, d, tribunal, path, config.ia_auth)
                        if resp.status_code != 200:
                            log.warning(
                                "final_flush_item_failed",
                                item_id=item_id,
                                date=d.isoformat(),
                                status=resp.status_code,
                            )
                            continue

                        await inventory.add(tribunal, d)
                        path.unlink(missing_ok=True)
                except Exception:
                    log.exception("final_flush_failed", item_id=item_id)

            await inventory.upload_to_ia(config.ia_auth)
            await upload_state_to_ia(IA_BACKFILL_STATE_FILENAME, state.to_dict(), config.ia_auth)

        log.info("sync_complete", hits=summary.hits, errors=summary.errors, dry_run=config.dry_run)
        return 1 if summary.errors > 0 else 0

    finally:
        await upload_client.aclose()
