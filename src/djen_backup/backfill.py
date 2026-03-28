from __future__ import annotations
import anyio

"""Backfill engine — scan historical dates per tribunal with 60-empty-day stop rule.

For each tribunal, scans backward one day at a time.  When 60 consecutive
*authoritative* empties are observed the tribunal is marked stopped and
skipped on future runs.  Errors and timeouts never count as empty.
"""


import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import contextlib
import httpx
import structlog

import httpx

from djen_backup.archive import (
    CircuitBreaker,
    upload_zip,
)
from djen_backup.djen import DJENNotFoundError, download_zip, get_caderno_url
from djen_backup.runner import validate_tribunal
from djen_backup.state import ItemStatus, State, load_state, save_state
from djen_backup.tribunais import get_tribunal_list


if TYPE_CHECKING:
    from pathlib import Path

log = structlog.get_logger()

STOP_THRESHOLD = 60

# ── Per-tribunal progress ────────────────────────────────────────────


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
        """Convert TribunalProgress to dictionary for serialization."""
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
        """Create TribunalProgress from dictionary."""
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

        last_checked = data.get("last_checked_at")
        last_result = data.get("last_result")

        raw_streak = data.get("empty_streak", 0)
        streak = int(raw_streak) if isinstance(raw_streak, (int, float, str)) else 0

        return cls(
            cursor_date=date.fromisoformat(cursor_raw),
            empty_streak=streak,
            stopped=bool(data.get("stopped", False)),
            stop_boundary=stop_boundary,
            last_hit_date=last_hit,
            last_checked_at=str(last_checked) if last_checked else None,
            last_result=str(last_result) if last_result else None,
        )


# ── Backfill state ───────────────────────────────────────────────────


