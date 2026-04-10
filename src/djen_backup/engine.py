from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Protocol

import httpx
import structlog

from djen_backup.archive import (
    CircuitBreaker,
    fetch_ia_existing,
    upload_zip,
)
from djen_backup.djen import DJENNotFoundError, download_zip, get_caderno_url
from djen_backup.inventory import ZipInventory
from djen_backup.tribunais import get_tribunal_list


if TYPE_CHECKING:
    from pathlib import Path

    from httpx import AsyncClient

log = structlog.get_logger()

# ── Protocols ───────────────────────────────────────────────────────


class SyncObserver(Protocol):
    """Interface for reporting sync progress to the UI."""

    def on_metadata_sync_start(self, tribunal: str, year: int) -> None: ...
    def on_metadata_sync_complete(self, tribunal: str, year: int, found: int) -> None: ...
    def on_gaps_discovered(self, tribunal: str, year: int, count: int) -> None: ...
    def on_item_start(self, tribunal: str, d: date) -> None: ...
    def on_item_complete(self, tribunal: str, d: date, status: str, url: str | None = None) -> None: ...
    def on_retry(self, tribunal: str, d: date, attempt: int, status: int, wait_s: float, body: str | None = None) -> None: ...
    def on_periodic_sync_start(self) -> None: ...
    def on_periodic_sync_complete(self) -> None: ...


# Constants
VERSION_EXPECTED = 2
STOP_THRESHOLD = 60
IA_BACKFILL_STATE_FILENAME = "backfill-state.json"
IA_STATE_ITEM = "causaganha-dashboard"
_IA_DOWNLOAD_URL = f"https://archive.org/download/{IA_STATE_ITEM}/{{}}"
_IA_S3_URL = f"https://s3.us.archive.org/{IA_STATE_ITEM}/{{}}"
HTTP_BAD_REQUEST = 400
HTTP_OK = 200


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
            last_checked_at=str(data.get("last_checked_at")) if data.get("last_checked_at") else None,
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

    async def advance_cursor(self, tribunal: str) -> None:
        async with self._lock:
            prog = self._tribunals[tribunal]
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
    url = _IA_DOWNLOAD_URL.format(filename)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        log.warning("state_download_failed", filename=filename, error=str(exc))
    return None


async def upload_state_to_ia(filename: str, data: dict, auth: str) -> bool:
    url = _IA_S3_URL.format(filename)
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

    start_date: date  # Newest date to scan
    lower_bound: date | None  # Oldest date to scan
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
    genesis_dates: dict[str, date] = field(default_factory=dict)
    observer: SyncObserver | None = None


@dataclass
class SyncSummary:
    """Statistics for the current run."""

    total: int = 0
    hits: int = 0
    cache_hits: int = 0
    empties: int = 0
    errors: int = 0
    ia_errors: int = 0
    scanned: int = 0
    stopped: int = 0
    skipped_deadline: int = 0
    skipped_circuit: int = 0
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

    async def inc_ia_error(self) -> None:
        async with self._lock:
            self.ia_errors += 1

    async def inc_skipped_deadline(self) -> None:
        async with self._lock:
            self.skipped_deadline += 1

    async def inc_skipped_circuit(self) -> None:
        async with self._lock:
            self.skipped_circuit += 1

    @property
    def processed(self) -> int:
        return self.hits + self.empties

    @property
    def attempted(self) -> int:
        return self.processed + self.errors + self.ia_errors

    @property
    def success_rate(self) -> float:
        if self.attempted == 0:
            return 1.0
        return self.processed / self.attempted


