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
from djen_backup.djen import (
    DJENNotFoundError,
    DJENRateLimitedError,
    download_zip,
    get_caderno_url,
)
from djen_backup.manifest import ManifestCounts, ManifestEntry, SyncManifest
from djen_backup.tribunais import get_tribunal_list


log = structlog.get_logger()

# ── Constants ────────────────────────────────────────────────────────

STAGING_DIR = Path("data/staging")
MAX_STAGED_FILES = 15
DJEN_SAFE_CONCURRENCY_FILE = Path("data/djen-safe-concurrency.json")
DEFAULT_DJEN_CONCURRENCY = 4


def load_djen_safe_concurrency() -> int:
    if not DJEN_SAFE_CONCURRENCY_FILE.exists():
        return DEFAULT_DJEN_CONCURRENCY
    try:
        import json

        data = json.loads(DJEN_SAFE_CONCURRENCY_FILE.read_text())
        return max(1, int(data.get("safe_concurrency", DEFAULT_DJEN_CONCURRENCY)))
    except (OSError, ValueError):
        return DEFAULT_DJEN_CONCURRENCY


def _save_safe_concurrency(value: int, *, reason: str) -> None:
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
    def on_phase(self, phase: str) -> None: ...
    def on_counts_updated(self, counts: ManifestCounts) -> None: ...
    def on_log(self, message: str) -> None: ...
    def on_subtask(self, name: str, total: int) -> None: ...
    def on_subtask_advance(self, name: str, delta: int = 1) -> None: ...
    def on_subtask_done(self, name: str) -> None: ...


# ── Data structures ──────────────────────────────────────────────────


class StagedItem(NamedTuple):
    item_id: str
    d: date
    tribunal: str
    path: Path


@dataclass
class SyncConfig:
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
    check_only: bool = False
    upload_only: bool = False
    observer: ManifestObserver | None = None


