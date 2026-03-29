"""Orchestration: discover gaps → download → upload."""

from __future__ import annotations

import asyncio
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import httpx
import structlog

from djen_backup.archive import (
    CircuitBreaker,
    fetch_ia_existing,
    upload_zip,
)
from djen_backup.djen import DJENNotFoundError, download_zip, get_caderno_url
from djen_backup.state import ItemStatus, State, load_state, save_state
from djen_backup.tribunais import get_tribunal_list


log = structlog.get_logger()

# HTTP status constants
HTTP_BAD_REQUEST = 400
SUCCESS_RATE_THRESHOLD = 0.5

_TRIBUNAL_RE = re.compile(r"^[A-Za-z0-9-]+$")


def validate_tribunal(code: str) -> str:
    """Validate a tribunal code against an allowlist pattern.

    Raises ``ValueError`` if the code contains unsafe characters.
    """
    if not _TRIBUNAL_RE.fullmatch(code):
        msg = f"Invalid tribunal code: {code!r} (must match {_TRIBUNAL_RE.pattern})"
        raise ValueError(msg)
    return code


# ── Data types ───────────────────────────────────────────────────────


@dataclass
class WorkItem:
    """Work item representing a (date, tribunal) pair to process."""

    date: date
    tribunal: str


@dataclass
class RunConfig:
    """Configuration for the backup pipeline run."""

    start_date: date
    end_date: date
    tribunal: str | None
    deadline_minutes: int
    max_items: int
    workers: int
    state_file: Path | None
    djen_proxy_url: str
    ia_auth: str
    dry_run: bool
    force_recheck: bool


@dataclass
class Summary:
    """Statistics tracking for a pipeline run."""

    total: int = 0
    uploaded: int = 0
    absent_marked: int = 0
    skipped_deadline: int = 0
    skipped_circuit: int = 0
    failed: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def inc_uploaded(self) -> None:
        """Increment the uploaded counter."""
        async with self._lock:
            self.uploaded += 1

    async def inc_absent(self) -> None:
        """Increment the absent marked counter."""
        async with self._lock:
            self.absent_marked += 1

    async def inc_skipped_deadline(self) -> None:
        """Increment the skipped due to deadline counter."""
        async with self._lock:
            self.skipped_deadline += 1

    async def inc_skipped_circuit(self) -> None:
        """Increment the skipped due to circuit breaker counter."""
        async with self._lock:
            self.skipped_circuit += 1

    async def inc_failed(self) -> None:
        """Increment the failed counter."""
        async with self._lock:
            self.failed += 1

    @property
    def processed(self) -> int:
        """Return total processed items (uploaded + absent marked)."""
        return self.uploaded + self.absent_marked

    @property
    def attempted(self) -> int:
        """Items that were actually attempted (excludes skipped)."""
        return self.processed + self.failed

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.attempted == 0:
            return 1.0
        return self.processed / self.attempted


# ── Gap discovery ────────────────────────────────────────────────────


def _date_range(start: date, end: date) -> list[date]:
    """Generate dates from *end* down to *start* (newest first)."""
    dates: list[date] = []
    current = end
    while current >= start:
        dates.append(current)
        current -= timedelta(days=1)
    return dates


async def _check_date(
    client: httpx.AsyncClient,
    d: date,
    tribunals: set[str],
    state: State,
    *,
    force_recheck: bool,
    semaphore: asyncio.Semaphore,
) -> list[WorkItem]:
    """Return work items for tribunals missing on *d*."""
    # Fast path: state says everything is done
    if not force_recheck:
        cached = await state.get_done_tribunals(d)
        remaining = tribunals - cached
        if not remaining:
            return []

    # Slow path: query IA metadata
    async with semaphore:
        ia_existing = await fetch_ia_existing(client, d)

    # Merge IA data into state
    for tribunal, status_str in ia_existing.items():
        status = ItemStatus.UPLOADED if status_str == "uploaded" else ItemStatus.ABSENT
        await state.mark(d, tribunal, status)

    all_done = await state.get_done_tribunals(d) if not force_recheck else set(ia_existing.keys())
    gaps = tribunals - all_done
    return [WorkItem(date=d, tribunal=t) for t in sorted(gaps)]