async def process_date(  # noqa: PLR0913
    client: AsyncClient,
    breaker: CircuitBreaker,
    tribunal: str,
    d: date,
    config: SyncConfig,
    state: SyncState,
    inventory: ZipInventory,
    summary: SyncSummary,
    deadline: float,
) -> str:
    """Process a single (tribunal, date) pair."""
    # 0. Deadline guard
    if time.monotonic() > deadline - 30:
        await summary.inc_skipped_deadline()
        return "skipped"

    # 1. Fast path: check inventory (Source of Truth)
    status = inventory.get_status(tribunal, d)
    if status == "uploaded":
        await state.record_hit(tribunal, d)
        await summary.inc_cache_hit()
        if config.observer:
            # URL for the item (containing the year's files)
            item_id = f"djen-{tribunal.lower()}-{d.year}"
            url = f"https://archive.org/download/{item_id}"
            config.observer.on_item_complete(tribunal, d, "hit", url=url)
        return "hit"
    if status == "absent":
        await state.record_empty(tribunal)
        await summary.inc_empty()
        if config.observer:
            config.observer.on_item_complete(tribunal, d, "empty")
        return "empty"

    if config.dry_run:
        log.info("sync_dry_run", tribunal=tribunal, date=d.isoformat())
        await summary.inc_hit()
        if config.observer:
            config.observer.on_item_complete(tribunal, d, "hit")
        return "hit"

    # 2. Circuit breaker guard
    if not await breaker.allow_request():
        await summary.inc_skipped_circuit()
        return "skipped"

    if config.observer:
        config.observer.on_item_start(tribunal, d)

    # 3. Fetch from DJEN
    zip_path: Path | None = None
    res_status = "error"
    try:
        zip_url = await get_caderno_url(client, config.djen_proxy_url, tribunal, d)
        zip_path = await download_zip(client, zip_url)
    except DJENNotFoundError as exc:
        if exc.reason in ("Not Found", "No publications"):
            await inventory.add_absent(tribunal, d)
            await state.record_empty(tribunal)
            await summary.inc_empty()
            res_status = "empty"
        else:
            await state.record_error(tribunal)
            await summary.inc_error()
            res_status = "error"
    except httpx.HTTPError:
        await state.record_error(tribunal)
        await summary.inc_error()
        res_status = "error"

    if res_status != "error":
        url = None
        if config.observer:
            config.observer.on_item_complete(tribunal, d, res_status, url=url)
        return res_status

    # 4. Upload to IA
    try:
        resp = await upload_zip(client, d, tribunal, zip_path, config.ia_auth, observer=config.observer)
        if resp.status_code < HTTP_BAD_REQUEST:
            await breaker.record_success()
            await inventory.add(tribunal, d)
            await state.record_hit(tribunal, d)
            await summary.inc_hit()
            res_status = "hit"
            item_id = f"djen-{tribunal.lower()}-{d.year}"
            url = f"https://archive.org/download/{item_id}"
        elif resp.status_code == HTTP_SERVICE_UNAVAILABLE:
            # Check if it was a saturation skip
            body = resp.text if resp.text else ""
            if "SlowDown" in body or "bucket_tasks_queued" in body:
                res_status = "saturated"
                url = None
            else:
                await breaker.record_failure()
                res_status = "error"
                url = None
        else:
            await breaker.record_failure()
            res_status = "error"
            url = None
    except Exception:
        await breaker.record_failure()
        res_status = "error"
        url = None
    finally:
        if zip_path:
            zip_path.unlink(missing_ok=True)

    if res_status == "error":
        await state.record_error(tribunal)
        await summary.inc_ia_error()

    if config.observer:
        config.observer.on_item_complete(tribunal, d, res_status, url=url)
    return res_status