@dataclass
class SyncSummary:
    downloads: int = 0
    uploads: int = 0
    errors: int = 0
    initial_uploaded: int = 0
    initial_absent: int = 0
    initial_unknown: int = 0
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
    import random

    # ── Phase 0: Discovery ──
    existing_items: set[tuple[str, int]] = set()
    if not config.upload_only:
        log.info("ia_discovery_starting")
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0), follow_redirects=True) as client:
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
                for d in resp.json()["response"]["docs"]:
                    ident = d["identifier"]
                    parts = ident.rsplit("-", 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        existing_items.add((parts[0][5:].upper(), int(parts[1])))
                log.info("ia_items_discovered", count=len(existing_items))
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                log.warning("ia_search_failed_fallback", error=str(exc))
                existing_items = {
                    (e.tribunal, e.date.year)
                    for e in manifest._entries.values()
                    if e.ia_status != "uploaded"
                }

    # Build check priority
    from collections import defaultdict

    uploaded_by_tribunal: dict[str, list[date]] = defaultdict(list)
    for e in manifest._entries.values():
        if e.ia_status == "uploaded":
            uploaded_by_tribunal[e.tribunal].append(e.date)
    for dates in uploaded_by_tribunal.values():
        dates.sort()

    def _is_adjacent(entry: ManifestEntry) -> bool:
        uploads = uploaded_by_tribunal.get(entry.tribunal)
        if not uploads:
            return False
        for up in uploads:
            if abs((up - entry.date).days) <= 30:
                return True
        return False

    adjacent_entries, isolated_entries = [], []
    for e in manifest._entries.values():
        if e.ia_status != "" or e.djen_status != "":
            continue
        if _is_adjacent(e):
            adjacent_entries.append(e)
        else:
            isolated_entries.append(e)

    random.shuffle(adjacent_entries)
    random.shuffle(isolated_entries)
    unknown_entries = adjacent_entries + isolated_entries

    await anyio.Path(STAGING_DIR).mkdir(parents=True, exist_ok=True)

    check_queue: asyncio.Queue[ManifestEntry] = asyncio.Queue()
    for entry in unknown_entries:
        check_queue.put_nowait(entry)

    download_queue: asyncio.Queue[ManifestEntry | None] = asyncio.Queue(maxsize=MAX_STAGED_FILES)
    upload_queue: asyncio.Queue[StagedItem | None] = asyncio.Queue(maxsize=MAX_STAGED_FILES)

    backlog = manifest.entries_needing_upload()
    if backlog:
        log.info("backlog_priority_load", count=len(backlog))

    circuit_breaker = CircuitBreaker()
    last_save = last_ia_upload = time.monotonic()
    save_interval, ia_upload_interval = 180.0, 600.0
    checkers_done = asyncio.Event()

    last_stats_log = last_notify = time.monotonic()
    stats_log_interval, notify_interval = 30.0, 0.5

    djen_breaker = CircuitBreaker(threshold=5, recovery_timeout=30.0)
    djen_limiter = AsyncLimiter(max_rate=1, time_period=1)

    async def _check_djen_breaker() -> bool:
        while not await djen_breaker.allow_request():
            if abort_event.is_set() or time.monotonic() > deadline:
                return False
            await asyncio.sleep(5.0)
        return True

    _ia_upload_running = False

    async def _upload_manifest_background() -> None:
        nonlocal _ia_upload_running
        if _ia_upload_running:
            return
        _ia_upload_running = True
        try:
            if await manifest.upload_to_ia(config.ia_auth):
                await manifest.upload_summary_to_ia(config.ia_auth)
        except (httpx.HTTPError, OSError) as exc:
            log.warning("manifest_upload_background_failed", error=str(exc))
        finally:
            _ia_upload_running = False

    def _notify_counts() -> None:
        nonlocal last_stats_log, last_notify
        now = time.monotonic()
        if now - last_notify < notify_interval:
            return
        last_notify = now
        c = manifest.counts()
        if config.observer:
            config.observer.on_counts_updated(c)
        if now - last_stats_log > stats_log_interval:
            last_stats_log = now
            log.info("progress", uploaded=c.uploaded, pending=c.available, unknown=c.unknown)

    synced_ia_items: set[tuple[str, int]] = set()
    ia_sync_lock = asyncio.Lock()

    async def checker_worker(client: httpx.AsyncClient) -> None:
        nonlocal last_save, last_ia_upload
        while not abort_event.is_set() and time.monotonic() < deadline:
            try:
                entry = check_queue.get_nowait()
            except asyncio.QueueEmpty:
                return

            item_key = (entry.tribunal, entry.date.year)
            if item_key in existing_items and item_key not in synced_ia_items:
                async with ia_sync_lock:
                    if item_key not in synced_ia_items:
                        try:
                            ia_dates = await fetch_ia_existing(
                                client, entry.tribunal, entry.date.year
                            )
                            if ia_dates:
                                await manifest.mark_ia_uploaded(
                                    entry.tribunal, set(ia_dates.keys())
                                )
                            synced_ia_items.add(item_key)
                            _notify_counts()
                        except httpx.HTTPError as exc:
                            log.warning(
                                "ia_metadata_sync_failed",
                                tribunal=entry.tribunal,
                                year=entry.date.year,
                                error=str(exc),
                            )

            if entry.ia_status == "uploaded":
                continue
            if not await _check_djen_breaker():
                return

            try:
                async with djen_limiter:
                    await get_caderno_url(client, config.djen_proxy_url, entry.tribunal, entry.date)
                raw_status = "200"
            except DJENNotFoundError as exc:
                raw_status = str(exc.status_code)
            except DJENRateLimitedError:
                # 403 / CloudFront block — transient, do NOT trip the breaker.
                raw_status = "403"
            except (httpx.HTTPError, asyncio.TimeoutError) as exc:
                log.warning(
                    "djen_check_error",
                    tribunal=entry.tribunal,
                    date=entry.date.isoformat(),
                    error=str(exc),
                )
                raw_status = "error"

            await manifest.mark_djen_raw(entry.tribunal, entry.date, raw_status)
            if raw_status in ("429", "timeout", "error"):
                await djen_breaker.record_failure()
            elif raw_status != "403":
                await djen_breaker.record_success()

            _notify_counts()
            if time.monotonic() - last_save > save_interval:
                last_save = time.monotonic()
                manifest.save_to_disk(config.manifest_file)
            if time.monotonic() - last_ia_upload > ia_upload_interval and not config.dry_run:
                last_ia_upload = time.monotonic()
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
                async with djen_limiter:
                    async for attempt in tenacity.AsyncRetrying(
                        stop=tenacity.stop_after_attempt(3),
                        wait=tenacity.wait_exponential(multiplier=2, min=4, max=10),
                        retry=tenacity.retry_if_exception_type(DJENNotFoundError),
                        reraise=True,
                    ):
                        with attempt:
                            # IMPORTANT: The proxy URL is used to fetch the file, NOT the direct DJEN URL
                            # to avoid Geofencing 403s on GitHub Runners.
                            url = await get_caderno_url(
                                client, config.djen_proxy_url, entry.tribunal, entry.date
                            )
                            zip_path = await download_zip(client, url)

                item_id = get_ia_item_id(entry.tribunal, entry.date)
                dest_dir = STAGING_DIR / item_id
                dest_dir.mkdir(parents=True, exist_ok=True)
                final_path = (
                    dest_dir / f"djen-{entry.date.isoformat()}-{entry.tribunal.upper()}.zip"
                )
                await asyncio.to_thread(shutil.move, str(zip_path), str(final_path))
                await summary.inc_download()
                await upload_queue.put(StagedItem(item_id, entry.date, entry.tribunal, final_path))
            except (httpx.HTTPError, OSError, DJENNotFoundError, DJENRateLimitedError) as exc:
                log.warning(
                    "download_failed",
                    tribunal=entry.tribunal,
                    date=entry.date.isoformat(),
                    error=str(exc),
                )
                await summary.inc_error()
            finally:
                download_queue.task_done()

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
                    if config.observer:
                        config.observer.on_log(f"[dim]Already on IA[/dim] {item.tribunal} {item.d}")
                    item.path.unlink(missing_ok=True)
                else:
                    try:
                        ok = await upload_zip(
                            upload_client,
                            item.item_id,
                            item.path,
                            circuit_breaker=circuit_breaker,
                            try_lock=True,
                        )
                    except ItemBusyError:
                        # Another worker holds the per-item lock — re-queue this
                        # item and pick a different one rather than blocking on
                        # the same bucket. Use put_nowait to avoid deadlocking
                        # the bounded queue; if it's saturated, drop the staged
                        # file (the manifest still flags the entry as available
                        # so the next run re-feeds it).
                        log.debug("upload_item_busy_requeue", item_id=item.item_id)
                        await asyncio.sleep(0.25)
                        try:
                            upload_queue.put_nowait(item)
                        except asyncio.QueueFull:
                            log.info("upload_requeue_dropped", item_id=item.item_id)
                            item.path.unlink(missing_ok=True)
                    else:
                        if ok:
                            await manifest.mark_uploaded(item.tribunal, item.d)
                            await summary.inc_upload()
                            if config.observer:
                                config.observer.on_log(
                                    f"[green]Uploaded[/green] {item.tribunal} {item.d}"
                                )
                        elif config.fail_fast:
                            abort_event.set()
                        item.path.unlink(missing_ok=True)
            except (httpx.HTTPError, OSError) as exc:
                log.warning("upload_exception", item_id=item.item_id, error=str(exc))
            finally:
                upload_queue.task_done()

    async with (
        httpx.AsyncClient(timeout=httpx.Timeout(15.0), follow_redirects=True) as check_client,
        httpx.AsyncClient(timeout=httpx.Timeout(120.0), follow_redirects=True) as dl_client,
        create_upload_client(config.ia_auth) as upload_client,
    ):

        async def feed_available() -> None:
            initial_backlog = backlog[: config.max_items] if config.max_items else backlog
            for entry in initial_backlog:
                await download_queue.put(entry)
            seen = {f"{e.tribunal}/{e.date.isoformat()}" for e in backlog}
            while not abort_event.is_set():
                if config.max_items and summary.downloads >= config.max_items:
                    return
                entries = manifest.entries_needing_upload()
                for entry in entries:
                    key = f"{entry.tribunal}/{entry.date.isoformat()}"
                    if key not in seen:
                        seen.add(key)
                        await download_queue.put(entry)
                if checkers_done.is_set() and not entries:
                    return
                await asyncio.sleep(5)

        feeder_task = asyncio.create_task(feed_available())
        checker_tasks = [
            asyncio.create_task(checker_worker(check_client)) for _ in range(min(2, config.workers))
        ]
        dl_tasks = [asyncio.create_task(download_worker(dl_client))]
        upload_tasks = [
            asyncio.create_task(upload_worker(upload_client)) for _ in range(config.workers)
        ]

        await asyncio.gather(*checker_tasks, return_exceptions=True)
        checkers_done.set()
        await asyncio.gather(feeder_task, return_exceptions=True)
        for _ in dl_tasks:
            await download_queue.put(None)
        await asyncio.gather(*dl_tasks, return_exceptions=True)
        for _ in upload_tasks:
            await upload_queue.put(None)
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(
                upload_queue.join(), timeout=max(0.0, deadline - time.monotonic())
            )
        await asyncio.gather(*upload_tasks, return_exceptions=True)


async def run_sync(config: SyncConfig) -> tuple[int, SyncSummary]:
    summary = SyncSummary()
    abort_event = asyncio.Event()
    manifest = SyncManifest()
    await manifest.load_from_ia()
    manifest.load_from_disk(config.manifest_file)
    counts_init = manifest.counts()
    summary.initial_uploaded, summary.initial_absent, summary.initial_unknown = (
        counts_init.uploaded,
        counts_init.absent,
        counts_init.unknown,
    )

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0), follow_redirects=True) as client:
        tribunals = await get_tribunal_list(client, config.djen_proxy_url)
    if config.tribunal:
        tribunals = [config.tribunal.upper()]
    manifest.build(tribunals, config.lower_bound or date(2020, 1, 1), config.start_date)
    manifest.prune()
    if config.observer:
        config.observer.on_counts_updated(manifest.counts())

    try:
        await run_pipeline(
            manifest, config, abort_event, summary, time.monotonic() + config.deadline_minutes * 60
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        manifest.save_to_disk(config.manifest_file)
        if not config.dry_run:
            if await manifest.upload_to_ia(config.ia_auth):
                await manifest.upload_summary_to_ia(config.ia_auth)

    summary.final_counts = manifest.counts()
    return (1 if summary.errors > 0 or abort_event.is_set() else 0), summary
