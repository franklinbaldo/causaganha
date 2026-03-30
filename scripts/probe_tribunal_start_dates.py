#!/usr/bin/env python3

EARLIEST_TRIBUNAL_YEAR = 1990
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_404_NOT_FOUND = 404

"""Probe the true start date for each DJEN tribunal.

Discovers when each of the 96 DJEN tribunals started publishing data using
an exponential probe backwards in time, followed by a lateral window check
to account for holidays and weekends (requiring a 60-day gap to confirm the start).

Outputs to dashboard/public/tribunal_start_dates.json.
"""

import argparse
import asyncio
import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx

from causaganha.config import TRIBUNAIS


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROXY_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"
OUTPUT_FILE = Path("dashboard/public/tribunal_start_dates.json")

# Concurrency limits - Increased for faster discovery
MAX_CONCURRENT_REQUESTS = 10

# Create a semaphore for global rate limiting
sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


async def check_date_has_data(client: httpx.AsyncClient, tribunal: str, target_date: date) -> bool:
    """Check if a tribunal has data for a specific date via the DJEN proxy."""
    url = f"{PROXY_URL}/api/v1/caderno/{tribunal}/{target_date.isoformat()}/D"

    async with sem:
        try:
            # The proxy returns 404 when there is no data
            response = await client.get(url, timeout=30.0)
            if response.status_code == HTTP_404_NOT_FOUND:
                return False
            response.raise_for_status()

            # Additional check: confirm valid JSON and presence of 'url'
            data = response.json()
            return bool(data and data.get("url"))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTP_404_NOT_FOUND:
                return False
            if e.response.status_code == HTTP_429_TOO_MANY_REQUESTS:
                # Retry on 429 using exponential backoff inside the function
                logger.warning(
                    "Rate limited (429) checking %s at %s. Retrying in 10s...",
                    tribunal,
                    target_date,
                )
                await asyncio.sleep(10.0)
                return await check_date_has_data(client, tribunal, target_date)
            logger.warning("HTTP error checking %s at %s: %s", tribunal, target_date, e)
            return False
        except Exception as e:
            logger.warning("Error checking %s at %s: %s", tribunal, target_date, e)
            return False


async def confirm_void(client: httpx.AsyncClient, tribunal: str, target_date: date) -> bool:
    """Check if `target_date` AND `target_date - 60 days` are BOTH absent.

    If both are absent, this confirms a >= 60 day patch (primordial void).
    Uses concurrent fetching for speed.
    """
    # Check X and X - 60 simultaneously
    date1 = target_date
    date2 = target_date - timedelta(days=60)

    res1, res2 = await asyncio.gather(
        check_date_has_data(client, tribunal, date1), check_date_has_data(client, tribunal, date2)
    )

    # Void is confirmed if BOTH are absent (False)
    return not res1 and not res2


