"""Manifest-driven sync engine for djen-backup."""

from __future__ import annotations

import asyncio
import contextlib
import shutil
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import NamedTuple, Protocol

import anyio
import httpx
import structlog
import tenacity
from aiolimiter import AsyncLimiter

from causaganha.pipeline.ia_s3 import create_upload_client
from djen_backup.archive import (
    CircuitBreaker,
    ItemBusyError,
    check_ia_file_exists,
    fetch_ia_existing,
    get_ia_item_id,
    upload_zip,
)
from djen_backup.djen import DJENNotFoundError, download_zip, get_caderno_url
from djen_backup.manifest import ManifestCounts, ManifestEntry, SyncManifest
from djen_backup.tribunais import get_tribunal_list


log = structlog.get_logger()

# ── Constants ────────────────────────────────────────────────────────

STAGING_DIR = Path("data/staging")
MAX_STAGED_FILES = 3
DJEN_SAFE_CONCURRENCY_FILE = Path("data/djen-safe-concurrency.json")
DEFAULT_DJEN_CONCURRENCY = 4  # fallback when stress test hasn't been run


def load_djen_safe_concurrency() -> int:
    """Return the discovered-safe DJEN concurrency, or fallback default.

    The value is produced by ``scripts/stress_test_djen.py`` and persisted
    in ``data/djen-safe-concurrency.json``. Re-run the stress test periodically
    to refresh it as DJEN's rate limiting changes.
    """
    if not DJEN_SAFE_CONCURRENCY_FILE.exists():
        return DEFAULT_DJEN_CONCURRENCY
    try:
        import json

        data = json.loads(DJEN_SAFE_CONCURRENCY_FILE.read_text())
        value = int(data.get("safe_concurrency", DEFAULT_DJEN_CONCURRENCY))
        return max(1, value)
    except (OSError, ValueError, KeyError, TypeError):
        return DEFAULT_DJEN_CONCURRENCY


def _save_safe_concurrency(value: int, *, reason: str) -> None:
    """Persist a new safe concurrency (from auto-adjust or stress test)."""
    import json
    from datetime import UTC, datetime

    DJEN_SAFE_CONCURRENCY_FILE.parent.mkdir(parents=True, exist_ok=True)
    DJEN_SAFE_CONCURRENCY_FILE.write_text(
        json.dumps(
            {
                "safe_concurrency": value,
                "reason": reason,
                "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
            },
            indent=2,
        )
    )


# ── Protocols ────────────────────────────────────────────────────────


class ManifestObserver(Protocol):
    """Interface for reporting manifest-driven sync progress to the UI."""

    def on_phase(self, phase: str) -> None: ...
    def on_counts_updated(self, counts: ManifestCounts) -> None: ...
    def on_log(self, message: str) -> None: ...
    def on_subtask(self, name: str, total: int) -> None: ...
    def on_subtask_advance(self, name: str, delta: int = 1) -> None: ...
    def on_subtask_done(self, name: str) -> None: ...


# ── Data structures ──────────────────────────────────────────────────


class StagedItem(NamedTuple):
    """A ZIP file that has been staged locally and is ready to upload."""

    item_id: str
    d: date
    tribunal: str
    path: Path


@dataclass
class SyncConfig:
    """Unified configuration for the sync engine."""

    start_date: date
    lower_bound: date | None
    tribunal: str | None
    deadline_minutes: int
    max_items: int
    workers: int
    manifest_file: Path
    djen_proxy_url: str
    ia_auth: str
    dry_run: bool
    fail_fast: bool = True
    publish_live_status: bool = False
    skip_if_mostly_complete: bool = False
    check_only: bool = False  # Only run DJEN checkers (no download/upload)
    upload_only: bool = False  # Only process already-available entries
    observer: ManifestObserver | None = None


@dataclass
class SyncSummary:
    """Statistics for the current run, tracking session-level gains."""

    # Real-time counters
    downloads: int = 0
    uploads: int = 0
    errors: int = 0

    # Baseline for calculating net progress
    initial_uploaded: int = 0
    initial_absent: int = 0
    initial_unknown: int = 0

    # Final result state (set at the end of run_sync)
    final_counts: ManifestCounts | None = None

    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def inc_download(self) -> None:
        async with self._lock:
            self.downloads += 1

    async def inc_upload(self) -> None:
        async with self._lock:
            self.uploads += 1

    async def inc_error(self) -> None:
        async with self._lock:
            self.errors += 1


