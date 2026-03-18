"""Persistent state cache backed by a JSON file.

Used as a GHA artifact to avoid redundant Internet Archive metadata queries
across runs.  The IA metadata API remains the authoritative source — this
cache is purely an optimisation.
"""

from __future__ import annotations

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


class ItemStatus(StrEnum):
    UPLOADED = "uploaded"
    ABSENT = "absent"


class State:
    """In-memory state cache with JSON serialisation.

    All mutation methods are protected by an asyncio.Lock so concurrent
    coroutines cannot interleave reads and writes.
    """

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, str]] = {}
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
        return tribunal in self._entries.get(d.isoformat(), {})

    def get_status(self, d: date, tribunal: str) -> str | None:
        """Return the status string (``"uploaded"``/``"absent"``) or ``None``."""
        return self._entries.get(d.isoformat(), {}).get(tribunal)

    @property
    def date_count(self) -> int:
        """Number of dates tracked in the cache."""
        return len(self._entries)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    async def mark(self, d: date, tribunal: str, status: ItemStatus) -> None:
        async with self._lock:
            key = d.isoformat()
            if key not in self._entries:
                self._entries[key] = {}
            self._entries[key][tribunal] = status.value

    # ------------------------------------------------------------------
    # TTL pruning
    # ------------------------------------------------------------------

    def prune(self, *, ttl_days: int = _TTL_DAYS) -> int:
        """Remove entries older than *ttl_days*.  Returns the number pruned."""
        cutoff = (date.today() - timedelta(days=ttl_days)).isoformat()
        old_keys = [k for k in self._entries if k < cutoff]
        for k in old_keys:
            del self._entries[k]
        return len(old_keys)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, object]:
        return {
            "version": 1,
            "updated_at": datetime.now(tz=UTC).isoformat(),
            "entries": self._entries,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> State:
        state = cls()
        entries = data.get("entries")
        if isinstance(entries, dict):
            for date_key, tribunals in entries.items():
                if isinstance(date_key, str) and isinstance(tribunals, dict):
                    state._entries[date_key] = {
                        k: v
                        for k, v in tribunals.items()
                        if isinstance(k, str) and isinstance(v, str)
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
        return state
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("state_cache_corrupt", path=str(path), error=str(exc))
        return State()


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
