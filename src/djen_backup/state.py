from __future__ import annotations


VERSION_EXPECTED = 2

"""Persistent state cache backed by a JSON file.

Used as a GHA artifact to avoid redundant Internet Archive metadata queries
across runs.  The IA metadata API remains the authoritative source — this
cache is purely an optimisation.
"""


import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

import structlog


if TYPE_CHECKING:
    from pathlib import Path

log = structlog.get_logger()

# Entries older than this are pruned on save to prevent unbounded growth.
_TTL_DAYS = 90


def _get_today() -> date:
    """Get today's date using UTC."""
    return datetime.now(tz=UTC).date()


class ItemStatus(StrEnum):
    """Status values for cache entries."""

    UPLOADED = "uploaded"
    ABSENT = "absent"


class State:
    """In-memory state cache with JSON serialisation.

    All mutation methods are protected by an asyncio.Lock so concurrent
    coroutines cannot interleave reads and writes.
    """

    def __init__(self) -> None:
        """Initialize the state cache with empty entries and a lock."""
        self._entries: dict[str, dict[str, str | dict[str, object]]] = {}
        # _entries layout: {"2024-01-15": {"TJSP": "uploaded", "TJRO": "absent"}}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def get_done_tribunals(self, d: date) -> set[str]:
        """Return tribunal codes known to be uploaded or absent for *d*."""
        async with self._lock:
            return set(self._entries.get(d.isoformat(), {}).keys())

    def is_done(self, d: date, tribunal: str) -> bool:
        """Check if a tribunal is marked as done for a date."""
        return tribunal in self._entries.get(d.isoformat(), {})

    def get_status(self, d: date, tribunal: str) -> str | None:
        """Return the status string (``"uploaded"``/``"absent"``) or ``None``."""
        val = self._entries.get(d.isoformat(), {}).get(tribunal)
        if isinstance(val, dict):
            return val.get("status")
        return val

    @property
    def date_count(self) -> int:
        """Number of dates tracked in the cache."""
        return len(self._entries)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def _mark_sync(self, d: date, tribunal: str, status: str) -> None:
        """Synchronous mark for bulk loading (no lock, use only at startup)."""
        key = d.isoformat()
        if key not in self._entries:
            self._entries[key] = {}
        self._entries[key][tribunal] = status

    async def mark(
        self, d: date, tribunal: str, status: ItemStatus, duration_s: float | None = None
    ) -> None:
        """Mark a tribunal as done for a date with the given status."""
        async with self._lock:
            key = d.isoformat()
            if key not in self._entries:
                self._entries[key] = {}
            if duration_s is not None:
                self._entries[key][tribunal] = {"status": status.value, "duration_s": duration_s}
            else:
                self._entries[key][tribunal] = status.value

    # ------------------------------------------------------------------
    # TTL pruning
    # ------------------------------------------------------------------

    def prune(self, *, ttl_days: int = _TTL_DAYS) -> int:
        """Remove entries older than *ttl_days*.  Returns the number pruned."""
        cutoff = (_get_today() - timedelta(days=ttl_days)).isoformat()
        old_keys = [k for k in self._entries if k < cutoff]
        for k in old_keys:
            del self._entries[k]
        return len(old_keys)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        """Convert State to dictionary for serialization."""
        return {
            "version": 2,
            "updated_at": datetime.now(tz=UTC).isoformat(),
            "entries": self._entries,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> State:
        """Create State from dictionary."""
        state = cls()
        if data.get("version") != VERSION_EXPECTED:
            return state

        entries = data.get("entries")
        if isinstance(entries, dict):
            for date_key, tribunals in entries.items():
                if isinstance(date_key, str) and isinstance(tribunals, dict):
                    state._entries[date_key] = {
                        k: v
                        for k, v in tribunals.items()
                        if isinstance(k, str) and isinstance(v, (str, dict))
                    }
        return state


def load_state(path: Path | None) -> State:
    """Load state from *path*, returning an empty state on any error."""
    if path is None or not path.is_file():
        log.info("state_cache_miss", path=str(path))
        return State()
    try:
        raw: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
        state = State.from_dict(raw)
        log.info(
            "state_cache_loaded",
            path=str(path),
            dates=state.date_count,
        )
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("state_cache_corrupt", path=str(path), error=str(exc))
        state = State()
    return state


def save_state(state: State, path: Path | None) -> None:
    """Persist *state* to *path*.  No-op when *path* is ``None``."""
    if path is None:
        return
    pruned = state.prune()
    if pruned:
        log.info("state_cache_pruned", removed=pruned)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
    log.info("state_cache_saved", path=str(path))


# ---------------------------------------------------------------------------
# IA-backed state persistence
# ---------------------------------------------------------------------------

IA_STATE_ITEM = "causaganha-dashboard"
IA_STATE_FILENAME = "ia-state.json"
IA_BACKFILL_STATE_FILENAME = "backfill-state.json"
_IA_DOWNLOAD_URL = f"https://archive.org/download/{IA_STATE_ITEM}/{{}}"
_IA_S3_URL = f"https://s3.us.archive.org/{IA_STATE_ITEM}/{{}}"


IA_ZIP_INVENTORY_FILENAME = "zip-inventory.txt"


async def download_text_from_ia(filename: str) -> str | None:
    """Download a text file from IA. Returns content string or None."""
    import httpx

    url = _IA_DOWNLOAD_URL.format(filename)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                log.info("text_downloaded_from_ia", filename=filename, size=len(resp.text))
                return resp.text
            log.info("text_not_found_on_ia", filename=filename, status=resp.status_code)
    except Exception as exc:
        log.warning("text_download_failed", filename=filename, error=str(exc))
    return None


async def upload_text_to_ia(filename: str, content: str, auth: str) -> bool:
    """Upload a text file to IA. Returns True on success."""
    import httpx

    url = _IA_S3_URL.format(filename)
    headers = {
        "Authorization": auth,
        "Content-Type": "text/plain",
        "x-amz-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.put(url, content=content.encode("utf-8"), headers=headers)
            if resp.status_code < 400:
                log.info("text_uploaded_to_ia", filename=filename)
                return True
            log.warning("text_upload_failed", filename=filename, status=resp.status_code)
    except Exception as exc:
        log.warning("text_upload_error", filename=filename, error=str(exc))
    return False


async def download_state_from_ia(filename: str) -> dict | None:
    """Download a state JSON from IA. Returns parsed dict or None."""
    import httpx

    url = _IA_DOWNLOAD_URL.format(filename)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                log.info("state_downloaded_from_ia", filename=filename)
                return data
            log.info("state_not_found_on_ia", filename=filename, status=resp.status_code)
    except Exception as exc:
        log.warning("state_download_failed", filename=filename, error=str(exc))
    return None


async def upload_state_to_ia(filename: str, data: dict, auth: str) -> bool:
    """Upload a state JSON to IA. Returns True on success."""
    import httpx

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
            log.warning("state_upload_failed", filename=filename, status=resp.status_code)
    except Exception as exc:
        log.warning("state_upload_error", filename=filename, error=str(exc))
    return False


def merge_state(local: State, remote: State) -> State:
    """Merge two State objects. Keeps all entries from both; local wins on conflict."""
    merged = State()
    # Start with remote entries
    for date_key, tribunals in remote._entries.items():
        merged._entries[date_key] = dict(tribunals)
    # Overlay local entries (local wins)
    for date_key, tribunals in local._entries.items():
        if date_key not in merged._entries:
            merged._entries[date_key] = {}
        merged._entries[date_key].update(tribunals)
    return merged
