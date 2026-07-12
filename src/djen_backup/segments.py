"""Immutable manifest-log segments — Phase 2 of the manifest source-of-truth plan.

Writers never rewrite the canonical manifest anymore. Each run emits its own
immutable, uniquely-named CSV segment under ``manifest-log/`` on the IA
dashboard item (see docs/planning/manifest-source-of-truth.md §4.2):

    manifest-log/<YYYYMMDDTHHMMSSZ>-<writer>-<run_id>.csv

Segment rows are *upsert events* keyed by ``(tribunal, date)`` using the same
six columns as the manifest (``tribunal,date,ia_status,djen_status,djen_raw,
updated_at``). Empty fields mean "no change" — the compaction merge is
field-by-field, last-write-wins by ``updated_at`` (plan §4.1/§4.3).

``djen_raw`` stays the raw transport code ("200", "404", "400",
"no_publications", "timeout", ...) — never a derived category.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

import anyio
import httpx
import structlog

from djen_backup.archive import put_ia_bytes


if TYPE_CHECKING:
    from pathlib import Path

log = structlog.get_logger()

IA_DASHBOARD_ITEM = "causaganha-dashboard"
SEGMENT_DIR = "manifest-log"
SEGMENT_COMPACTED_DIR = "manifest-log/compacted"
SEGMENT_HEADER = "tribunal,date,ia_status,djen_status,djen_raw,updated_at"

_IA_S3_ITEM_URL = f"https://s3.us.archive.org/{IA_DASHBOARD_ITEM}"

# A segment with only the header carries no events — don't upload it.
_MIN_SEGMENT_SIZE = len(SEGMENT_HEADER) + 1


_HTTP_OK = 200
_HTTP_ERROR = 400


def absent_raw_code(status_code: int) -> str:
    """Raw transport code for a verified absence.

    HTTP 200 with body ``"Sem comunicações"`` (no download URL) records the
    ``no_publications`` sentinel — a bare "200" would re-derive to
    ``available`` and manufacture a phantom caderno (CLAUDE.md Correctness).
    404/400 record their real HTTP code.
    """
    return "no_publications" if status_code == _HTTP_OK else str(status_code)


def default_run_id() -> str:
    """Run identifier: the GHA run id when available, else a random token."""
    return os.environ.get("GITHUB_RUN_ID", "").strip() or uuid.uuid4().hex[:8]


def segment_name(writer: str, run_id: str | None = None) -> str:
    """Unique, immutable segment file name (plan §4.2).

    ``<YYYYMMDDTHHMMSSZ>-<writer>-<run_id>.csv`` where ``run_id`` carries a
    short random suffix so two flushes from the same run within the same
    second can never collide (no clobber by construction).
    """
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    rid = run_id or default_run_id()
    return f"{ts}-{writer}-{rid}-{uuid.uuid4().hex[:6]}.csv"


def format_event(
    tribunal: str,
    d: date,
    *,
    ia_status: str = "",
    djen_status: str = "",
    djen_raw: str = "",
    updated_at: str | None = None,
) -> str:
    """Render one segment CSV line. Empty fields mean "no change"."""
    ts = updated_at or datetime.now(UTC).isoformat(timespec="seconds")
    return f"{tribunal.upper()},{d.isoformat()},{ia_status},{djen_status},{djen_raw},{ts}"


class SegmentWriter:
    """Append-only local segment file for drain/probe style writers.

    Unified replacement for the old ``DeltaWriter``/``ProbeDeltaWriter``
    (which wrote 5-column ``upload-deltas-*.csv`` files without ``djen_raw``).
    """

    def __init__(self, path: Path) -> None:
        """Create the local segment file and write the header."""
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(SEGMENT_HEADER + "\n", encoding="utf-8")
        self.count = 0  # uploaded events (drain compatibility)
        self.absent_count = 0
        self.confirmed_count = 0
        self._lock = asyncio.Lock()

    async def _append(self, line: str) -> None:
        async with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")

    async def mark_uploaded(self, tribunal: str, d: date) -> None:
        """Record a verified upload to Internet Archive."""
        await self._append(format_event(tribunal, d, ia_status="uploaded"))
        self.count += 1

    async def mark_absent(self, tribunal: str, d: date, raw: str) -> None:
        """Record a verified DJEN absence with the raw transport code.

        ``raw`` must be the observed code — "404", "400" or the
        "no_publications" sentinel for HTTP 200 with body "Sem comunicações".
        Never pass a derived category.
        """
        await self._append(format_event(tribunal, d, djen_status="absent", djen_raw=raw))
        self.absent_count += 1

    async def mark_confirmed(self, tribunal: str, d: date) -> None:
        """Record a live-verified download URL (HTTP 200 *with* URL)."""
        await self._append(format_event(tribunal, d, djen_status="confirmed", djen_raw="200"))
        self.confirmed_count += 1


async def upload_segment(path: Path, ia_auth: str, *, remote_name: str | None = None) -> bool:
    """Upload a local segment file to ``manifest-log/`` on the dashboard item.

    Returns False when the segment carries no events (header only) or the
    upload failed. Never mutates or overwrites existing segments — the name
    is unique per run/flush.
    """
    try:
        content = await anyio.Path(path).read_bytes()
    except OSError as exc:
        log.warning("segment_read_failed", path=str(path), error=str(exc))
        return False
    if len(content) <= _MIN_SEGMENT_SIZE:
        return False

    name = remote_name or path.name
    url = f"{_IA_S3_ITEM_URL}/{SEGMENT_DIR}/{name}"
    headers = {
        "Authorization": ia_auth,
        "Content-Type": "text/csv",
        "x-amz-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await put_ia_bytes(client, url, content, headers)
            if resp.status_code < _HTTP_ERROR:
                log.info("segment_uploaded", name=name, bytes=len(content))
                return True
            log.warning("segment_upload_failed", name=name, status=resp.status_code)
    except (httpx.HTTPError, httpx.RequestError) as exc:
        log.warning("segment_upload_error", name=name, error=str(exc))
    return False