class BackfillState:
    """Per-tribunal backfill progress tracking with JSON persistence.

    All mutation methods are protected by an asyncio.Lock.
    """

    def __init__(self) -> None:
        """Initialize the backfill state with empty tribunals and a lock."""
        self._tribunals: dict[str, TribunalProgress] = {}
        self._lock = asyncio.Lock()

    async def get_or_init(self, tribunal: str, start_date: date) -> TribunalProgress:
        """Return existing progress or create a new one starting at *start_date*."""
        async with self._lock:
            if tribunal not in self._tribunals:
                self._tribunals[tribunal] = TribunalProgress(cursor_date=start_date)
            return self._tribunals[tribunal]

    async def record_hit(self, tribunal: str, d: date) -> None:
        """Record a successful download (resets empty streak)."""
        async with self._lock:
            prog = self._tribunals[tribunal]
            prog.empty_streak = 0
            prog.stop_boundary = None
            prog.last_hit_date = d
            prog.last_result = "hit"
            prog.last_checked_at = datetime.now(tz=UTC).isoformat()

    async def record_empty(self, tribunal: str) -> bool:
        """Record an authoritative empty.  Returns ``True`` if tribunal just stopped."""
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
        """Record a non-authoritative error (does NOT increment streak)."""
        async with self._lock:
            prog = self._tribunals[tribunal]
            prog.last_result = "error"
            prog.last_checked_at = datetime.now(tz=UTC).isoformat()

    async def advance_cursor(self, tribunal: str) -> None:
        """Move the cursor one day backward."""
        async with self._lock:
            prog = self._tribunals[tribunal]
            prog.cursor_date -= timedelta(days=1)

    async def reset_tribunal(self, tribunal: str) -> bool:
        """Reset a stopped tribunal.  Returns ``True`` if it was found."""
        async with self._lock:
            if tribunal in self._tribunals:
                prog = self._tribunals[tribunal]
                prog.stopped = False
                prog.empty_streak = 0
                return True
            return False

    async def stop_at_boundary(self, tribunal: str) -> None:
        """Mark tribunal as stopped because it hit the historical boundary."""
        async with self._lock:
            prog = self._tribunals[tribunal]
            prog.stopped = True
            prog.stop_boundary = None

    async def ensure_cursor_at_least(self, tribunal: str, min_date: date) -> bool:
        """Advance the tribunal's cursor to *min_date* if it is older.

        Also un-stops the tribunal when advanced, since new dates may have
        publications.  Returns ``True`` if the cursor was changed.
        """
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
        """Return a snapshot of all tribunal progress (not locked — read-only use)."""
        return dict(self._tribunals)

    def tribunal_count(self) -> int:
        """Return the number of tribunals being tracked."""
        return len(self._tribunals)

    # ── Serialisation ────────────────────────────────────────────────

    def to_dict(self) -> dict[str, object]:
        """Convert BackfillState to dictionary for serialization."""
        return {
            "version": 2,
            "updated_at": datetime.now(tz=UTC).isoformat(),
            "tribunals": {k: v.to_dict() for k, v in self._tribunals.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> BackfillState:
        """Create BackfillState from dictionary."""
        state = cls()
        if data.get("version") != 2:
            return state

        tribunals = data.get("tribunals")
        if isinstance(tribunals, dict):
            for code, raw in tribunals.items():
                if isinstance(code, str) and isinstance(raw, dict):
                    try:
                        state._tribunals[code] = TribunalProgress.from_dict(raw)
                    except (ValueError, TypeError):
                        log.warning("backfill_state_skip_entry", tribunal=code)
        return state


def load_backfill_state(path: Path | None) -> BackfillState:
    """Load backfill state from *path*, returning empty state on any error."""
    if path is None or not path.is_file():
        log.info("backfill_state_miss", path=str(path))
        return BackfillState()
    try:
        raw: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
        state = BackfillState.from_dict(raw)
        log.info(
            "backfill_state_loaded",
            path=str(path),
            tribunals=state.tribunal_count(),
        )
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("backfill_state_corrupt", path=str(path), error=str(exc))
        state = BackfillState()
    return state


def save_backfill_state(state: BackfillState, path: Path | None) -> None:
    """Persist backfill state.  No-op when *path* is ``None``."""
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")


# ── Backfill config & summary ────────────────────────────────────────


@dataclass
class BackfillConfig:
    """Configuration for the backfill engine."""

    start_date: date
    lower_bound: date | None
    tribunal: str | None
    deadline_minutes: int
    max_items: int
    workers: int
    backfill_state_file: Path | None
    state_file: Path | None
    djen_proxy_url: str
    ia_auth: str
    dry_run: bool
    skip_absent_markers: bool = False
    publish_live_status: bool = False
    genesis_dates: dict[str, date] = field(default_factory=dict)


@dataclass
class BackfillSummary:
    """Summary of backfill execution statistics."""

    hits: int = 0
    empties: int = 0
    errors: int = 0  # DJEN source errors (download failed, proxy down)
    ia_errors: int = 0  # IA upload errors (our infra broken — fail loudly)
    tribunals_scanned: int = 0
    tribunals_stopped: int = 0
    tribunals_skipped_stopped: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def inc_hit(self) -> None:
        """Increment the hit counter."""
        async with self._lock:
            self.hits += 1

    async def inc_empty(self) -> None:
        """Increment the empties counter."""
        async with self._lock:
            self.empties += 1

    async def inc_error(self) -> None:
        """Increment the errors counter."""
        async with self._lock:
            self.errors += 1

    async def inc_ia_error(self) -> None:
        """Increment the IA errors counter."""
        async with self._lock:
            self.ia_errors += 1

    async def inc_stopped(self) -> None:
        """Increment the tribunals stopped counter."""
        async with self._lock:
            self.tribunals_stopped += 1

    async def inc_skipped_stopped(self) -> None:
        """Increment the tribunals skipped stopped counter."""
        async with self._lock:
            self.tribunals_skipped_stopped += 1

    async def inc_scanned(self) -> None:
        """Increment the tribunals scanned counter."""
        async with self._lock:
            self.tribunals_scanned += 1


NTFY_TOPIC = "causaganha-a7f3b2e9c1d4"


async def _publish_ntfy_status(
    summary: BackfillSummary,
    status: str,
    bstate: BackfillState,
) -> None:
    """Publish live pipeline status to ntfy.sh topic."""
    progress = bstate.get_all_progress()
    active_tribunals = sum(1 for p in progress.values() if not p.stopped)

    payload = json.dumps(
        {
            "last_updated": datetime.now(tz=UTC).isoformat(),
            "zips_uploaded": summary.hits,
            "zips_failed": summary.errors,
            "active_tribunals": active_tribunals,
            "status": status,
        }
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                content=payload.encode(),
                headers={"Content-Type": "application/json", "Title": "CausaGanha Pipeline"},
                timeout=10.0,
            )
            if resp.status_code >= 300:
                log.warning("ntfy_publish_failed", status_code=resp.status_code)
            else:
                log.debug("ntfy_publish_success", status=status, zips=summary.hits)
    except Exception as e:
        log.warning("ntfy_publish_error", error=str(e))


# ── Single-date processing ───────────────────────────────────────────

# HTTP status constants
HTTP_OK = 200
HTTP_BAD_REQUEST = 400


async def _process_djen_not_found(  # noqa: PLR0913
    client: httpx.AsyncClient,
    breaker: CircuitBreaker,
    d: date,
    tribunal: str,
    config: BackfillConfig,
    bstate: BackfillState,
    ia_state: State,
    summary: BackfillSummary,
    exc: DJENNotFoundError,
) -> str:
    """Handle DJENNotFoundError by marking as absent in state."""
    log.info(
        "backfill_empty",
        tribunal=tribunal,
        date=d.isoformat(),
        status_code=exc.status_code,
    )
    if not config.skip_absent_markers:
        await ia_state.mark(d, tribunal, ItemStatus.ABSENT)
    stopped = await bstate.record_empty(tribunal)
    await summary.inc_empty()
    if stopped:
        await summary.inc_stopped()
    return "empty"


async def _process_upload_to_ia(  # noqa: PLR0913
    client: httpx.AsyncClient,
    breaker: CircuitBreaker,
    d: date,
    tribunal: str,
    zip_path: Path,
    config: BackfillConfig,
    bstate: BackfillState,
    ia_state: State,
    summary: BackfillSummary,
) -> str:
    """Upload ZIP to IA and record result."""
    try:
        resp = await upload_zip(client, d, tribunal, zip_path, config.ia_auth)
        if resp.status_code < HTTP_BAD_REQUEST:
            await breaker.record_success()
            await ia_state.mark(d, tribunal, ItemStatus.UPLOADED)
            await bstate.record_hit(tribunal, d)
            await summary.inc_hit()
            return "hit"
        body = resp.content or b""
        if b"appears to be spam" in body:
            # IA rejected this specific item as spam — skip it, don't trip circuit
            log.warning(
                "backfill_item_spam_skipped",
                tribunal=tribunal,
                date=d.isoformat(),
                status=resp.status_code,
            )
            # Mark as a DJEN error (skip), not an IA infrastructure error
            await bstate.record_error(tribunal)
            await summary.inc_error()
            return "spam"
        log.error(
            "backfill_upload_failed",
            tribunal=tribunal,
            date=d.isoformat(),
            status=resp.status_code,
            body=body[:300].decode("utf-8", errors="replace"),
        )
        await breaker.record_failure()
    except (httpx.HTTPError, RuntimeError) as exc:
        # RuntimeError is raised by request_with_retry when all retries are
        # exhausted (e.g. IA returns 503 "spam" on every attempt).  Treat as a
        # transient upload failure so the run can continue with other dates.
        log.warning(
            "backfill_upload_error",
            tribunal=tribunal,
            date=d.isoformat(),
            error=str(exc),
        )
        await breaker.record_failure()

    await bstate.record_error(tribunal)
    await summary.inc_ia_error()  # IA error — not a source error
    return "error"


async def backfill_process_date(
    client: httpx.AsyncClient,
    breaker: CircuitBreaker,
    tribunal: str,
    d: date,
    config: BackfillConfig,
    bstate: BackfillState,
    ia_state: State,
    summary: BackfillSummary,
) -> str:
    """Process one (tribunal, date) for backfill.

    Returns ``"hit"``, ``"empty"``, ``"spam"``, or ``"error"``.
    """
    # Fast path: already on IA
    status = ia_state.get_status(d, tribunal)
    if status == "uploaded":
        await bstate.record_hit(tribunal, d)
        await summary.inc_hit()
        return "hit"
    if status == "absent":
        stopped = await bstate.record_empty(tribunal)
        await summary.inc_empty()
        if stopped:
            await summary.inc_stopped()
        return "empty"

    # Circuit breaker guard
    if not await breaker.allow_request():
        await bstate.record_error(tribunal)
        await summary.inc_error()
        return "error"

    if config.dry_run:
        log.info("backfill_dry_run", tribunal=tribunal, date=d.isoformat())
        await bstate.record_hit(tribunal, d)
        await summary.inc_hit()
        return "hit"

    # Fetch from DJEN
    zip_path: Path | None = None
    try:
        zip_url = await get_caderno_url(client, config.djen_proxy_url, tribunal, d)
        zip_path = await download_zip(client, zip_url)
    except DJENNotFoundError as exc:
        return await _process_djen_not_found(
            client, breaker, d, tribunal, config, bstate, ia_state, summary, exc
        )
    except httpx.HTTPError as exc:
        log.exception(
            "backfill_download_error",
            tribunal=tribunal,
            date=d.isoformat(),
            exc_info=exc,
        )
        await bstate.record_error(tribunal)
        await summary.inc_error()
        return "error"

    # Upload to IA
    return await _process_upload_to_ia(
        client, breaker, d, tribunal, zip_path, config, bstate, ia_state, summary
    )


# ── Per-tribunal scan loop ───────────────────────────────────────────


async def backfill_tribunal(
    client: httpx.AsyncClient,
    breaker: CircuitBreaker,
    tribunal: str,
    config: BackfillConfig,
    bstate: BackfillState,
    ia_state: State,
    deadline: float,
    summary: BackfillSummary,
) -> None:
    """Scan one tribunal backward until stopped, lower-bound, or deadline."""
    prog = await bstate.get_or_init(tribunal, config.start_date)

    if prog.stopped:
        log.info("backfill_skipped_stopped", tribunal=tribunal)
        await summary.inc_skipped_stopped()
        return

    await summary.inc_scanned()
    items_processed = 0

    # Determine per-tribunal dynamic lower bound (Genesis)
    genesis_str = config.genesis_dates.get(tribunal)
    genesis_date = (
        date.fromisoformat(genesis_str) if genesis_str and genesis_str != "None" else None
    )

    while True:
        # Check against global lower bound
        if config.lower_bound and prog.cursor_date < config.lower_bound:
            break

        # Check against discovered Genesis (discovery script)
        if genesis_date and prog.cursor_date < genesis_date:
            log.info(
                "backfill_hit_genesis",
                tribunal=tribunal,
                genesis=genesis_date.isoformat(),
                cursor=prog.cursor_date.isoformat(),
            )
            await bstate.stop_at_boundary(tribunal)
            break
        # Deadline guard
        if time.monotonic() > deadline - 30:
            log.info("backfill_deadline_reached", tribunal=tribunal)
            break

        # Max items guard
        if config.max_items and items_processed >= config.max_items:
            break

        current_date = prog.cursor_date

        if prog.stop_boundary and current_date <= prog.stop_boundary:
            log.info(
                "backfill_hit_boundary",
                tribunal=tribunal,
                boundary=prog.stop_boundary.isoformat(),
            )
            await bstate.stop_at_boundary(tribunal)
            break

        log.debug(
            "backfill_date",
            tribunal=tribunal,
            date=current_date.isoformat(),
            empty_streak=prog.empty_streak,
        )

        zip_path: Path | None = None
        result = "error"  # default if exception before process_date returns
        try:
            result = await backfill_process_date(
                client,
                breaker,
                tribunal,
                current_date,
                config,
                bstate,
                ia_state,
                summary,
            )
        finally:
            if zip_path is not None:
                await asyncio.to_thread(zip_path.unlink, missing_ok=True)

        # Advance on definitive results, including spam rejections that should be skipped.
        # Only genuine upload errors keep the cursor so the next run retries this date.
        if result in {"hit", "empty", "spam"}:
            await bstate.advance_cursor(tribunal)
        else:
            log.info(
                "backfill_cursor_held",
                tribunal=tribunal,
                date=current_date.isoformat(),
                reason="upload_error_will_retry",
            )
            break  # Stop this tribunal's scan; next run retries from same date
        items_processed += 1

        # Checkpoint after each date
        save_backfill_state(bstate, config.backfill_state_file)

        # Check if just stopped
        if prog.stopped:
            log.info(
                "backfill_tribunal_stopped",
                tribunal=tribunal,
                empty_streak=prog.empty_streak,
                cursor=prog.cursor_date.isoformat(),
            )
            break


# ── Main orchestration ───────────────────────────────────────────────


async def _advance_stopped_cursors(
    bstate: BackfillState,
    all_tribunals: list[str],
    start_date: date,
) -> None:
    """Advance stopped tribunal cursors to start_date if needed."""
    for t in all_tribunals:
        prog = bstate.get_all_progress().get(t)
        if prog is not None and prog.stopped:
            advanced = await bstate.ensure_cursor_at_least(t, start_date)
            if advanced:
                log.info(
                    "cursor_auto_advanced",
                    tribunal=t,
                    new_cursor=start_date.isoformat(),
                )


async def _run_backfill_workers(
    client: httpx.AsyncClient,
    breaker: CircuitBreaker,
    config: BackfillConfig,
    bstate: BackfillState,
    ia_state: State,
    deadline: float,
    summary: BackfillSummary,
    all_tribunals: list[str],
) -> None:
    """Run workers to process tribunals."""
    queue: asyncio.Queue[str] = asyncio.Queue()
    for t in all_tribunals:
        queue.put_nowait(t)

    async def _worker() -> None:
        while not queue.empty():
            if time.monotonic() > deadline - 30:
                break
            try:
                tribunal = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            await backfill_tribunal(
                client,
                breaker,
                tribunal,
                config,
                bstate,
                ia_state,
                deadline,
                summary,
            )
            queue.task_done()

    async def _status_publisher() -> None:
        if not config.publish_live_status:
            return

        interval_str = os.getenv("LIVE_STATUS_INTERVAL_SECONDS", "60")
        try:
            interval = float(interval_str)
        except ValueError:
            interval = 60.0

        while True:
            await asyncio.sleep(interval)
            await _publish_ntfy_status(
                summary,
                "running",
                bstate,
            )

    workers = [asyncio.create_task(_worker()) for _ in range(config.workers)]
    publisher_task = asyncio.create_task(_status_publisher())

    await asyncio.gather(*workers)

    # Cancel the publisher once workers finish
    publisher_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await publisher_task


async def run_backfill(config: BackfillConfig) -> int:
    """Execute the backfill pipeline.  Returns the process exit code."""
    deadline = time.monotonic() + config.deadline_minutes * 60
    bstate = load_backfill_state(config.backfill_state_file)
    ia_state = load_state(config.state_file)

    # 0. Load discovered Genesis dates
    genesis_dates = {}
    genesis_path = Path("dashboard/public/tribunal_start_dates.json")
    if await anyio.Path(genesis_path).exists():
        try:
            genesis_dates = json.loads(await anyio.Path(genesis_path).read_text(encoding="utf-8"))
            log.info("backfill_genesis_loaded", tribunals=len(genesis_dates))
        except (json.JSONDecodeError, OSError):
            log.warning("backfill_genesis_load_failed", path=str(genesis_path))
    config.genesis_dates = genesis_dates

    timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        # 1. Tribunal list
        all_tribunals = await get_tribunal_list(client, config.djen_proxy_url)
        if config.tribunal:
            validate_tribunal(config.tribunal)
            all_tribunals = [config.tribunal]

        # 2. Advance stopped tribunal cursors
        await _advance_stopped_cursors(bstate, all_tribunals, config.start_date)

        # 3. Process tribunals
        summary = BackfillSummary()
        # Increased threshold from 3 to 10 - was too aggressive, causing many skips
        breaker = CircuitBreaker(threshold=10, recovery_timeout=60.0)

        if config.publish_live_status:
            # Fire and forget initial status
            _bg_task = asyncio.create_task(_publish_ntfy_status(summary, "running", bstate))

        await _run_backfill_workers(
            client, breaker, config, bstate, ia_state, deadline, summary, all_tribunals
        )

    # 4. Save state
    save_backfill_state(bstate, config.backfill_state_file)
    save_state(ia_state, config.state_file)

    # 5. Summary
    log.info(
        "backfill_complete",
        tribunals_scanned=summary.tribunals_scanned,
        tribunals_stopped=summary.tribunals_stopped,
        tribunals_skipped_stopped=summary.tribunals_skipped_stopped,
        hits=summary.hits,
        empties=summary.empties,
        errors=summary.errors,
        ia_errors=summary.ia_errors,
    )

    # Pass metrics to CI environment if running in GitHub Actions
    if gh_output := os.getenv("GITHUB_OUTPUT"):
        async with await anyio.open_file(gh_output, "a") as f:
            await f.write(f"uploaded={summary.hits}\n")
            await f.write(f"errors={summary.errors}\n")
            await f.write(f"empties={summary.empties}\n")
            await f.write(f"stopped={summary.tribunals_stopped}\n")

    if gh_summary := os.getenv("GITHUB_STEP_SUMMARY"):
        start_date_str = config.lower_bound.isoformat() if config.lower_bound else "2013-01-01"
        end_date_str = config.start_date.isoformat()
        async with await anyio.open_file(gh_summary, "a") as f:
            await f.write("## Results (success = uploaded > 0)\n")
            await f.write("| Metric | Value |\n")
            await f.write("|--------|-------|\n")
            await f.write(f"| ✅ Uploaded (hits) | **{summary.hits}** |\n")
            await f.write(f"| ❌ Errors | {summary.errors} |\n")
            await f.write(f"| ⬜ Empties | {summary.empties} |\n")
            await f.write(f"| ⏹ Stopped | {summary.tribunals_stopped} |\n")
            await f.write(f"| Window | {start_date_str} → {end_date_str} |\n\n")

    exit_code = 0
    if summary.ia_errors > 0:
        log.error(
            "backfill_failed",
            ia_errors=summary.ia_errors,
            djen_errors=summary.errors,
            message="IA upload errors detected — pipeline must not silently succeed",
        )
        exit_code = 1

    if config.publish_live_status:
        # Publish final status blockingly
        final_status = "failed" if exit_code != 0 else "completed"
        await _publish_ntfy_status(summary, final_status, bstate)

    return exit_code