# ── Unified check + download + upload pipeline ──────────────────────


async def run_pipeline(
    manifest: SyncManifest,
    config: SyncConfig,
    abort_event: asyncio.Event,
    summary: SyncSummary,
    deadline: float,
) -> None:
    """Check IA/DJEN and download+upload concurrently."""
    import random

    # ── Phase 0: Discovery ──
    existing_items: set[tuple[str, int]] = set()
    if not config.upload_only:
        log.info("ia_discovery_starting")
        timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                resp = await client.get(
                    "https://archive.org/advancedsearch.php",
                    params={
                        "q": "identifier:djen-*-*",
                        "fl[]": "identifier",
                        "rows": "2000",
                        "output": "json",
                    },
                )
                docs = resp.json()["response"]["docs"]
                for d in docs:
                    ident = d["identifier"]
                    parts = ident.rsplit("-", 1)
                    if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 4:
                        tribunal = parts[0][5:].upper()
                        year = int(parts[1])
                        if tribunal and 2000 < year < 2100:
                            existing_items.add((tribunal, year))
                log.info("ia_items_discovered", count=len(existing_items))
            except Exception as exc:
                log.warning("ia_search_failed_fallback", error=str(exc))
                existing_items = {(e.tribunal, e.date.year) for e in manifest._entries.values() if e.ia_status != "uploaded"}

    # Build check priority
    from collections import defaultdict
    from datetime import date as dt_date

    uploaded_by_tribunal: dict[str, list[dt_date]] = defaultdict(list)
    for e in manifest._entries.values():
        if e.ia_status == "uploaded":
            uploaded_by_tribunal[e.tribunal].append(e.date)
    for dates in uploaded_by_tribunal.values():
        dates.sort()

    def _is_adjacent(entry: ManifestEntry, window_days: int = 30) -> bool:
        uploads = uploaded_by_tribunal.get(entry.tribunal)
        if not uploads: return False
        d = entry.date
        for up in uploads:
            if abs((up - d).days) <= window_days: return True
            if up > d: break
        return False

    adjacent_entries, isolated_entries = [], []
    for e in manifest._entries.values():
        if e.ia_status != "" or e.djen_status != "": continue
        if _is_adjacent(e): adjacent_entries.append(e)
        else: isolated_entries.append(e)

    random.shuffle(adjacent_entries)
    random.shuffle(isolated_entries)
    unknown_entries = adjacent_entries + isolated_entries

    await anyio.Path(STAGING_DIR).mkdir(parents=True, exist_ok=True)

    check_queue: asyncio.Queue[ManifestEntry] = asyncio.Queue()
    for entry in unknown_entries: check_queue.put_nowait(entry)

    download_queue: asyncio.Queue[ManifestEntry | None] = asyncio.Queue(maxsize=MAX_STAGED_FILES)
    upload_queue: asyncio.Queue[StagedItem | None] = asyncio.Queue(maxsize=MAX_STAGED_FILES)

    # ── PRIORITY: Load existing backlog ──
    backlog = manifest.entries_needing_upload()
    if backlog:
        log.info("backlog_priority_load", count=len(backlog))

    circuit_breaker = CircuitBreaker()
    last_save = time.monotonic()
    last_ia_upload = time.monotonic()
    save_interval, ia_upload_interval = 180.0, 600.0
    checkers_done = asyncio.Event()

    last_stats_log, last_notify = time.monotonic(), time.monotonic()
    stats_log_interval, notify_interval = 30.0, 0.5

    djen_breaker = CircuitBreaker(threshold=5, recovery_timeout=30.0)
    djen_limiter = AsyncLimiter(max_rate=3, time_period=1)

    async def _check_djen_breaker() -> bool:
        while not await djen_breaker.allow_request():
            if abort_event.is_set() or time.monotonic() > deadline: return False
            await asyncio.sleep(5.0)
        return True

    _ia_upload_running = False
    async def _upload_manifest_background() -> None:
        nonlocal _ia_upload_running
        if _ia_upload_running: return
        _ia_upload_running = True
        try:
            if await manifest.upload_to_ia(config.ia_auth):
                await manifest.upload_summary_to_ia(config.ia_auth)
        except Exception: pass
        finally: _ia_upload_running = False

    def _notify_counts() -> None:
        nonlocal last_stats_log, last_notify
        now = time.monotonic()
        if now - last_notify < notify_interval: return
        last_notify = now
        c = manifest.counts()
        if config.observer: config.observer.on_counts_updated(c)
        if now - last_stats_log > stats_log_interval:
            last_stats_log = now
            log.info("progress", uploaded=c.uploaded, pending=c.available, unknown=c.unknown)

    synced_ia_items: set[tuple[str, int]] = set()
    ia_sync_lock = asyncio.Lock()

    async def checker_worker(client: httpx.AsyncClient) -> None:
        nonlocal last_save, last_ia_upload
        while not abort_event.is_set() and time.monotonic() < deadline:
            try: entry = check_queue.get_nowait()
            except asyncio.QueueEmpty: return

            item_key = (entry.tribunal, entry.date.year)
            if item_key in existing_items and item_key not in synced_ia_items:
                async with ia_sync_lock:
                    if item_key not in synced_ia_items:
                        try:
                            ia_dates = await fetch_ia_existing(client, entry.tribunal, entry.date.year)
                            if ia_dates: await manifest.mark_ia_uploaded(entry.tribunal, set(ia_dates.keys()))
                            synced_ia_items.add(item_key)
                            _notify_counts()
                        except Exception: pass

            if entry.ia_status == "uploaded": continue
            if not await _check_djen_breaker(): return

            try:
                async with djen_limiter:
                    await get_caderno_url(client, config.djen_proxy_url, entry.tribunal, entry.date)
                raw_status = "200"
            except DJENNotFoundError as exc: raw_status = str(exc.status_code)
            except Exception: raw_status = "error"

            await manifest.mark_djen_raw(entry.tribunal, entry.date, raw_status)
            if raw_status in ("403", "timeout", "error"): await djen_breaker.record_failure()
            else: await djen_breaker.record_success()

            _notify_counts()
            now = time.monotonic()
            if now - last_save > save_interval:
                last_save = now
                manifest.save_to_disk(config.manifest_file)
            if now - last_ia_upload > ia_upload_interval and not config.dry_run:
                last_ia_upload = now
                asyncio.create_task(_upload_manifest_background())

    async def download_worker(client: httpx.AsyncClient) -> None:
        while not abort_event.is_set():
            entry = await download_queue.get()
            if entry is None:
                download_queue.task_done()
                return
            if config.max_items and summary.downloads >= config.max_items:
                download_queue.task_done()
                continue
            try:
                async for attempt in tenacity.AsyncRetrying(
                    stop=tenacity.stop_after_attempt(4), wait=tenacity.wait_exponential(multiplier=1, min=1, max=4),
                    retry=tenacity.retry_if_exception_type(DJENNotFoundError), reraise=True,
                ):
                    with attempt: url = await get_caderno_url(client, config.djen_proxy_url, entry.tribunal, entry.date)
                zip_path = await download_zip(client, url)
                item_id = get_ia_item_id(entry.tribunal, entry.date)
                dest_dir = STAGING_DIR / item_id
                dest_dir.mkdir(parents=True, exist_ok=True)
                final_path = dest_dir / f"djen-{entry.date.isoformat()}-{entry.tribunal.upper()}.zip"
                await asyncio.to_thread(shutil.move, str(zip_path), str(final_path))
                await summary.inc_download()
                await upload_queue.put(StagedItem(item_id, entry.date, entry.tribunal, final_path))
            except Exception as exc:
                log.warning("download_failed", tribunal=entry.tribunal, date=entry.date.isoformat(), error=str(exc))
                await summary.inc_error()
            finally: download_queue.task_done()

    async def upload_worker(upload_client: httpx.AsyncClient) -> None:
        while not abort_event.is_set():
            item = await upload_queue.get()
            if item is None:
                upload_queue.task_done()
                return
            try:
                if await check_ia_file_exists(upload_client, item.tribunal, item.d):
                    await manifest.mark_uploaded(item.tribunal, item.d)
                    await summary.inc_upload()
                    if config.observer: config.observer.on_log(f"[dim]Already on IA[/dim] {item.tribunal} {item.d}")
                    item.path.unlink(missing_ok=True)
                    continue
                if await upload_zip(upload_client, item.item_id, item.path, circuit_breaker=circuit_breaker, try_lock=True):
                    await manifest.mark_uploaded(item.tribunal, item.d)
                    await summary.inc_upload()
                    if config.observer: config.observer.on_log(f"[green]Uploaded[/green] {item.tribunal} {item.d}")
                    item.path.unlink(missing_ok=True)
                else:
                    if config.fail_fast: abort_event.set()
            except Exception as exc:
                log.warning("upload_exception", item_id=item.item_id, error=str(exc))
            finally: upload_queue.task_done()

    check_timeout = httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=10.0)
    dl_timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)

    async with (
        httpx.AsyncClient(timeout=check_timeout, follow_redirects=True) as check_client,
        httpx.AsyncClient(timeout=dl_timeout, follow_redirects=True) as dl_client,
        create_upload_client(config.ia_auth) as upload_client,
    ):
        async def feed_available() -> None:
            # 1. Load backlog first (respecting max_items)
            initial_backlog = backlog[:config.max_items] if config.max_items else backlog
            for entry in initial_backlog:
                await download_queue.put(entry)
            
            seen = {f"{e.tribunal}/{e.date.isoformat()}" for e in backlog}
            # 2. Continuous feed for newly discovered entries
            while not abort_event.is_set():
                if config.max_items and summary.downloads >= config.max_items: return
                entries = manifest.entries_needing_upload()
                for entry in entries:
                    key = f"{entry.tribunal}/{entry.date.isoformat()}"
                    if key not in seen:
                        seen.add(key)
                        await download_queue.put(entry)
                if checkers_done.is_set() and not entries: return
                await asyncio.sleep(2)

        feeder_task = asyncio.create_task(feed_available())
        checker_tasks = [asyncio.create_task(checker_worker(check_client)) for _ in range(0 if config.upload_only else config.workers)]
        dl_tasks = [asyncio.create_task(download_worker(dl_client)) for _ in range(0 if config.check_only else max(1, config.workers // 4))]
        upload_tasks = [asyncio.create_task(upload_worker(upload_client)) for _ in range(0 if config.check_only else config.workers)]

        await asyncio.gather(*checker_tasks, return_exceptions=True)
        checkers_done.set()
        await asyncio.gather(feeder_task, return_exceptions=True)
        for _ in dl_tasks: await download_queue.put(None)
        await asyncio.gather(*dl_tasks, return_exceptions=True)
        for _ in upload_tasks: await upload_queue.put(None)
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(upload_queue.join(), timeout=max(0.0, deadline - time.monotonic()))
        await asyncio.gather(*upload_tasks, return_exceptions=True)


async def run_sync(config: SyncConfig) -> tuple[int, SyncSummary]:
    """Manifest-driven sync: build → check+download+upload (concurrent)."""
    start_time = time.monotonic()
    deadline = start_time + config.deadline_minutes * 60
    summary = SyncSummary()
    abort_event = asyncio.Event()
    manifest = SyncManifest()

    if config.observer: config.observer.on_phase("Loading manifest")
    await manifest.load_from_ia()
    manifest.load_from_disk(config.manifest_file)
    
    # Capture baseline
    counts_init = manifest.counts()
    summary.initial_uploaded = counts_init.uploaded
    summary.initial_absent = counts_init.absent
    summary.initial_unknown = counts_init.unknown

    if config.observer: config.observer.on_phase("Building manifest")
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0), follow_redirects=True) as client:
        tribunals = await get_tribunal_list(client, config.djen_proxy_url)
    if config.tribunal: tribunals = [config.tribunal.upper()]

    manifest.build(tribunals, config.lower_bound or date(2020, 1, 1), config.start_date)
    manifest.prune()
    if config.observer: config.observer.on_counts_updated(manifest.counts())

    if config.observer: config.observer.on_phase("Syncing")
    try:
        await run_pipeline(manifest, config, abort_event, summary, deadline)
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.warning("sync_interrupted")
    finally:
        manifest.save_to_disk(config.manifest_file)
        if not config.dry_run:
            log.info("final_ia_manifest_upload_starting")
            if await manifest.upload_to_ia(config.ia_auth):
                await manifest.upload_summary_to_ia(config.ia_auth)
                log.info("final_ia_manifest_upload_complete")

    summary.final_counts = manifest.counts()
    exit_code = 1 if summary.errors > 0 or abort_event.is_set() else 0
    return exit_code, summary
