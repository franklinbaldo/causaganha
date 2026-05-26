"""Batched upload-only drain mode.

Bypasses the full SyncManifest cold-start. Queries the remote
``sync-manifest.parquet`` (rendered from the canonical CSV) via DuckDB
httpfs, fetches small batches of pending entries, drains them through
the existing download/upload helpers, and writes a per-run delta CSV
that gets uploaded to IA at exit.

Designed for the upload-backlog workflow: full-manifest load takes
~2 min on cold start; this path takes ~5 s and lets workers start
uploading immediately.
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
from djen_backup.archive import (
    CircuitBreaker,
    ItemBusyError,
    check_ia_file_exists,
    get_ia_item_id,
    upload_zip,
)
from djen_backup.djen import DJENNotFoundError, download_zip, get_caderno_url


log = structlog.get_logger()

PARQUET_URL = "https://archive.org/download/causaganha-dashboard/sync-manifest.parquet"
IA_DASHBOARD_ITEM = "causaganha-dashboard"
_MIN_CSV_SIZE = 50


def fetch_pending_batch(
    con: duckdb.DuckDBPyConnection,
    parquet_url: str,
    batch_size: int,
    seen: set[tuple[str, date]] | None = None,
) -> list[tuple[str, date]]:
    """Fetch a random batch of pending (tribunal, date) pairs from the remote parquet.

    Prioritises ``djen_status='confirmed'`` entries (verified by probe) over
    plain ``'available'`` entries so that probe output is consumed first and
    no worker time is wasted on unverified items.
    """
    seen_filter = ""
    if seen:
        seen_list = ", ".join(f"'{t}_{d.isoformat()}'" for t, d in seen)
        seen_filter = f"AND (tribunal || '_' || CAST(date AS VARCHAR)) NOT IN ({seen_list})"

    rows = con.execute(
        f"""
        SELECT tribunal, date FROM read_parquet('{parquet_url}')
        WHERE djen_status IN ('available', 'confirmed')
          AND (ia_status IS NULL OR ia_status != 'uploaded')
          {seen_filter}
        ORDER BY
            CASE WHEN djen_status = 'confirmed' THEN 0 ELSE 1 END,
            random()
        LIMIT {batch_size}
        """
    ).fetchall()
    return [(r[0], r[1]) for r in rows]


class DeltaWriter:
    """Append-only CSV of (tribunal, date, ia_status, djen_status, updated_at)."""

    def __init__(self, path: Path) -> None:
        """Initialize the DeltaWriter.

        Args:
            path: Path to write the CSV to.
        """
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("tribunal,date,ia_status,djen_status,updated_at\n", encoding="utf-8")
        self.count = 0
        self.absent_count = 0
        self._lock = asyncio.Lock()

    async def mark_uploaded(self, tribunal: str, d: date) -> None:
        """Record a successful upload to Internet Archive."""
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        async with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(f"{tribunal},{d.isoformat()},uploaded,,{ts}\n")
            self.count += 1

    async def mark_absent(self, tribunal: str, d: date) -> None:
        """Record a DJEN 404 so the parquet stops treating this entry as pending."""
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        async with self._lock:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(f"{tribunal},{d.isoformat()},,absent,{ts}\n")
            self.absent_count += 1


async def _drain_one(
    tribunal: str,
    d: date,
    dl_client: httpx.AsyncClient,
    upload_client: httpx.AsyncClient,
    djen_proxy_url: str,
    breaker: CircuitBreaker,
    delta_writer: DeltaWriter,
) -> None:
    """Process a single (tribunal, date) pair: fetch URL, download, upload, log delta."""
    item_id = get_ia_item_id(tribunal, d)
    zip_path: Path | None = None
    try:
        if await check_ia_file_exists(upload_client, tribunal, d):
            await delta_writer.mark_uploaded(tribunal, d)
            return
        url = await get_caderno_url(dl_client, djen_proxy_url, tribunal, d)
        zip_path = await download_zip(dl_client, url)
        # Loop until lock available — re-queue pattern would need shared queue;
        # simpler here: just retry briefly on busy, then give up for this run
        for attempt in range(5):
            try:
                ok = await upload_zip(
                    upload_client, item_id, zip_path, circuit_breaker=breaker, try_lock=True
                )
                if ok:
                    await delta_writer.mark_uploaded(tribunal, d)
                return
            except ItemBusyError:
                await asyncio.sleep(0.5 * (attempt + 1))
    except DJENNotFoundError:
        log.debug("drain_skip_404", tribunal=tribunal, date=d.isoformat())
        await delta_writer.mark_absent(tribunal, d)
    except (httpx.HTTPError, httpx.RequestError) as exc:
        log.debug("drain_skip_error", tribunal=tribunal, date=d.isoformat(), error=str(exc))
    finally:
        if zip_path is not None:
            with contextlib.suppress(OSError):
                zip_path.unlink(missing_ok=True)


async def _drain_worker(
    queue: asyncio.Queue,
    dl_client: httpx.AsyncClient,
    upload_client: httpx.AsyncClient,
    djen_proxy_url: str,
    breaker: CircuitBreaker,
    delta_writer: DeltaWriter,
    deadline: float,
) -> None:
    """Worker: pulls (tribunal, date) pairs from queue, processes each."""
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
            await _drain_one(
                tribunal, d, dl_client, upload_client, djen_proxy_url, breaker, delta_writer
            )
        finally:
            queue.task_done()


async def upload_delta(delta_path: Path, ia_auth: str) -> bool:
    """Upload delta CSV to Internet Archive."""
    stat = await anyio.Path(delta_path).stat()
    if stat.st_size <= _MIN_CSV_SIZE:  # only header
        return False
    target = f"upload-deltas/{delta_path.name}"
    async with create_upload_client(ia_auth) as client:
        return await upload_to_ia(client, IA_DASHBOARD_ITEM, delta_path, target)


async def drain(
    *,
    workers: int,
    batch_size: int,
    deadline_seconds: float,
    djen_proxy_url: str,
    ia_auth: str,
    parquet_url: str = PARQUET_URL,
) -> int:
    """Run the batched drain loop. Returns number of uploads completed."""
    deadline = time.monotonic() + deadline_seconds
    delta_path = Path(f"data/upload-deltas-{int(time.time())}.csv")
    delta_writer = DeltaWriter(delta_path)
    breaker = CircuitBreaker(threshold=5, recovery_timeout=30.0)

    duck = duckdb.connect()
    duck.execute("INSTALL httpfs; LOAD httpfs;")

    queue: asyncio.Queue = asyncio.Queue(maxsize=batch_size * 2)
    seen: set[tuple[str, date]] = set()

    dl_timeout = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=10.0)
    async with (
        httpx.AsyncClient(timeout=dl_timeout, follow_redirects=True) as dl_client,
        create_upload_client(ia_auth) as upload_client,
    ):
        worker_tasks = [
            asyncio.create_task(
                _drain_worker(
                    queue, dl_client, upload_client, djen_proxy_url, breaker, delta_writer, deadline
                )
            )
            for _ in range(workers)
        ]

        # Producer: fetch a batch, enqueue, wait for batch drained, repeat.
        try:
            while time.monotonic() < deadline:
                batch = fetch_pending_batch(duck, parquet_url, batch_size, seen)
                fresh = [e for e in batch if e not in seen]
                if not fresh:
                    if len(batch) < batch_size:
                        log.info("drain_no_more_pending")
                        break
                    await asyncio.sleep(1)
                    continue
                log.info("drain_batch_fetched", size=len(fresh), uploads_so_far=delta_writer.count)
                for entry in fresh:
                    seen.add(entry)
                    await queue.put(entry)
                remaining = max(0.0, deadline - time.monotonic())
                try:
                    await asyncio.wait_for(queue.join(), timeout=remaining)
                except TimeoutError:
                    break
        finally:
            for _ in range(workers):
                await queue.put(None)
            await asyncio.gather(*worker_tasks, return_exceptions=True)

    log.info(
        "drain_complete",
        uploads=delta_writer.count,
        absent_marked=delta_writer.absent_count,
        delta=str(delta_path),
    )

    if breaker.was_opened:
        log.warning(
            "drain_completed_with_throttling",
            reason=(
                "Circuit breaker opened during the run due to "
                "S3/WAF saturation. Performance was throttled."
            ),
        )

    if delta_writer.count > 0:
        try:
            ok = await upload_delta(delta_path, ia_auth)
            log.info("delta_uploaded" if ok else "delta_upload_failed", count=delta_writer.count)
        except (httpx.HTTPError, httpx.RequestError, OSError) as exc:
            log.warning("delta_upload_exception", error=str(exc))

    return delta_writer.count
