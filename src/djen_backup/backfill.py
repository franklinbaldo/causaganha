from __future__ import annotations

import anyio


HTTP_300_MULTIPLE_CHOICES = 300
VERSION_EXPECTED = 2

"""Backfill engine — scan historical dates per tribunal with 60-empty-day stop rule.

For each tribunal, scans backward one day at a time.  When 60 consecutive
*authoritative* empties are observed the tribunal is marked stopped and
skipped on future runs.  Errors and timeouts never count as empty.
"""


import asyncio
import contextlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import structlog

from djen_backup.archive import (
    CircuitBreaker,
    upload_zip,
)
from djen_backup.djen import DJENNotFoundError, download_zip, get_caderno_url
from djen_backup.runner import validate_tribunal
from djen_backup.state import (
    IA_BACKFILL_STATE_FILENAME,
    IA_STATE_FILENAME,
    IA_ZIP_INVENTORY_FILENAME,
    ItemStatus,
    State,
    download_state_from_ia,
    download_text_from_ia,
    load_state,
    merge_state,
    save_state,
    upload_state_to_ia,
    upload_text_to_ia,
)
from djen_backup.tribunais import get_tribunal_list


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

    async def set_cursor(self, tribunal: str, target_cursor: date) -> bool:
        """Set the cursor to a specific date and reset streak."""
        async with self._lock:
            if tribunal in self._tribunals:
                prog = self._tribunals[tribunal]
                prog.cursor_date = target_cursor
                prog.stopped = False
                prog.empty_streak = 0
                prog.stop_boundary = None
                return True
            return False

    async def reset_tribunal(self, tribunal: str) -> bool:
        """Reset a stopped tribunal.  Returns ``True`` if it was found."""
        async with self._lock:
            if tribunal in self._tribunals:
                prog = self._tribunals[tribunal]
                prog.stopped = False
                prog.empty_streak = 0
                prog.stop_boundary = None
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
        if data.get("version") != VERSION_EXPECTED:
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


def merge_backfill_state(local: BackfillState, remote: BackfillState) -> BackfillState:
    """Merge two BackfillStates. Keeps the more advanced cursor (older date) per tribunal."""
    merged = BackfillState()
    all_tribunals = set(local._tribunals) | set(remote._tribunals)
    for t in all_tribunals:
        local_prog = local._tribunals.get(t)
        remote_prog = remote._tribunals.get(t)
        if local_prog and remote_prog:
            # Keep the one with the older cursor (more progress)
            if local_prog.cursor_date <= remote_prog.cursor_date:
                merged._tribunals[t] = local_prog
            else:
                merged._tribunals[t] = remote_prog
        else:
            merged._tribunals[t] = local_prog or remote_prog
    return merged


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
    skip_if_mostly_complete: bool = False
    genesis_dates: dict[str, date] = field(default_factory=dict)


@dataclass
class BackfillSummary:
    """Summary of backfill execution statistics."""

    hits: int = 0
    cache_hits: int = 0
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

    async def inc_cache_hit(self) -> None:
        """Increment the cache hit counter."""
        async with self._lock:
            self.cache_hits += 1

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
            if resp.status_code >= HTTP_300_MULTIPLE_CHOICES:
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
    # Fast path 1: check local state cache
    status = ia_state.get_status(d, tribunal)
    if status == "uploaded":
        await bstate.record_hit(tribunal, d)
        await summary.inc_cache_hit()
        return "hit"
    if status == "absent":
        stopped = await bstate.record_empty(tribunal)
        await summary.inc_empty()
        if stopped:
            await summary.inc_stopped()
        return "empty"

    if config.dry_run:
        log.info("backfill_dry_run", tribunal=tribunal, date=d.isoformat())
        await bstate.record_hit(tribunal, d)
        await summary.inc_hit()
        return "hit"

    # No HEAD check — inventory already knows what's on IA.
    # If we're here, the date is NOT in inventory → go straight to DJEN.

    # Circuit breaker guard
    if not await breaker.allow_request():
        await bstate.record_error(tribunal)
        await summary.inc_error()
        return "error"

    # Fetch from DJEN
    zip_path: Path | None = None
    try:
        zip_url = await get_caderno_url(client, config.djen_proxy_url, tribunal, d)
        zip_path = await download_zip(client, zip_url)
    except DJENNotFoundError as exc:
        if exc.reason not in ("Not Found", "No publications"):
            log.warning(
                "backfill_download_error_djen",
                tribunal=tribunal,
                date=d.isoformat(),
                reason=exc.reason,
            )
            await bstate.record_error(tribunal)
            await summary.inc_error()
            return "error"
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
    retry_count = 0

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
            retry_count = 0
            await bstate.advance_cursor(tribunal)
        else:
            if retry_count == 0:
                log.info(
                    "backfill_error_retry",
                    tribunal=tribunal,
                    date=current_date.isoformat(),
                    delay=30,
                )
                await asyncio.sleep(30)
                retry_count += 1
                continue

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


