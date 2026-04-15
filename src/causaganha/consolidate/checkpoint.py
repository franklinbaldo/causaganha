"""Per-date checkpoint to resume after crash.

State file: ``data/consolidate-checkpoint.json``

Schema::

    {
      "current_date": "2026-04-01" | null,
      "processed_zips": ["djen-2026-04-01-TJSP.zip", ...],
      "completed_dates": ["2026-03-30", "2026-03-31"]
    }

Behavior: when we switch to a new date, ``processed_zips`` resets. When
a date completes, it moves to ``completed_dates`` and ``current_date``
clears. Next run reads this file and resumes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog


log = structlog.get_logger()

DEFAULT_CHECKPOINT_PATH = Path("data/consolidate-checkpoint.json")


def _empty_state() -> dict[str, Any]:
    return {"current_date": None, "processed_zips": [], "completed_dates": []}


def load_checkpoint_state(path: Path = DEFAULT_CHECKPOINT_PATH) -> dict[str, Any]:
    """Load checkpoint state from disk, returning an empty shell on failure."""
    if not path.exists():
        return _empty_state()
    try:
        with path.open("r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("checkpoint_load_failed", error=str(e))
        return _empty_state()


def save_checkpoint_state(state: dict[str, Any], path: Path = DEFAULT_CHECKPOINT_PATH) -> None:
    """Persist checkpoint state, creating the parent directory if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("w") as f:
            json.dump(state, f, indent=2)
        log.info(
            "checkpoint_saved",
            date=state.get("current_date"),
            processed=len(state.get("processed_zips", [])),
        )
    except OSError as e:
        log.exception("checkpoint_save_failed", error=str(e))


def update_checkpoint_progress(
    date: str, zip_filename: str, path: Path = DEFAULT_CHECKPOINT_PATH
) -> None:
    """Record that ``zip_filename`` has been processed for ``date``.

    Resets ``processed_zips`` when the date changes (we don't keep stale
    entries from a previous date).
    """
    state = load_checkpoint_state(path)

    if state["current_date"] != date:
        state["current_date"] = date
        state["processed_zips"] = []

    if zip_filename not in state["processed_zips"]:
        state["processed_zips"].append(zip_filename)

    save_checkpoint_state(state, path)


def mark_date_complete(date: str, path: Path = DEFAULT_CHECKPOINT_PATH) -> None:
    """Mark a date as fully consolidated and clear the in-progress state."""
    state = load_checkpoint_state(path)

    if date not in state["completed_dates"]:
        state["completed_dates"].append(date)

    state["current_date"] = None
    state["processed_zips"] = []
    save_checkpoint_state(state, path)


def should_skip_zip(date: str, zip_filename: str, path: Path = DEFAULT_CHECKPOINT_PATH) -> bool:
    """Return True if this ZIP has already been processed for this date."""
    state = load_checkpoint_state(path)
    if state["current_date"] != date:
        return False
    return zip_filename in state.get("processed_zips", [])


def is_date_completed(date: str, path: Path = DEFAULT_CHECKPOINT_PATH) -> bool:
    """Return True if a date has been marked complete."""
    state = load_checkpoint_state(path)
    return date in state.get("completed_dates", [])
