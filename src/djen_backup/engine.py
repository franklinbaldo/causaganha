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

import httpx
import structlog

from causaganha.pipeline.ia_s3 import create_upload_client
from djen_backup.archive import (
    CircuitBreaker,
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
UPLOAD_WORKERS = 4

# ── Protocols ────────────────────────────────────────────────────────


class ManifestObserver(Protocol):
    """Interface for reporting manifest-driven sync progress to the UI."""

    def on_phase(self, phase: str) -> None: ...
    def on_counts_updated(self, counts: ManifestCounts) -> None: ...
    def on_log(self, message: str) -> None: ...


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
    observer: ManifestObserver | None = None


@dataclass
class SyncSummary:
    """Statistics for the current run."""

    downloads: int = 0
    uploads: int = 0
    errors: int = 0
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
    """Check IA/DJEN and download+upload concurrently.

    Checker workers discover available entries and push them into a
    download queue. Download workers fetch from DJEN and push into an
    upload queue. Upload workers send to IA. All run concurrently.

    Checkers use a **priority queue** sorted by absent streak: the
    tribunal with the shortest streak is always checked next. This
    ensures tribunals with data get processed first and tribunals
    hitting long absent tails are naturally deprioritized.
    No fixed stop threshold — the min-streak strategy handles it.
    """
    items = manifest.items_needing_ia_check()
    if not items:
        entries_to_upload = manifest.entries_needing_upload()
        if not entries_to_upload:
            log.info("pipeline_nothing_to_do")
            return

    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    # Priority queue: (streak, tribunal, year) — lowest streak checked first
    import heapq

    check_heap: list[tuple[int, str, int]] = []
    for tribunal, year in items:
        heapq.heappush(check_heap, (0, tribunal, year))
    check_lock = asyncio.Lock()

    download_queue: asyncio.Queue[ManifestEntry | None] = asyncio.Queue(maxsize=MAX_STAGED_FILES)
    upload_queue: asyncio.Queue[StagedItem | None] = asyncio.Queue(maxsize=MAX_STAGED_FILES)

    circuit_breaker = CircuitBreaker()
    first_error: list[str] = []
    last_save = time.monotonic()
    save_interval = 180.0
    checkers_done = asyncio.Event()

    # Per-tribunal absent streak (global across years)
    absent_streaks: dict[str, int] = {}

    # Track which (tribunal, year) items already had their IA metadata fetched
    ia_checked_items: set[tuple[str, int]] = set()

    def _notify_counts() -> None:
        if config.observer:
            config.observer.on_counts_updated(manifest.counts())

    # ── Checker workers ──────────────────────────────────────────
    # Each checker grabs an entire (tribunal, year) item and processes
    # ALL its entries before returning it. This eliminates heap contention
    # and shared-list race conditions — each worker owns its batch.
    async def checker_worker(client: httpx.AsyncClient) -> None:
        nonlocal last_save
        while True:
            if abort_event.is_set():
                return
            if time.monotonic() > deadline:
                return

            # Grab the tribunal+year with the shortest absent streak
            async with check_lock:
                if not check_heap:
                    return
                _streak, tribunal, year = heapq.heappop(check_heap)

            try:
                item_key = (tribunal, year)

                # 1. Lazy IA check — once per (tribunal, year)
                if item_key not in ia_checked_items:
                    if not manifest.has_uploaded_entries(tribunal, year):
                        ia_dates = await fetch_ia_existing(client, tribunal, year)
                        if ia_dates:
                            await manifest.mark_ia_checked(tribunal, year, set(ia_dates.keys()))
                            log.info(
                                "ia_checked", tribunal=tribunal, year=year, found=len(ia_dates)
                            )
                        _notify_counts()
                    ia_checked_items.add(item_key)

                # 2. Get entries to DJEN-check (this worker owns this batch)
                if config.dry_run:
                    continue
                entries = manifest.entries_needing_djen_check(tribunal, year)
                if not entries:
                    continue

                # 3. Process ALL entries for this tribunal+year
                for entry in entries:
                    if abort_event.is_set() or time.monotonic() > deadline:
                        return

                    try:
                        await get_caderno_url(client, config.djen_proxy_url, tribunal, entry.date)
                        await manifest.mark_djen_available(tribunal, entry.date)
                        absent_streaks[tribunal] = 0
                    except DJENNotFoundError:
                        await manifest.mark_djen_absent(tribunal, entry.date)
                        absent_streaks[tribunal] = absent_streaks.get(tribunal, 0) + 1
                    except Exception as exc:
                        log.warning(
                            "djen_check_skipped",
                            tribunal=tribunal,
                            date=entry.date.isoformat(),
                            error=str(exc),
                        )

                    _notify_counts()

                # Periodic save
                now = time.monotonic()
                if now - last_save > save_interval:
                    last_save = now
                    manifest.save_to_disk(config.manifest_file)

            except Exception as exc:
                log.warning(
                    "checker_error",
                    tribunal=tribunal,
                    year=year,
                    error=str(exc),
                )
                if config.fail_fast:
                    if not first_error:
                        first_error.append(f"Checker error: {tribunal} {year}")
                    abort_event.set()
                    return

    # ── Download workers ─────────────────────────────────────────
    async def download_worker(client: httpx.AsyncClient) -> None:
        while True:
            if abort_event.is_set():
                return
            entry = await download_queue.get()
            if entry is None:  # poison pill
                download_queue.task_done()
                return

            try:
                if config.max_items and summary.downloads >= config.max_items:
                    download_queue.task_done()
                    continue

                # Always fetch a fresh URL (pre-signed URLs expire quickly)
                url = await get_caderno_url(
                    client, config.djen_proxy_url, entry.tribunal, entry.date
                )
                zip_path = await download_zip(client, url)

                # Stage
                item_id = get_ia_item_id(entry.tribunal, entry.date)
                dest_dir = STAGING_DIR / item_id
                dest_dir.mkdir(parents=True, exist_ok=True)
                filename = f"djen-{entry.date.isoformat()}-{entry.tribunal.upper()}.zip"
                final_path = dest_dir / filename
                await asyncio.to_thread(shutil.move, str(zip_path), str(final_path))

                await summary.inc_download()
                log.info("staged", tribunal=entry.tribunal, date=entry.date.isoformat())

                # Enqueue for upload
                await upload_queue.put(StagedItem(item_id, entry.date, entry.tribunal, final_path))

            except DJENNotFoundError:
                # Checker confirmed available but downloader got 404 —
                # DJEN is inconsistent. Leave as available for retry.
                log.warning(
                    "download_inconsistent",
                    tribunal=entry.tribunal,
                    date=entry.date.isoformat(),
                    msg="checker confirmed available but download got 404",
                )

            except Exception as exc:
                log.warning(
                    "download_failed",
                    tribunal=entry.tribunal,
                    date=entry.date.isoformat(),
                    error=str(exc),
                )
                await summary.inc_error()
                if config.fail_fast:
                    if not first_error:
                        first_error.append(
                            f"Download failed: {entry.tribunal} {entry.date.isoformat()}"
                        )
                    abort_event.set()
            finally:
                download_queue.task_done()

    # ── Upload workers ───────────────────────────────────────────
    async def upload_worker(upload_client: httpx.AsyncClient) -> None:
        while True:
            if abort_event.is_set():
                return
            item = await upload_queue.get()
            if item is None:  # poison pill
                upload_queue.task_done()
                return
            failed = False
            try:
                # Quick HEAD check — skip if already on IA
                if await check_ia_file_exists(upload_client, item.tribunal, item.d):
                    await manifest.mark_uploaded(item.tribunal, item.d)
                    await summary.inc_upload()
                    item.path.unlink(missing_ok=True)
                    _notify_counts()
                    if config.observer:
                        config.observer.on_log(
                            f"[dim]Already on IA[/dim] {item.tribunal} {item.d.isoformat()}"
                        )
                    continue  # finally handles task_done()

                ok = await upload_zip(
                    upload_client,
                    item.item_id,
                    item.path,
                    circuit_breaker=circuit_breaker,
                )
                if not ok:
                    log.warning(
                        "upload_failed",
                        item_id=item.item_id,
                        date=item.d.isoformat(),
                    )
                    failed = True
                    if config.fail_fast:
                        if not first_error:
                            first_error.append(
                                f"Upload failed: {item.item_id} {item.d.isoformat()}"
                            )
                        abort_event.set()

                if not failed:
                    await manifest.mark_uploaded(item.tribunal, item.d)
                    await summary.inc_upload()
                    item.path.unlink(missing_ok=True)
                    _notify_counts()
                    if config.observer:
                        config.observer.on_log(
                            f"[green]Uploaded[/green] {item.tribunal} {item.d.isoformat()}"
                        )
            except Exception:
                log.exception(
                    "upload_exception",
                    item_id=item.item_id,
                    date=item.d.isoformat(),
                )
                if config.fail_fast:
                    if not first_error:
                        first_error.append(f"Upload exception: {item.item_id} {item.d.isoformat()}")
                    abort_event.set()
            finally:
                upload_queue.task_done()
            if abort_event.is_set():
                return

    # ── Launch all workers concurrently ──────────────────────────
    timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)

    async with (
        httpx.AsyncClient(timeout=timeout, follow_redirects=True) as check_client,
        httpx.AsyncClient(timeout=timeout, follow_redirects=True) as dl_client,
        create_upload_client(config.ia_auth) as upload_client,
    ):
        # Feeder: continuously pushes available entries into download queue.
        # Checkers mark entries as available; this feeder picks them up.
        # Polls every 2s for new available entries until checkers are done.
        async def feed_available() -> None:
            if config.dry_run:
                return
            seen: set[str] = set()
            while not abort_event.is_set():
                entries = manifest.entries_needing_upload()
                fed = 0
                for entry in entries:
                    if abort_event.is_set():
                        return
                    key = f"{entry.tribunal}/{entry.date.isoformat()}"
                    if key in seen:
                        continue
                    seen.add(key)
                    await download_queue.put(entry)
                    fed += 1
                if fed:
                    log.info("feeder_dispatched", count=fed)
                # If checkers are done and no more entries, stop
                if checkers_done.is_set() and not entries:
                    return
                await asyncio.sleep(2)

        feeder_task = asyncio.create_task(feed_available())

        # Worker allocation:
        # - Checkers: most workers (lightweight DJEN API calls, need parallelism)
        # - Downloaders: few (fast downloads, bottlenecked by upload queue)
        # - Uploaders: fixed (IA rate-limited, more workers don't help)
        checker_count = config.workers
        dl_count = max(1, config.workers // 4) if not config.dry_run else 0

        upload_tasks = [
            asyncio.create_task(upload_worker(upload_client)) for _ in range(UPLOAD_WORKERS)
        ]

        dl_tasks = [asyncio.create_task(download_worker(dl_client)) for _ in range(dl_count)]

        checker_tasks = [
            asyncio.create_task(checker_worker(check_client)) for _ in range(checker_count)
        ]

        log.info(
            "workers_started",
            checkers=checker_count,
            downloaders=dl_count,
            uploaders=UPLOAD_WORKERS,
        )

        # Wait for checkers to finish, then signal feeder
        await asyncio.gather(*checker_tasks, return_exceptions=True)
        checkers_done.set()
        await asyncio.gather(feeder_task, return_exceptions=True)

        # Signal download workers: no more work coming
        for _ in dl_tasks:
            await download_queue.put(None)

        # Wait for downloads to finish
        if dl_tasks:
            await asyncio.gather(*dl_tasks, return_exceptions=True)

        # Signal upload workers: no more work coming
        for _ in upload_tasks:
            await upload_queue.put(None)

        # Wait for uploads to drain
        remaining_s = max(0.0, deadline - time.monotonic())
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(upload_queue.join(), timeout=remaining_s)

        await asyncio.gather(*upload_tasks, return_exceptions=True)

    if first_error:
        log.error("pipeline_aborted", reason=first_error[0])


# ── Main entry point ─────────────────────────────────────────────────


async def run_sync(config: SyncConfig) -> int:
    """Manifest-driven sync: build → check+download+upload (concurrent)."""
    start_time = time.monotonic()
    deadline = start_time + config.deadline_minutes * 60
    summary = SyncSummary()
    abort_event = asyncio.Event()
    manifest = SyncManifest()

    # ── Load existing state ──────────────────────────────────────
    if config.observer:
        config.observer.on_phase("Loading manifest")

    await manifest.load_from_ia()
    manifest.load_from_disk(config.manifest_file)

    # ── Phase 1: Build manifest ──────────────────────────────────
    if config.observer:
        config.observer.on_phase("Building manifest")

    timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        tribunals = await get_tribunal_list(client, config.djen_proxy_url)

    if config.tribunal:
        tribunals = [config.tribunal.upper()]

    upper = config.start_date
    lower = config.lower_bound or date(2020, 1, 1)
    added = manifest.build(tribunals, lower, upper)
    pruned = manifest.prune()
    counts = manifest.counts()
    log.info(
        "manifest_built",
        tribunals=len(tribunals),
        total=counts.total,
        new_entries=added,
        pruned=pruned,
        already_uploaded=counts.uploaded,
    )
    if config.observer:
        config.observer.on_counts_updated(counts)

    # ── Pipeline: Check + Download + Upload (concurrent) ─────────
    if config.observer:
        config.observer.on_phase("Checking + Downloading + Uploading")

    interrupted = False
    try:
        await run_pipeline(manifest, config, abort_event, summary, deadline)
    except (KeyboardInterrupt, asyncio.CancelledError):
        interrupted = True
        log.warning("sync_interrupted")
    finally:
        # Always save manifest — even on Ctrl+C
        log.info("saving_manifest")
        manifest.save_to_disk(config.manifest_file)
        if not config.dry_run and not interrupted:
            await manifest.upload_to_ia(config.ia_auth)
            await manifest.upload_summary_to_ia(config.ia_auth)

    counts = manifest.counts()
    log.info(
        "sync_complete",
        downloads=summary.downloads,
        uploads=summary.uploads,
        errors=summary.errors,
        uploaded=counts.uploaded,
        available=counts.available,
        absent=counts.absent,
        unknown=counts.unknown,
    )

    if interrupted or abort_event.is_set():
        return 1
    return 1 if summary.errors > 0 else 0