async def discover_gaps(
    client: httpx.AsyncClient,
    state: State,
    tribunals: list[str],
    start_date: date,
    end_date: date,
    *,
    force_recheck: bool,
) -> list[WorkItem]:
    """Build the work queue of (date, tribunal) pairs not yet on IA."""
    dates = _date_range(start_date, end_date)
    tribunal_set = set(tribunals)
    sem = asyncio.Semaphore(5)

    results = await asyncio.gather(
        *(
            _check_date(client, d, tribunal_set, state, force_recheck=force_recheck, semaphore=sem)
            for d in dates
        )
    )

    work: list[WorkItem] = []
    for items in results:
        work.extend(items)
    return work


# ── Item processing ──────────────────────────────────────────────────


async def _handle_djen_not_found_item(
    client: httpx.AsyncClient,
    breaker: CircuitBreaker,
    item: WorkItem,
    config: RunConfig,
    state: State,
    summary: Summary,
    exc: DJENNotFoundError,
) -> None:
    """Handle DJEN not found error by marking as absent in state."""
    log.info(
        "djen_not_found",
        date=item.date.isoformat(),
        tribunal=item.tribunal,
        status_code=exc.status_code,
    )
    await state.mark(item.date, item.tribunal, ItemStatus.ABSENT)
    await summary.inc_absent()


async def _handle_upload_to_ia(
    client: httpx.AsyncClient,
    breaker: CircuitBreaker,
    item: WorkItem,
    config: RunConfig,
    state: State,
    summary: Summary,
    zip_path: Path,
) -> None:
    """Upload ZIP to IA and handle response."""
    try:
        resp = await upload_zip(client, item.date, item.tribunal, zip_path, config.ia_auth)
        if resp.status_code < HTTP_BAD_REQUEST:
            await breaker.record_success()
            await state.mark(item.date, item.tribunal, ItemStatus.UPLOADED)
            await summary.inc_uploaded()
        else:
            log.error(
                "ia_upload_failed",
                date=item.date.isoformat(),
                tribunal=item.tribunal,
                status=resp.status_code,
            )
            await breaker.record_failure()
            await summary.inc_failed()
    except httpx.HTTPError as exc:
        log.exception(
            "ia_upload_error",
            date=item.date.isoformat(),
            tribunal=item.tribunal,
            exc_info=exc,
        )
        await breaker.record_failure()
        await summary.inc_failed()


async def process_item(
    client: httpx.AsyncClient,
    breaker: CircuitBreaker,
    item: WorkItem,
    state: State,
    config: RunConfig,
    deadline: float,
    summary: Summary,
) -> None:
    """Process a single (date, tribunal) work item.

    Downloads the ZIP from DJEN to a temporary file, then uploads it to IA.
    The temp file is cleaned up after processing regardless of outcome.
    """
    # Deadline guard
    if time.monotonic() > deadline - 30:
        log.info(
            "skipped_deadline",
            date=item.date.isoformat(),
            tribunal=item.tribunal,
        )
        await summary.inc_skipped_deadline()
        return

    # Circuit breaker guard
    if not await breaker.allow_request():
        log.info(
            "skipped_circuit_breaker",
            date=item.date.isoformat(),
            tribunal=item.tribunal,
        )
        await summary.inc_skipped_circuit()
        return

    if config.dry_run:
        log.info(
            "dry_run_skip",
            date=item.date.isoformat(),
            tribunal=item.tribunal,
        )
        await summary.inc_uploaded()
        return

    zip_path: Path | None = None
    try:
        zip_url = await get_caderno_url(client, config.djen_proxy_url, item.tribunal, item.date)
        zip_path = await download_zip(client, zip_url)
    except DJENNotFoundError as exc:
        await _handle_djen_not_found_item(client, breaker, item, config, state, summary, exc)
        return
    except httpx.HTTPError as exc:
        log.exception(
            "djen_download_error",
            date=item.date.isoformat(),
            tribunal=item.tribunal,
            exc_info=exc,
        )
        await summary.inc_failed()
        return

    # Upload to IA from the temp file
    try:
        await _handle_upload_to_ia(client, breaker, item, config, state, summary, zip_path)
    finally:
        if zip_path is not None:
            zip_path.unlink(missing_ok=True)


