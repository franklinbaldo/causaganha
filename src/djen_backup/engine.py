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
    import random

    # ── Phase 0: Sync IA metadata upfront (skip if done recently) ──
    # Fetch IA metadata for every (tribunal, year) pair that has
    # unknown or available entries. Skip if synced within the last
    # 6 hours (tracked via data/.ia-sync-timestamp).
    from datetime import UTC, datetime, timedelta

    ia_sync_sentinel = Path("data/.ia-sync-timestamp")
    sync_skip_window = timedelta(hours=6)
    should_sync_ia = True
    if ia_sync_sentinel.exists():
        try:
            last_sync = datetime.fromisoformat(ia_sync_sentinel.read_text().strip())
            if datetime.now(UTC) - last_sync < sync_skip_window:
                should_sync_ia = False
                log.info("ia_sync_skipped", last_sync=last_sync.isoformat())
        except (ValueError, OSError):
            pass

    items_to_sync = {
        (e.tribunal, e.date.year)
        for e in manifest._entries.values()
        if e.ia_status != "uploaded"
    } if should_sync_ia else set()

    if items_to_sync:
        log.info("ia_sync_starting", items=len(items_to_sync))
        if config.observer:
            config.observer.on_subtask("IA sync", len(items_to_sync))
        timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            sem = asyncio.Semaphore(config.workers * 2)

            async def _sync_item(tribunal: str, year: int) -> int:
                async with sem:
                    try:
                        ia_dates = await fetch_ia_existing(client, tribunal, year)
                    except (httpx.HTTPError, httpx.RequestError):
                        return 0
                    finally:
                        if config.observer:
                            config.observer.on_subtask_advance("IA sync")
                    if ia_dates:
                        return await manifest.mark_ia_uploaded(
                            tribunal, set(ia_dates.keys())
                        )
                    return 0

            results = await asyncio.gather(
                *[_sync_item(t, y) for t, y in items_to_sync],
                return_exceptions=True,
            )
            total_new = sum(r for r in results if isinstance(r, int))
            log.info("ia_sync_complete", items=len(items_to_sync), newly_marked=total_new)
        # Write sentinel timestamp so subsequent runs skip IA sync
        ia_sync_sentinel.parent.mkdir(parents=True, exist_ok=True)
        ia_sync_sentinel.write_text(datetime.now(UTC).isoformat())
        if config.observer:
            config.observer.on_subtask_done("IA sync")
            config.observer.on_counts_updated(manifest.counts())

    # Build a shuffled flat queue of ALL unknown entries across all tribunals.
    # Workers grab one entry at a time, maximum parallelism.
    unknown_entries: list[ManifestEntry] = [
        e for e in manifest._entries.values()
        if e.ia_status == "" and e.djen_status == ""
    ]
    random.shuffle(unknown_entries)

    if not unknown_entries:
        entries_to_upload = manifest.entries_needing_upload()
        if not entries_to_upload:
            log.info("pipeline_nothing_to_do")
            return

    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    check_queue: asyncio.Queue[ManifestEntry] = asyncio.Queue()
    for entry in unknown_entries:
        check_queue.put_nowait(entry)

    download_queue: asyncio.Queue[ManifestEntry | None] = asyncio.Queue(maxsize=MAX_STAGED_FILES)
    upload_queue: asyncio.Queue[StagedItem | None] = asyncio.Queue(maxsize=MAX_STAGED_FILES)

    circuit_breaker = CircuitBreaker()
    first_error: list[str] = []
    last_save = time.monotonic()
    save_interval = 180.0
    checkers_done = asyncio.Event()


    last_stats_log = time.monotonic()
    last_notify = time.monotonic()
    stats_log_interval = 30.0  # log stats every 30s for CI/pipes
    notify_interval = 0.5  # throttle observer updates to 2 Hz

    # Adaptive throttle via CircuitBreaker — same pattern used for IA uploads.
    # Trips after 5 consecutive 403 CloudFront blocks, opens for 30s,
    # doubles timeout on repeated failure (capped at 5 min).
    djen_breaker = CircuitBreaker(threshold=5, recovery_timeout=30.0)

    async def _check_djen_breaker() -> bool:
        """Wait for the DJEN circuit breaker, return True if we can proceed."""
        while not await djen_breaker.allow_request():
            await asyncio.sleep(5.0)
            if abort_event.is_set() or time.monotonic() > deadline:
                return False
        return True

    def _notify_counts() -> None:
        nonlocal last_stats_log, last_notify
        now = time.monotonic()
        # Throttle — counts() scans 157K entries, blocks event loop
        if now - last_notify < notify_interval:
            return
        last_notify = now
        c = manifest.counts()
        if config.observer:
            config.observer.on_counts_updated(c)
        if now - last_stats_log > stats_log_interval:
            last_stats_log = now
            log.info(
                "progress",
                uploaded=c.uploaded,
                pending=c.available,
                absent=c.absent,
                unknown=c.unknown,
                total=c.total,
            )

    # ── Checker workers ──────────────────────────────────────────
    # Each worker grabs ONE entry from the shuffled queue and checks it.
    # Maximum parallelism: 8 workers = 8 concurrent DJEN calls for 8
    # different (tribunal, date) pairs.
    async def checker_worker(client: httpx.AsyncClient) -> None:
        nonlocal last_save
        while True:
            if abort_event.is_set():
                return
            if time.monotonic() > deadline:
                return

            try:
                entry = check_queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            try:
                if config.dry_run:
                    continue

                # Wait for circuit breaker (opens when DJEN rate-limits us)
                if not await _check_djen_breaker():
                    return

                # DJEN check — record the raw response code.
                # ANY exception here just gets recorded as raw; worker never dies.
                raw_status = "error"
                try:
                    await get_caderno_url(
                        client, config.djen_proxy_url, entry.tribunal, entry.date
                    )
                    raw_status = "200"
                except DJENNotFoundError as exc:
                    raw_status = str(exc.status_code)
                except httpx.HTTPStatusError as exc:
                    raw_status = str(exc.response.status_code)
                except httpx.TimeoutException:
                    raw_status = "timeout"
                except (httpx.HTTPError, httpx.RequestError, RuntimeError) as exc:
                    error_str = str(exc)
                    if "403" in error_str or "CloudFront" in error_str:
                        raw_status = "403"
                    else:
                        log.debug(
                            "djen_check_error",
                            tribunal=entry.tribunal,
                            date=entry.date.isoformat(),
                            error=error_str,
                        )

                await manifest.mark_djen_raw(entry.tribunal, entry.date, raw_status)

                # Feed circuit breaker: 403/timeout = failure, others = success
                if raw_status in ("403", "timeout", "error"):
                    await djen_breaker.record_failure()
                else:
                    await djen_breaker.record_success()

                _notify_counts()

                # Periodic save
                now = time.monotonic()
                if now - last_save > save_interval:
                    last_save = now
                    manifest.save_to_disk(config.manifest_file)

            except (httpx.HTTPError, httpx.RequestError, OSError) as exc:
                log.warning(
                    "checker_error",
                    tribunal=entry.tribunal,
                    date=entry.date.isoformat(),
                    error=str(exc),
                )
                if config.fail_fast:
                    if not first_error:
                        first_error.append(
                            f"Checker error: {entry.tribunal} {entry.date.isoformat()}"
                        )
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

                # Fetch fresh URL with retries — DJEN is inconsistent and
                # sometimes returns 404 on a date that IS available moments later
                url = None
                for attempt in range(4):
                    try:
                        url = await get_caderno_url(
                            client, config.djen_proxy_url, entry.tribunal, entry.date
                        )
                        break
                    except DJENNotFoundError:
                        if attempt >= 3:
                            raise
                        await asyncio.sleep(2**attempt)  # 1s, 2s, 4s
                assert url is not None
                zip_path = await download_zip(client, url)

                # Stage
                item_id = get_ia_item_id(entry.tribunal, entry.date)
                dest_dir = STAGING_DIR / item_id
                dest_dir.mkdir(parents=True, exist_ok=True)
                filename = f"djen-{entry.date.isoformat()}-{entry.tribunal.upper()}.zip"
                final_path = dest_dir / filename
                await asyncio.to_thread(shutil.move, str(zip_path), str(final_path))

                await summary.inc_download()
                log.debug("staged", tribunal=entry.tribunal, date=entry.date.isoformat())

                # Enqueue for upload
                await upload_queue.put(StagedItem(item_id, entry.date, entry.tribunal, final_path))

            except DJENNotFoundError:
                # Checker said available, but fresh URL now returns 404.
                # Leave as available — feeder's `seen` set prevents retry
                # this run; next run's checker will re-verify.
                log.warning(
                    "download_skipped_404",
                    tribunal=entry.tribunal,
                    date=entry.date.isoformat(),
                )

            except (httpx.HTTPError, httpx.RequestError, OSError) as exc:
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

                # Try to acquire item lock — if another worker is uploading
                # to this item, re-queue and grab another instead of blocking
                try:
                    ok = await upload_zip(
                        upload_client,
                        item.item_id,
                        item.path,
                        circuit_breaker=circuit_breaker,
                        try_lock=True,
                    )
                except ItemBusyError:
                    # Another worker has this item — send to back of queue
                    await upload_queue.put(item)
                    await asyncio.sleep(0.1)  # yield to avoid busy-spinning
                    continue  # finally handles task_done()
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
            except (httpx.HTTPError, httpx.RequestError, RuntimeError, OSError) as exc:
                # RuntimeError catches "client has been closed" cascade during shutdown
                log.warning(
                    "upload_exception",
                    item_id=item.item_id,
                    date=item.d.isoformat(),
                    error=str(exc),
                )
                # Don't fail-fast on upload exceptions — they're often transient
                # (IA rate-limit, network glitches, client cascade during shutdown).
                # Next run will retry.
            finally:
                upload_queue.task_done()
            if abort_event.is_set():
                return

    # ── Launch all workers concurrently ──────────────────────────
    # Short timeout for check (cheap API calls) — long timeout for download
    # (heavy transfers). If a check hangs, worker won't block for 2 minutes.
    check_timeout = httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=10.0)
    dl_timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)

    async with (
        httpx.AsyncClient(timeout=check_timeout, follow_redirects=True) as check_client,
        httpx.AsyncClient(timeout=dl_timeout, follow_redirects=True) as dl_client,
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

        # Worker allocation — respects --check-only and --upload-only flags
        if config.upload_only:
            checker_count = 0
        else:
            checker_count = config.workers

        if config.check_only or config.dry_run:
            dl_count = 0
            upload_count = 0
        else:
            dl_count = max(1, config.workers // 4)
            upload_count = config.workers

        upload_tasks = [
            asyncio.create_task(upload_worker(upload_client)) for _ in range(upload_count)
        ]

        dl_tasks = [asyncio.create_task(download_worker(dl_client)) for _ in range(dl_count)]

        checker_tasks = [
            asyncio.create_task(checker_worker(check_client)) for _ in range(checker_count)
        ]

        log.info(
            "workers_started",
            checkers=checker_count,
            downloaders=dl_count,
            uploaders=upload_count,
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