async def find_start_date(client: httpx.AsyncClient, tribunal: str) -> str | None:
    """Find the true start date for a tribunal using exponential 60-day patch confirmation.

    Phase 1: Exponential probe backwards from today (step=60, 120, 240, 480...)
    Phase 2: Binary search to find the exact right edge of the 60-day void.
    """
    today = datetime.now(UTC).date()
    logger.info("[%s] Starting exponential probe...", tribunal)

    # Verify if the tribunal has ANY data at all recently
    res_today, res_today_30 = await asyncio.gather(
        check_date_has_data(client, tribunal, today),
        check_date_has_data(client, tribunal, today - timedelta(days=30)),
    )
    if not res_today and not res_today_30:
        logger.warning("[%s] No recent data found. Is the tribunal active?", tribunal)
        # It's possible the tribunal is completely offline or not in DJEN
        return None

    # Phase 1: Exponential probe backwards
    step = 60
    current_date = today - timedelta(days=step)
    prev_date = today

    lo_date = None  # Edge of void (no data)
    hi_date = today  # Known to have data eventually

    while True:
        # Guard against going too far back (e.g. before 1990)
        if current_date.year < EARLIEST_TRIBUNAL_YEAR:
            logger.warning("[%s] Probe went too far back (%s).", tribunal, current_date)
            return None

        is_void = await confirm_void(client, tribunal, current_date)

        if is_void:
            lo_date = current_date
            hi_date = prev_date
            logger.info(
                "[%s] Confirmed >= 60 day void at %s. Bracket found: [%s, %s]",
                tribunal,
                lo_date,
                lo_date,
                hi_date,
            )
            break

        logger.info("[%s] No void at %s. Probing further back...", tribunal, current_date)
        prev_date = current_date

        # Double the step (60, 120, 240, 480, 960...)
        step *= 2
        current_date = today - timedelta(days=step)

    if not lo_date:
        return None

    logger.info("[%s] Phase 2: Binary search between %s and %s", tribunal, lo_date, hi_date)

    # Phase 2: Binary search
    # We must use `confirm_void` as the predicate to maintain a monotonic signal.
    # We want to narrow down the bracket [lo_date (is_void=True), hi_date (is_void=False)]
    while (hi_date - lo_date).days > 1:
        mid_days = (hi_date - lo_date).days // 2
        mid_date = lo_date + timedelta(days=mid_days)

        logger.info(
            "[%s] Binary search checking %s (span: %s days)",
            tribunal,
            mid_date,
            (hi_date - lo_date).days,
        )
        is_void = await confirm_void(client, tribunal, mid_date)

        if is_void:
            # Still in the void
            lo_date = mid_date
        else:
            # Not a void (we hit data, or at least a gap < 60 days)
            hi_date = mid_date

    # The exact right edge of the void is `hi_date`.
    # Since `confirm_void(hi_date)` returned False, it means either `hi_date` OR `hi_date - 60` has data.
    # To find the EXACT start date, we scan forward starting from `hi_date - 60` up to `hi_date`.
    logger.info(
        "[%s] Void right edge found at %s. Scanning forward to find exact start date...",
        tribunal,
        hi_date,
    )

    start_scan_date = hi_date - timedelta(days=60)

    # We linearly scan forward for the exact first day with data
    for i in range(61):
        check_d = start_scan_date + timedelta(days=i)
        if await check_date_has_data(client, tribunal, check_d):
            logger.info("[%s] Exact start date found: %s", tribunal, check_d)
            return check_d.isoformat()

    # Fallback (should not be reached if confirm_void returned False)
    logger.info("[%s] Fallback start date found: %s", tribunal, hi_date)
    return hi_date.isoformat()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-tribunals", type=int, default=0, help="Max tribunals to check (for testing)"
    )
    args = parser.parse_args()

    # Use a large timeout for the client and higher connection limits
    transport = httpx.AsyncHTTPTransport(retries=3)

    results = {}

    # Check if we already have some results to resume
    if OUTPUT_FILE.exists():
        try:
            with Path(OUTPUT_FILE).open() as f:
                results = json.load(f)
            logger.info("Loaded %s existing results from %s", len(results), OUTPUT_FILE)
        except json.JSONDecodeError:
            pass

    async with httpx.AsyncClient(transport=transport, timeout=60.0) as client:
        tribunals_to_check = TRIBUNAIS
        if args.max_tribunals > 0:
            tribunals_to_check = tribunals_to_check[: args.max_tribunals]

        for tribunal in tribunals_to_check:
            if tribunal in results:
                logger.info(
                    "[%s] Already processed (start date: %s), skipping.",
                    tribunal,
                    results[tribunal],
                )
                continue

            start_date = await find_start_date(client, tribunal)
            if start_date:
                results[tribunal] = start_date
            else:
                results[tribunal] = None

            # Save incrementally
            OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with Path(OUTPUT_FILE).open("w") as f:
                json.dump(results, f, indent=2)

    logger.info("Finished processing. Results saved to %s", OUTPUT_FILE)


if __name__ == "__main__":
    asyncio.run(main())