# ── Main orchestration ───────────────────────────────────────────────


async def run(config: RunConfig) -> int:
    """Execute the backup pipeline.  Returns the process exit code."""
    deadline = time.monotonic() + config.deadline_minutes * 60
    state = load_state(config.state_file)

    # Use a 30s timeout for read/write/connect as requested.
    timeout = httpx.Timeout(connect=30.0, read=30.0, write=30.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        # 1. Tribunal list
        all_tribunals = await get_tribunal_list(client, config.djen_proxy_url)
        if config.tribunal:
            validate_tribunal(config.tribunal)
            if config.tribunal in all_tribunals:
                all_tribunals = [config.tribunal]
            else:
                log.warning("tribunal_not_found", tribunal=config.tribunal)
                all_tribunals = [config.tribunal]

        # 2. Discover gaps
        log.info(
            "discovering_gaps",
            start=config.start_date.isoformat(),
            end=config.end_date.isoformat(),
            tribunals=len(all_tribunals),
        )
        work_queue = await discover_gaps(
            client,
            state,
            all_tribunals,
            config.start_date,
            config.end_date,
            force_recheck=config.force_recheck,
        )

        # Sort newest-first (already done by _date_range, but re-sort for safety)
        work_queue.sort(key=lambda w: w.date, reverse=True)

        # Cap
        if config.max_items and len(work_queue) > config.max_items:
            work_queue = work_queue[: config.max_items]

        if not work_queue:
            log.info("nothing_to_do")
            save_state(state, config.state_file)
            return 0

        log.info("work_queue_built", total=len(work_queue))

        # 3. Process — bounded concurrency with semaphore
        summary = Summary(total=len(work_queue))
        breaker = CircuitBreaker(threshold=5, recovery_timeout=60.0)

        # Use a temporary directory for ZIP downloads in this run
        tmp_dir = Path(tempfile.mkdtemp(prefix="djen-"))

        # Concurrency limit: maximum 10 simultaneous requests
        sem = asyncio.Semaphore(10)

        async def _process_with_semaphore(item: WorkItem) -> None:
            async with sem:
                log.info(
                    "process_item_start",
                    date=item.date.isoformat(),
                    tribunal=item.tribunal,
                )
                await process_item(client, breaker, item, state, config, deadline, summary)

        start_time = time.monotonic()
        try:
            await asyncio.gather(*(_process_with_semaphore(item) for item in work_queue))
        finally:
            # Clean up the temp directory
            shutil.rmtree(tmp_dir, ignore_errors=True)

        duration_sec = time.monotonic() - start_time

    # 4. Save state
    save_state(state, config.state_file)

    # 5. Summary
    log.info(
        "run_complete",
        total=summary.total,
        uploaded=summary.uploaded,
        absent_marked=summary.absent_marked,
        skipped_deadline=summary.skipped_deadline,
        skipped_circuit=summary.skipped_circuit,
        failed=summary.failed,
        success_rate=f"{summary.success_rate:.1%}",
        duration_sec=round(duration_sec, 2),
    )

    # Progress summary at end as requested
    print(f"Collected {summary.uploaded}/91 ZIPs in {duration_sec:.1f} seconds")

    # 6. Exit code: 0 if nothing to do or ≥50% success, else 1
    if summary.success_rate >= SUCCESS_RATE_THRESHOLD:
        return 0
    return 1