async def run_sync(config: SyncConfig) -> int:
    """The unified sync entry point."""
    start_time = time.monotonic()
    deadline = start_time + config.deadline_minutes * 60

    # 0. Initial state & inventory
    inventory = ZipInventory()
    await inventory.load_from_ia()
    inventory.load_from_disk()
    await inventory.load_from_snapshot()

    local_state_data = None
    if config.state_file and config.state_file.exists():
        with contextlib.suppress(Exception):
            local_state_data = json.loads(config.state_file.read_text())

    remote_state_data = await download_state_from_ia(IA_BACKFILL_STATE_FILENAME)

    if remote_state_data:
        state = SyncState.from_dict(remote_state_data)
    elif local_state_data:
        state = SyncState.from_dict(local_state_data)
    else:
        state = SyncState()

    # 1. Prepare Workers
    timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        tribunals = await get_tribunal_list(client, config.djen_proxy_url)
        if config.tribunal:
            tribunals = [config.tribunal]

        summary = SyncSummary()
        breaker = CircuitBreaker(threshold=10, recovery_timeout=60.0)

        # Advance/Unstick logic
        for t in tribunals:
            await state.ensure_cursor_at_least(t, config.start_date)

        # 2. Main Scan (Year by Year)
        upper = config.start_date
        lower = config.lower_bound or date(2013, 1, 1)
        years = sorted(range(lower.year, upper.year + 1), reverse=True)

        last_ia_sync = time.monotonic()
        sync_interval_s = 180  # 3 minutes

        for year in years:
            if time.monotonic() > deadline - 60:
                break
            log.info("sync_year_starting", year=year)

            # 2a. Discovery Phase: Build interleaved work queue for the year
            # Group gaps by date so we can process all tribunals for a date, then move to next
            # This naturally rotates buckets (tribunals)
            tribunal_gaps: dict[str, list[date]] = {}
            for t in tribunals:
                prog = await state.get_or_init(t, config.start_date)
                if prog.stopped:
                    continue

                # Just-in-time metadata sync for items we haven't seen this year
                if not inventory.is_year_complete(t, year, upper, lower):
                    if config.observer:
                        config.observer.on_metadata_sync_start(t, year)
                    ia_dates = await fetch_ia_existing(client, t, year)
                    if ia_dates:
                        await inventory.add_many(t, set(ia_dates.keys()))
                    if config.observer:
                        config.observer.on_metadata_sync_complete(t, year, len(ia_dates))

                gaps = inventory.gaps_for_year(t, year, upper, lower)
                if gaps:
                    tribunal_gaps[t] = sorted(gaps, reverse=True)

            if not tribunal_gaps:
                continue

            # 2b. Interleave gaps: Round-Robin across tribunals
            # This is the "Hopping" strategy to avoid 503s
            work_queue: list[tuple[str, date]] = []
            max_gaps = max(len(g) for g in tribunal_gaps.values()) if tribunal_gaps else 0
            for i in range(max_gaps):
                for t in sorted(tribunal_gaps.keys()):
                    if i < len(tribunal_gaps[t]):
                        d = tribunal_gaps[t][i]
                        # Double check inventory here to be 100% sure we don't queue duplicates
                        if not inventory.has(t, d):
                            work_queue.append((t, d))

            log.info("sync_queue_ready", year=year, items=len(work_queue), tribunals=len(tribunal_gaps))

            # 2c. Worker Phase: Process the interleaved queue
            sem = asyncio.Semaphore(config.workers)
            consecutive_errors_map: dict[str, int] = {t: 0 for t in tribunal_gaps}

            async def worker_task(t: str, d: date) -> None:
                nonlocal last_ia_sync
                async with sem:
                    if time.monotonic() > deadline - 30:
                        return
                    if config.max_items and summary.hits >= config.max_items:
                        return

                    # Check if tribunal was stopped by a previous concurrent task
                    prog = await state.get_or_init(t, config.start_date)
                    if prog.stopped or consecutive_errors_map.get(t, 0) >= 3:
                        return

                    res = await process_date(
                        client, breaker, t, d, config, state, inventory, summary, deadline
                    )

                    # Periodic IA Sync (every 3 minutes)
                    if not config.dry_run and time.monotonic() - last_ia_sync > sync_interval_s:
                        last_ia_sync = time.monotonic()
                        if config.observer:
                            config.observer.on_periodic_sync_start()
                        await inventory.upload_to_ia(config.ia_auth)
                        await upload_state_to_ia(IA_BACKFILL_STATE_FILENAME, state.to_dict(), config.ia_auth)
                        if config.observer:
                            config.observer.on_periodic_sync_complete()

                    if res == "error":
                        consecutive_errors_map[t] += 1
                        if consecutive_errors_map[t] >= 3:
                            log.warning("sync_skipping_tribunal", tribunal=t, reason="3 consecutive errors")
                    elif res == "saturated":
                        # If a bucket is STILL saturated even with hopping, stop this tribunal for this run
                        consecutive_errors_map[t] = 99
                        log.warning("sync_switching_tribunal", tribunal=t, reason="bucket saturation (SlowDown)")
                    elif res in ("hit", "empty"):
                        consecutive_errors_map[t] = 0
                        await state.advance_cursor(t)

            # Gather all items for the current year
            await asyncio.gather(*(worker_task(t, d) for t, d in work_queue))

            # Checkpoint after each year
            inventory.save_to_disk()
            if config.state_file:
                config.state_file.write_text(json.dumps(state.to_dict(), indent=2))

    # 3. Finalization
    if not config.dry_run:
        await inventory.upload_to_ia(config.ia_auth)
        await upload_state_to_ia(IA_BACKFILL_STATE_FILENAME, state.to_dict(), config.ia_auth)

    duration_sec = time.monotonic() - start_time
    log.info(
        "sync_complete",
        hits=summary.hits,
        cache_hits=summary.cache_hits,
        empties=summary.empties,
        errors=summary.errors,
        ia_errors=summary.ia_errors,
        duration_s=round(duration_sec, 1),
        success_rate=f"{summary.success_rate:.1%}",
    )
    print(f"Collected {summary.hits} ZIPs in {duration_sec:.1f} seconds")

    if gh_output := os.getenv("GITHUB_OUTPUT"):
        from pathlib import Path

        with Path(gh_output).open("a") as f:
            f.write(f"uploaded={summary.hits}\n")
            f.write(f"errors={summary.errors}\n")
            f.write(f"empties={summary.empties}\n")

    return 0 if summary.success_rate >= 0.5 else 1
