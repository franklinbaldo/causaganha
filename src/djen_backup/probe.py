"""Lightweight DJEN availability probe for the upload-backlog pipeline.

Fetches batches of pending entries from the remote sync-manifest.parquet and
probes each one with a single ``get_caderno_url`` call — no download, no IA
upload.  Results are written to an immutable manifest-log/ segment (Phase 2
of docs/planning/manifest-source-of-truth.md — formerly ``upload-deltas-*``)
that the compactor merges on the next run:

* 404/400/200-"Sem comunicações" → ``djen_status='absent'`` with the raw
  transport code → removed from the pending pool permanently
* URL found → ``djen_status='confirmed'`` → drain prioritises these entries

Running probe in parallel with drain (two separate GHA jobs) means the drain
workers spend zero time on 404s and can focus entirely on real content.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import httpx
import structlog


if TYPE_CHECKING:
    from datetime import date

from djen_backup.djen import DJENNotFoundError, get_caderno_url
from djen_backup.segments import SegmentWriter, absent_raw_code, segment_name
from djen_backup.segments import upload_segment as _upload_segment


log = structlog.get_logger()

PARQUET_URL = "https://archive.org/download/causaganha-dashboard/sync-manifest.parquet"
IA_DASHBOARD_ITEM = "causaganha-dashboard"


# ---------------------------------------------------------------------------
# Batch fetcher — same pending filter as drain, same random ordering
# ---------------------------------------------------------------------------


def fetch_pending_batch(
    con: duckdb.DuckDBPyConnection,
    parquet_url: str,
    batch_size: int,
    seen: set[tuple[str, date]] | None = None,
) -> list[tuple[str, date]]:
    """Fetch a random batch of unconfirmed pending (tribunal, date) pairs."""
    seen_filter = ""
    if seen:
        seen_list = ", ".join(f"'{t}_{d.isoformat()}'" for t, d in seen)
        seen_filter = f"AND (tribunal || '_' || CAST(date AS VARCHAR)) NOT IN ({seen_list})"

    rows = con.execute(
        f"""
        SELECT tribunal, date FROM read_parquet(?)
        WHERE djen_status = 'available'
          AND (ia_status IS NULL OR ia_status != 'uploaded')
          {seen_filter}
        ORDER BY random()
        LIMIT ?
        """,  # noqa: S608
        (parquet_url, batch_size),
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


async def _probe_one(
    tribunal: str,
    d: date,
    client: httpx.AsyncClient,
    djen_proxy_url: str,
    delta_writer: SegmentWriter,
) -> None:
    """Probe a single (tribunal, date) — only checks URL existence."""
    try:
        await get_caderno_url(client, djen_proxy_url, tribunal, d)
        await delta_writer.mark_confirmed(tribunal, d)
        log.debug("probe_confirmed", tribunal=tribunal, date=d.isoformat())
    except DJENNotFoundError as exc:
        # Verified absence — keep the raw transport code (404/400, or
        # no_publications for HTTP 200 "Sem comunicações"), never a bare 200.
        await delta_writer.mark_absent(tribunal, d, absent_raw_code(exc.status_code))
        log.debug("probe_absent", tribunal=tribunal, date=d.isoformat())
    except (httpx.HTTPError, httpx.RequestError) as exc:
        # Transient error — don't mark either way, will retry next run
        log.debug("probe_skip_error", tribunal=tribunal, date=d.isoformat(), error=str(exc))


async def _probe_worker(
    queue: asyncio.Queue,
    client: httpx.AsyncClient,
    djen_proxy_url: str,
    delta_writer: SegmentWriter,
    deadline: float,
) -> None:
    while True:
        try:
            entry = await asyncio.wait_for(queue.get(), timeout=2.0)
        except TimeoutError:
            if time.monotonic() > deadline:
                return
            continue
        if entry is None:
            queue.task_done()
            return
        if time.monotonic() > deadline:
            queue.task_done()
            continue
        tribunal, d = entry
        try:
            await _probe_one(tribunal, d, client, djen_proxy_url, delta_writer)
        finally:
            queue.task_done()


# ---------------------------------------------------------------------------
# Delta upload helper (mirrors drain.upload_delta)
# ---------------------------------------------------------------------------


async def upload_delta(delta_path: Path, ia_auth: str) -> bool:
    """Upload the run's segment to manifest-log/ on IA (skips header-only files)."""
    return await _upload_segment(delta_path, ia_auth)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


async def probe(
    *,
    workers: int,
    batch_size: int,
    deadline_seconds: float,
    djen_proxy_url: str,
    ia_auth: str,
    parquet_url: str = PARQUET_URL,
) -> tuple[int, int]:
    """Run the probe loop. Returns (confirmed_count, absent_count)."""
    deadline = time.monotonic() + deadline_seconds
    delta_path = Path("data") / segment_name("probe")
    delta_writer = SegmentWriter(delta_path)

    duck = duckdb.connect()
    duck.execute("INSTALL httpfs; LOAD httpfs;")

    queue: asyncio.Queue = asyncio.Queue(maxsize=batch_size * 2)
    seen: set[tuple[str, date]] = set()

    # Light timeout — probe is just a URL fetch, should be fast
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        worker_tasks = [
            asyncio.create_task(
                _probe_worker(queue, client, djen_proxy_url, delta_writer, deadline)
            )
            for _ in range(workers)
        ]

        try:
            while time.monotonic() < deadline:
                batch = fetch_pending_batch(duck, parquet_url, batch_size, seen)
                fresh = [e for e in batch if e not in seen]
                if not fresh:
                    if len(batch) < batch_size:
                        log.info("probe_no_more_pending")
                        break
                    await asyncio.sleep(1)
                    continue
                log.info(
                    "probe_batch_fetched",
                    size=len(fresh),
                    confirmed_so_far=delta_writer.confirmed_count,
                    absent_so_far=delta_writer.absent_count,
                )
                for entry in fresh:
                    seen.add(entry)
                    await queue.put(entry)
                remaining = max(0.0, deadline - time.monotonic())
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(queue.join(), timeout=remaining)
        finally:
            for _ in range(workers):
                await queue.put(None)
            await asyncio.gather(*worker_tasks, return_exceptions=True)

    log.info(
        "probe_complete",
        confirmed=delta_writer.confirmed_count,
        absent=delta_writer.absent_count,
        delta=str(delta_path),
    )

    total = delta_writer.confirmed_count + delta_writer.absent_count
    if total > 0:
        try:
            ok = await upload_delta(delta_path, ia_auth)
            log.info("probe_delta_uploaded" if ok else "probe_delta_upload_failed", total=total)
        except (httpx.HTTPError, httpx.RequestError, OSError) as exc:
            log.warning("probe_delta_upload_exception", error=str(exc))

    return delta_writer.confirmed_count, delta_writer.absent_count