def _days_in_year(year: int, upper: date, lower: date) -> list[date]:
    """Return all days in a year within [lower, upper] bounds."""
    start = max(date(year, 1, 1), lower)
    end = min(date(year, 12, 31), upper)
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


ZIP_INVENTORY_FILE = Path("data/zip-inventory.txt")


async def _fetch_ia_item_zips(
    client: httpx.AsyncClient,
    tribunal: str,
    year: int,
    sem: asyncio.Semaphore,
) -> set[date]:
    """Fetch all ZIP dates for a tribunal×year from IA metadata (1 request per item)."""
    item_id = get_ia_item_id(tribunal, date(year, 1, 1))
    metadata_url = f"https://archive.org/metadata/{item_id}/files"
    async with sem:
        try:
            resp = await client.get(metadata_url, timeout=15)
            if resp.status_code >= 400:
                return set()
            files = resp.json().get("result", [])
            dates: set[date] = set()
            for f in files:
                name = f.get("name", "")
                if not name.startswith("djen-") or not name.endswith(".zip"):
                    continue
                parts = name[len("djen-"):].split("-")
                if len(parts) < 4:
                    continue
                try:
                    dates.add(date.fromisoformat(f"{parts[0]}-{parts[1]}-{parts[2]}"))
                except ValueError:
                    continue
            return dates
        except (httpx.HTTPError, httpx.TimeoutException, Exception):
            return set()


