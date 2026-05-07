#!/usr/bin/env python3
"""One-shot backfill — drain djen_raw="" rows by hitting the DJEN proxy live.

Bypasses ``collect-zips``' Phase 0 IA discovery and engine plumbing (which is
currently breaching GHA's timeout, see PR #677) to push the unknown bucket
forward. Pulls the canonical manifest from IA, classifies every unknown row
in parallel against the DJEN proxy, then merges and uploads the result back
to IA in one shot.

Designed to be safe to re-run: it only writes ``djen_raw`` for rows where
``djen_raw`` is currently empty, and ``upload_to_ia`` re-downloads-and-merges
to avoid clobbering concurrent updates.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import sys
from collections import Counter
from datetime import datetime

import httpx
import structlog

from djen_backup.djen import (
    DJENNotFoundError,
    DJENRateLimitedError,
    get_caderno_url,
)
from djen_backup.manifest import SyncManifest


DJEN_PROXY_FALLBACK = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"

# Tuned for backfill: still respectful of the proxy. The first run of this
# script at 24x concurrency tripped CloudFront/WAF (PR #677), so keep this
# low. The proxy can sustain a few req/s but rejects bursts.
CONCURRENCY = 4
PER_REQUEST_TIMEOUT = 30.0
DEADLINE_SECONDS = int(os.environ.get("DRAIN_DEADLINE_SECONDS", "1500"))  # 25 min default
LIMIT = int(os.environ.get("DRAIN_LIMIT", "0"))  # 0 = no cap
UPLOAD_INTERVAL_S = 600  # push to IA every ~10min while draining
WAF_403_COOLDOWN_S = 30  # consecutive 403s → sleep this long before continuing
WAF_403_THRESHOLD = 5  # consecutive 403s required to trip the cooldown

log = structlog.get_logger()


def _proxy_base() -> str:
    return os.environ.get("DJEN_PROXY_URL", "").strip() or DJEN_PROXY_FALLBACK


def _ia_auth() -> str:
    access = os.environ.get("IAS3_ACCESS_KEY", "").strip()
    secret = os.environ.get("IAS3_SECRET_KEY", "").strip()
    if not access or not secret:
        msg = "IAS3_ACCESS_KEY / IAS3_SECRET_KEY env vars not set"
        raise RuntimeError(msg)
    return f"LOW {access}:{secret}"


async def _classify(client: httpx.AsyncClient, base: str, tribunal, d) -> str:
    """Hit the DJEN proxy once and return the canonical raw_status string."""
    try:
        await get_caderno_url(client, base, tribunal, d)
    except DJENNotFoundError as exc:
        return str(exc.status_code)
    except DJENRateLimitedError:
        return "403"
    except httpx.TimeoutException:
        return "timeout"
    except httpx.HTTPStatusError as exc:
        return str(exc.response.status_code)
    except httpx.HTTPError:
        return "network"
    return "200"


async def main() -> int:
    started = datetime.now().astimezone().isoformat()
    base = _proxy_base()
    auth = _ia_auth()

    print("=" * 78)
    print("DRAIN UNKNOWNS")
    print("=" * 78)
    print(f"started:        {started}")
    print(f"proxy_base:     {base}")
    print(f"concurrency:    {CONCURRENCY}")
    print(f"deadline_s:     {DEADLINE_SECONDS}")
    print(f"limit:          {LIMIT or 'no cap'}")

    manifest = SyncManifest()
    loaded = await manifest.load_from_ia()
    print(f"manifest_rows:  {loaded}")

    unknowns = [
        e
        for e in manifest._entries.values()
        if not (e.djen_raw or "").strip() and e.ia_status != "uploaded"
    ]
    print(f"unknowns:       {len(unknowns)}")
    if LIMIT > 0:
        unknowns = unknowns[:LIMIT]
        print(f"capped to:      {len(unknowns)}")

    if not unknowns:
        print("nothing to do.")
        return 0

    # Bounded worker pool: N=CONCURRENCY consumers pulling from a queue, so
    # we don't allocate a coroutine per row up front (Codex P2, PR #677).
    queue: asyncio.Queue = asyncio.Queue(maxsize=CONCURRENCY * 4)
    results: Counter[str] = Counter()
    processed = 0
    consecutive_403 = 0
    last_upload = asyncio.get_event_loop().time()
    deadline = asyncio.get_event_loop().time() + DEADLINE_SECONDS

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(PER_REQUEST_TIMEOUT), follow_redirects=True
    ) as client:

        async def _worker() -> None:
            nonlocal processed, consecutive_403
            while True:
                entry = await queue.get()
                try:
                    if entry is None or asyncio.get_event_loop().time() > deadline:
                        return
                    raw = await _classify(client, base, entry.tribunal, entry.date)
                    if raw == "403":
                        # WAF/CloudFront block. Don't pollute the manifest with a
                        # transient signal — leave djen_raw="" so the next sync
                        # reclassifies cleanly. If we keep tripping, back off.
                        consecutive_403 += 1
                        results["403"] += 1
                        if consecutive_403 >= WAF_403_THRESHOLD:
                            print(
                                f"  WAF cooldown: {consecutive_403} consecutive 403s, "
                                f"sleeping {WAF_403_COOLDOWN_S}s"
                            )
                            await asyncio.sleep(WAF_403_COOLDOWN_S)
                        continue
                    consecutive_403 = 0
                    await manifest.mark_djen_raw(entry.tribunal, entry.date, raw)
                    results[raw] += 1
                    processed += 1
                    if processed % 500 == 0:
                        elapsed = asyncio.get_event_loop().time() - (deadline - DEADLINE_SECONDS)
                        rate = processed / max(elapsed, 1)
                        print(
                            f"  progress: {processed}/{len(unknowns)} "
                            f"({rate:.1f} req/s)  current={dict(results.most_common(5))}"
                        )
                finally:
                    queue.task_done()

        async def _producer() -> None:
            for entry in unknowns:
                if asyncio.get_event_loop().time() > deadline:
                    break
                await queue.put(entry)
            for _ in range(CONCURRENCY):
                await queue.put(None)  # sentinel to stop each worker

        async def _periodic_upload() -> None:
            nonlocal last_upload
            while True:
                await asyncio.sleep(60)
                if asyncio.get_event_loop().time() > deadline:
                    return
                if asyncio.get_event_loop().time() - last_upload < UPLOAD_INTERVAL_S:
                    continue
                last_upload = asyncio.get_event_loop().time()
                try:
                    if await manifest.upload_to_ia(auth):
                        print(f"  [periodic] uploaded manifest after {processed} processed")
                except (httpx.HTTPError, OSError) as exc:
                    print(f"  [periodic] upload failed: {exc!r}")

        upload_task = asyncio.create_task(_periodic_upload())
        producer_task = asyncio.create_task(_producer())
        worker_tasks = [asyncio.create_task(_worker()) for _ in range(CONCURRENCY)]
        try:
            await asyncio.gather(producer_task, *worker_tasks)
        finally:
            upload_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await upload_task

    print()
    print("=" * 78)
    print("RESULT")
    print("=" * 78)
    print(f"processed: {processed}")
    print("by raw_status:")
    for raw, n in results.most_common():
        print(f"  {raw!r:>12s}  {n:>8d}")

    print()
    print("Final upload to IA…")
    ok = await manifest.upload_to_ia(auth)
    if ok:
        await manifest.upload_summary_to_ia(auth)
        print("Final upload OK.")
        return 0
    print("Final upload FAILED.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
