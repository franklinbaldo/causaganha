"""Lightweight DJEN availability probe for the upload-backlog pipeline.

Fetches batches of pending entries from the remote sync-manifest.parquet and
probes each one with a single ``get_caderno_url`` call — no download, no IA
upload.  Results are written to a delta CSV that ``render_manifest_parquet``
will merge on the next run:

* 404 → ``djen_status='absent'``   → removed from the pending pool permanently
* URL found → ``djen_status='confirmed'`` → drain prioritises these entries

Running probe in parallel with drain (two separate GHA jobs) means the drain
workers spend zero time on 404s and can focus entirely on real content.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from datetime import UTC, date, datetime
from pathlib import Path

import anyio
import duckdb
import httpx
import structlog

from causaganha.pipeline.ia_s3 import create_upload_client, upload_to_ia
from djen_backup.djen import DJENNotFoundError, get_caderno_url


log = structlog.get_logger()

PARQUET_URL = "https://archive.org/download/causaganha-dashboard/sync-manifest.parquet"
IA_DASHBOARD_ITEM = "causaganha-dashboard"
_MIN_CSV_SIZE = 50



# ---------------------------------------------------------------------------
# Delta writer (probe flavour — no upload tracking, just absent + confirmed)
# ---------------------------------------------------------------------------


class ProbeDeltaWriter:
    """Append-only CSV of probe results: absent and confirmed entries."""

    def __init__(self, path: Path) -> None:
        """Initialize the ProbeDeltaWriter.

        Args:
            path: Path to write the CSV to.
        """
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            "tribunal,date,ia_status,djen_status,updated_at\n", encoding="utf-8"
        )
        self.absent_count = 0
        self.confirmed_count = 0
        self._lock = asyncio.Lock()


    async def mark_absent(self, tribunal: str, d: date) -> None:
        """Mark entry as absent on DJEN (returned 404)."""
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        async with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(f"{tribunal},{d.isoformat()},,absent,{ts}\n")
            self.absent_count += 1


    async def mark_confirmed(self, tribunal: str, d: date) -> None:
        """Mark entry as DJEN-confirmed — drain should prioritise it."""
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        async with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(f"{tribunal},{d.isoformat()},,confirmed,{ts}\n")
            self.confirmed_count += 1


# ---------------------------------------------------------------------------
# Batch fetcher — same pending filter as drain, same random ordering
# ---------------------------------------------------------------------------


def fetch_pending_batch(
    con: duckdb.DuckDBPyConnection, parquet_url: str, batch_size: int
) -> list[tuple[str, date]]:
    """Fetch a random batch of unconfirmed pending (tribunal, date) pairs."""
    rows = con.execute(
        """
        SELECT tribunal, date FROM read_parquet(?)
        WHERE djen_status = 'available'
          AND (ia_status IS NULL OR ia_status != 'uploaded')
        ORDER BY random()
        LIMIT ?
        """,
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
    delta_writer: ProbeDeltaWriter,
) -> None:
    """Probe a single (tribunal, date) — only checks URL existence."""
    try:
        await get_caderno_url(client, djen_proxy_url, tribunal, d)
        await delta_writer.mark_confirmed(tribunal, d)
        log.debug("probe_confirmed", tribunal=tribunal, date=d.isoformat())
    except DJENNotFoundError:
        await delta_writer.mark_absent(tribunal, d)
        log.debug("probe_absent", tribunal=tribunal, date=d.isoformat())
    except (httpx.HTTPError, httpx.RequestError) as exc:
        # Transient error — don't mark either way, will retry next run
        log.debug("probe_skip_error", tribunal=tribunal, date=d.isoformat(), error=str(exc))


async def _probe_worker(
    queue: asyncio.Queue,
    client: httpx.AsyncClient,
    djen_proxy_url: str,
    delta_writer: ProbeDeltaWriter,
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
    """Upload delta CSV to Internet Archive."""
    stat = await anyio.Path(delta_path).stat()
    if stat.st_size <= _MIN_CSV_SIZE:  # only header
        return False
    target = f"upload-deltas/{delta_path.name}"
    async with create_upload_client(ia_auth) as client:
        return await upload_to_ia(client, IA_DASHBOARD_ITEM, delta_path, target)



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
    delta_path = Path(f"data/upload-deltas-probe-{int(time.time())}.csv")
    delta_writer = ProbeDeltaWriter(delta_path)


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
                batch = fetch_pending_batch(duck, parquet_url, batch_size)
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