class ZipInventory:
    """CSV-based inventory of all known ZIPs on Internet Archive.

    Format (one line per entry, sorted by timestamp):
        TIMESTAMP,TRIBUNAL,DATE,STATUS,URL

    STATUS is ``uploaded`` or ``absent``.
    URL is the IA download URL for uploaded ZIPs, empty for absents.

    Lookup is O(1) via a ``{TRIBUNAL/DATE}`` keyed dict.
    """

    HEADER = "timestamp,tribunal,date,status,url"

    def __init__(self) -> None:
        # Key: "TRIBUNAL/YYYY-MM-DD" → (status, url, timestamp)
        self._entries: dict[str, tuple[str, str, str]] = {}

    @staticmethod
    def _key(tribunal: str, d: date) -> str:
        return f"{tribunal.upper()}/{d.isoformat()}"

    @staticmethod
    def _url(tribunal: str, d: date) -> str:
        item_id = f"djen-{tribunal.lower()}-{d.year}"
        filename = f"djen-{d.isoformat()}-{tribunal.upper()}.zip"
        return f"https://archive.org/download/{item_id}/{filename}"

    def has(self, tribunal: str, d: date) -> bool:
        """Check if date is known (either uploaded or absent)."""
        return self._key(tribunal, d) in self._entries

    def add(self, tribunal: str, d: date) -> None:
        """Mark a date as uploaded (ZIP exists on IA)."""
        k = self._key(tribunal, d)
        if k not in self._entries:
            self._entries[k] = (
                "uploaded",
                self._url(tribunal, d),
                datetime.now(UTC).isoformat(timespec="seconds"),
            )

    def add_absent(self, tribunal: str, d: date) -> None:
        """Mark a date as confirmed absent (no journal published)."""
        k = self._key(tribunal, d)
        if k not in self._entries:
            self._entries[k] = (
                "absent",
                "",
                datetime.now(UTC).isoformat(timespec="seconds"),
            )

    def add_many(self, tribunal: str, dates: set[date]) -> None:
        for d in dates:
            self.add(tribunal, d)

    def __len__(self) -> int:
        """Return number of inventory entries."""
        return len(self._entries)

    def load_from_csv(self, text: str) -> int:
        """Load from CSV text. Returns count added."""
        before = len(self._entries)
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("timestamp"):
                continue
            parts = line.split(",", 4)
            if len(parts) < 4:
                continue
            ts, tribunal, date_str, status = parts[0], parts[1], parts[2], parts[3]
            url = parts[4] if len(parts) > 4 else ""
            k = f"{tribunal.upper()}/{date_str}"
            if k not in self._entries:
                self._entries[k] = (status, url, ts)
        return len(self._entries) - before

    def to_csv(self) -> str:
        """Serialize to CSV sorted by timestamp."""
        lines = [self.HEADER]
        rows = []
        for k, (status, url, ts) in self._entries.items():
            tribunal, date_str = k.split("/", 1)
            rows.append((ts, tribunal, date_str, status, url))
        rows.sort()  # Sorts by timestamp first
        for ts, tribunal, date_str, status, url in rows:
            lines.append(f"{ts},{tribunal},{date_str},{status},{url}")
        return "\n".join(lines) + "\n"

    async def load_from_ia(self) -> int:
        """Download inventory from Internet Archive. Returns count loaded."""
        text = await download_text_from_ia(IA_ZIP_INVENTORY_FILENAME)
        if text:
            return self.load_from_csv(text)
        return 0

    async def upload_to_ia(self, auth: str) -> bool:
        """Upload inventory to Internet Archive."""
        return await upload_text_to_ia(IA_ZIP_INVENTORY_FILENAME, self.to_csv(), auth)

    def load_from_disk(self, path: Path = ZIP_INVENTORY_FILE) -> int:
        """Load from local disk as fallback. Returns count loaded."""
        if not path.exists():
            return 0
        return self.load_from_csv(path.read_text(encoding="utf-8"))

    def save_to_disk(self, path: Path = ZIP_INVENTORY_FILE) -> None:
        """Persist to local disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_csv(), encoding="utf-8")

    def load_from_snapshot(self) -> int:
        """Seed from ia-snapshot.json (zero network)."""
        snapshot_path = Path("dashboard/public/ia-snapshot.json")
        if not snapshot_path.exists():
            return 0
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return 0
        before = len(self._entries)
        for item_data in snapshot.get("items", {}).values():
            tribunal = item_data.get("tribunal", "")
            for date_str in item_data.get("dates", []):
                try:
                    d = date.fromisoformat(date_str)
                except ValueError:
                    continue
                self.add(tribunal, d)
        return len(self._entries) - before

    def gaps_for_year(
        self,
        tribunal: str,
        year: int,
        upper: date,
        lower: date,
    ) -> list[date]:
        """Return days in the year that are NOT in inventory."""
        start = max(date(year, 1, 1), lower)
        end = min(date(year, 12, 31), upper)
        missing = []
        current = start
        t_upper = tribunal.upper()
        while current <= end:
            if f"{t_upper}/{current.isoformat()}" not in self._entries:
                missing.append(current)
            current += timedelta(days=1)
        return missing


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
    """Naive inventory-based backfill. Zero upfront scanning.

    1. Load zip-inventory.txt + ia-snapshot.json from disk (instant)
    2. Compute gaps: days NOT in inventory = work to do
    3. Process gaps year by year (newest first)
    4. Each processed item updates inventory (hit from IA or new upload)
    5. Inventory grows over runs — subsequent starts are instant
    """
    active_tribunals = []
    for t in all_tribunals:
        prog = await bstate.get_or_init(t, config.start_date)
        if prog.stopped:
            log.info("backfill_skipped_stopped", tribunal=t)
            await summary.inc_skipped_stopped()
        else:
            active_tribunals.append(t)

    lower = config.lower_bound or date(2013, 1, 1)
    today = datetime.now(UTC).date()
    upper = min(config.start_date, today)
    years = sorted(range(lower.year, upper.year + 1), reverse=True)

    # Load inventory: IA first (source of truth), then disk fallback, then snapshot seed
    inventory = ZipInventory()
    loaded_ia = await inventory.load_from_ia()
    loaded_disk = inventory.load_from_disk()
    loaded_snapshot = inventory.load_from_snapshot()
    log.info(
        "zip_inventory_loaded",
        from_ia=loaded_ia,
        from_disk=loaded_disk,
        from_snapshot=loaded_snapshot,
        total=len(inventory),
    )

    scanned_tribunals: set[str] = set()

    for year in years:
        if time.monotonic() > deadline - 60:
            break
        if config.max_items > 0 and summary.hits >= config.max_items:
            break

        # Step A: Enrich inventory from IA metadata (1 request per tribunal×year)
        # This discovers ZIPs on IA that aren't in the inventory yet.
        ia_fetch_tasks = {
            t: asyncio.create_task(_fetch_ia_item_zips(client, t, year, sem))
            for t in active_tribunals
        }
        ia_added = 0
        for t, task in ia_fetch_tasks.items():
            ia_dates = await task
            for d in ia_dates:
                if not inventory.has(t, d):
                    inventory.add(t, d)
                    ia_added += 1
        if ia_added:
            log.info("inventory_enriched_from_ia", year=year, new_entries=ia_added)

        # Step B: Compute gaps from enriched inventory (instant)
        all_gaps: list[tuple[date, str]] = []
        for t in active_tribunals:
            genesis_str = config.genesis_dates.get(t)
            t_lower = lower
            if genesis_str and genesis_str != "None":
                with contextlib.suppress(ValueError):
                    t_lower = max(lower, date.fromisoformat(genesis_str))

            missing = inventory.gaps_for_year(t, year, upper, t_lower)
            for d in missing:
                all_gaps.append((d, t))

        if not all_gaps:
            log.info("backfill_year_complete", year=year)
            continue

        all_gaps.sort(key=lambda x: x[0], reverse=True)
        queue: asyncio.Queue[tuple[date, str]] = asyncio.Queue()
        for gap in all_gaps:
            queue.put_nowait(gap)

        log.info("backfill_year_working", year=year, gaps=len(all_gaps))

        async def _worker(queue: asyncio.Queue = queue) -> None:
            while not queue.empty():
                if time.monotonic() > deadline - 30:
                    break
                if config.max_items > 0 and summary.hits >= config.max_items:
                    break
                try:
                    d, tribunal = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                if tribunal not in scanned_tribunals:
                    scanned_tribunals.add(tribunal)
                    await summary.inc_scanned()

                result = await backfill_process_date(
                    client, breaker, tribunal, d, config, bstate, ia_state, summary,
                )

                if result == "hit":
                    inventory.add(tribunal, d)
                elif result in {"empty", "spam"}:
                    inventory.add_absent(tribunal, d)
                elif result == "error":
                    log.warning("backfill_item_error", tribunal=tribunal, date=d.isoformat())

                queue.task_done()

        worker_tasks = [asyncio.create_task(_worker()) for _ in range(config.workers)]

        async def _state_syncer() -> None:
            while True:
                await asyncio.sleep(120)
                if not config.dry_run:
                    save_backfill_state(bstate, config.backfill_state_file)
                    save_state(ia_state, config.state_file)
                    inventory.save_to_disk()
                    await upload_state_to_ia(
                        IA_BACKFILL_STATE_FILENAME, bstate.to_dict(), config.ia_auth
                    )
                    await upload_state_to_ia(IA_STATE_FILENAME, ia_state.to_dict(), config.ia_auth)
                    await inventory.upload_to_ia(config.ia_auth)
                    log.info("state_checkpoint_saved", inventory_size=len(inventory))

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
                await _publish_ntfy_status(summary, "running", bstate)

        syncer_task = asyncio.create_task(_state_syncer())
        publisher_task = asyncio.create_task(_status_publisher())
        await asyncio.gather(*worker_tasks)
        syncer_task.cancel()
        publisher_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await syncer_task
        with contextlib.suppress(asyncio.CancelledError):
            await publisher_task

        inventory.save_to_disk()
        save_backfill_state(bstate, config.backfill_state_file)
        log.info(
            "backfill_year_done", year=year, uploads=summary.hits, discovered=summary.cache_hits
        )

    # Final save: disk + IA
    inventory.save_to_disk()
    if not config.dry_run:
        await inventory.upload_to_ia(config.ia_auth)
    log.info("zip_inventory_saved", total=len(inventory))

    if not scanned_tribunals:
        for t in active_tribunals:
            await summary.inc_scanned()


async def run_backfill(config: BackfillConfig) -> int:
    """Execute the backfill pipeline.  Returns the process exit code."""
    deadline = time.monotonic() + config.deadline_minutes * 60

    # 0. Load local state, then try to fetch remote state from IA and merge
    local_bstate = load_backfill_state(config.backfill_state_file)
    local_ia_state = load_state(config.state_file)

    remote_bstate_data = await download_state_from_ia(IA_BACKFILL_STATE_FILENAME)
    remote_ia_state_data = await download_state_from_ia(IA_STATE_FILENAME)

    if remote_bstate_data:
        remote_bstate = BackfillState.from_dict(remote_bstate_data)
        bstate = merge_backfill_state(local_bstate, remote_bstate)
        log.info(
            "backfill_state_merged",
            local=local_bstate.tribunal_count(),
            remote=remote_bstate.tribunal_count(),
            merged=bstate.tribunal_count(),
        )
    else:
        bstate = local_bstate

    if remote_ia_state_data:
        remote_ia_state = State.from_dict(remote_ia_state_data)
        ia_state = merge_state(local_ia_state, remote_ia_state)
        log.info(
            "ia_state_merged",
            local=local_ia_state.date_count,
            remote=remote_ia_state.date_count,
            merged=ia_state.date_count,
        )
    else:
        ia_state = local_ia_state

    # Idempotency check for single-day runs
    if config.skip_if_mostly_complete and config.start_date == config.lower_bound:
        done_tribs = await ia_state.get_done_tribunals(config.start_date)
        if len(done_tribs) > 80:
            log.info(
                "idempotency_skip",
                message=f"Skip: today already collected ({len(done_tribs)}/91)",
                date=config.start_date.isoformat(),
            )
            print(f"Skip: today already collected ({len(done_tribs)}/91)")
            return 0

    # 0b. Load discovered Genesis dates
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

        # 1b. Unstick tribunals that were incorrectly stopped
        #     (e.g., proxy errors counted as empties in older code).
        all_progress = bstate.get_all_progress()
        for t in all_tribunals:
            prog = all_progress.get(t)
            if prog and prog.stopped and prog.last_result == "error":
                log.info("backfill_unsticking_tribunal", tribunal=t, last_result=prog.last_result)
                await bstate.reset_tribunal(t)

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

    # 4. Save state locally and upload to IA
    save_backfill_state(bstate, config.backfill_state_file)
    save_state(ia_state, config.state_file)

    if not config.dry_run:
        await upload_state_to_ia(IA_BACKFILL_STATE_FILENAME, bstate.to_dict(), config.ia_auth)
        await upload_state_to_ia(IA_STATE_FILENAME, ia_state.to_dict(), config.ia_auth)

    # 5. Summary
    log.info(
        "backfill_complete",
        tribunals_scanned=summary.tribunals_scanned,
        tribunals_stopped=summary.tribunals_stopped,
        tribunals_skipped_stopped=summary.tribunals_skipped_stopped,
        hits=summary.hits,
        cache_hits=summary.cache_hits,
        empties=summary.empties,
        errors=summary.errors,
        ia_errors=summary.ia_errors,
    )

    # Pass metrics to CI environment if running in GitHub Actions
    if gh_output := os.getenv("GITHUB_OUTPUT"):
        async with await anyio.open_file(gh_output, "a") as f:
            await f.write(f"uploaded={summary.hits}\n")
            await f.write(f"cache_hits={summary.cache_hits}\n")
            await f.write(f"errors={summary.errors}\n")
            await f.write(f"empties={summary.empties}\n")
            await f.write(f"stopped={summary.tribunals_stopped}\n")
    else:
        # Fallback to local file for testing/local runs if needed, or stdout.
        # But this script usually runs in GH Actions. We will also export to a local file
        # so the bash script can reliably read it.
        pass

    # We also write a special marker so we can grep it reliably in GH Actions.
    # The GITHUB_OUTPUT should work now that we also explicitly check the format.

    if gh_summary := os.getenv("GITHUB_STEP_SUMMARY"):
        start_date_str = config.lower_bound.isoformat() if config.lower_bound else "2013-01-01"
        end_date_str = config.start_date.isoformat()
        async with await anyio.open_file(gh_summary, "a") as f:
            await f.write("## Results (success = uploaded > 0)\n")
            await f.write("| Metric | Value |\n")
            await f.write("|--------|-------|\n")
            await f.write(f"| ✅ Uploaded (new) | **{summary.hits}** |\n")
            await f.write(f"| ♻️ Cache hits | {summary.cache_hits} |\n")
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
