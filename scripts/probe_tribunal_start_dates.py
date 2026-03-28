#!/usr/bin/env python3
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
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx


# Add src/ to sys.path so we can import from causaganha
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from causaganha.config import TRIBUNAIS


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROXY_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"
OUTPUT_FILE = Path("dashboard/public/tribunal_start_dates.json")

# Concurrency limits - Reduced to avoid 429
MAX_CONCURRENT_REQUESTS = 1

# Create a semaphore for global rate limiting
sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


async def check_date_has_data(client: httpx.AsyncClient, tribunal: str, target_date: date) -> bool:
    """Check if a tribunal has data for a specific date via the DJEN proxy."""
    url = f"{PROXY_URL}/api/v1/caderno/{tribunal}/{target_date.isoformat()}/D"

    async with sem:
        try:
            # The proxy returns 404 when there is no data
            response = await client.get(url, timeout=30.0)
            if response.status_code == 404:
                return False
            response.raise_for_status()

            # Additional check: confirm valid JSON and presence of 'url'
            data = response.json()
            if data and data.get("url"):
                return True
            return False
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            if e.response.status_code == 429:
                # Retry on 429 using exponential backoff inside the function
                logger.warning(
                    f"Rate limited (429) checking {tribunal} at {target_date}. Cooling down for 30s..."
                )
                await asyncio.sleep(30.0)
                return await check_date_has_data(client, tribunal, target_date)
            logger.warning(f"HTTP error checking {tribunal} at {target_date}: {e}")
            return False
        except Exception as e:
            logger.warning(f"Error checking {tribunal} at {target_date}: {e}")
            return False


def get_nearest_weekday(d: date) -> date:
    """If the date falls on a weekend, shift it to the nearest weekday.
    Saturday -> Friday. Sunday -> Monday.
    This guarantees mathematically that the galloping jumps never hit weekends.
    """
    if d.weekday() == 5: # Saturday
        return d - timedelta(days=1)
    elif d.weekday() == 6: # Sunday
        return d + timedelta(days=1)
    return d


async def find_start_date(client: httpx.AsyncClient, tribunal: str, known_oldest: str | None = None) -> str | None:
    """Robust Galloping Search (Exponential Jumps + Binary Search).
    
    Flies backward from the oldest known date using mathematically snapped (workday) steps.
    """
    today = date.today()
    logger.info(f"[{tribunal}] Iniciando Robust Galloping Search...")

    current = today
    if known_oldest:
        try:
             current = date.fromisoformat(known_oldest)
        except ValueError:
             pass

    # Safety: ensure starting point has data.
    current_test = get_nearest_weekday(current)
    if not await check_date_has_data(client, tribunal, current_test):
         current_test = get_nearest_weekday(today)
         if not await check_date_has_data(client, tribunal, current_test):
             # Try 15 days ago if today is holiday
             backup = get_nearest_weekday(today - timedelta(days=15))
             if not await check_date_has_data(client, tribunal, backup):
                 logger.warning(f"[{tribunal}] Tribunal totalmente inativo ou vazio. Ignorando.")
                 return None
             current_test = backup
             
    current = current_test
    logger.info(f"[{tribunal}] Ponto Inicial Confirmado: {current}")

    step = 60
    void_date = None

    # Phase 1: Exponential Jump Backwards
    while True:
        probe_date = get_nearest_weekday(current - timedelta(days=step))
        
        if probe_date.year < 1980:
            logger.warning(f"[{tribunal}] Chegou no passado remoto (1980). Assumindo limite máximo de retroatividade.")
            void_date = date(1980, 1, 1)
            break

        logger.info(f"[{tribunal}] Salto EXPO: Testando {probe_date} (Pulo de {step} dias)")
        
        if await check_date_has_data(client, tribunal, probe_date):
            # HIT! Origin is older, step x 2
            current = probe_date
            step *= 2
        else:
            # MISS! Triggers Phase 2.
            logger.info(f"[{tribunal}] DESERTO ENCONTRADO em {probe_date}. Invertendo motor para Refino Binário...")
            void_date = probe_date
            break

    # Phase 2: Robust Binary Search
    # Genesis is exactly between void_date (False) and current (True)
    low = void_date
    high = current
    
    logger.info(f"[{tribunal}] Busca Binária entre {low} e {high}")
    
    while (high - low).days > 1:
        mid_days = (high - low).days // 2
        mid_date = get_nearest_weekday(low + timedelta(days=mid_days))
        
        # Snapping safeguard (so we don't infinitely loop on weekends)
        if mid_date <= low or mid_date >= high:
            break
            
        logger.info(f"[{tribunal}] Divisão Binária: Testando {mid_date} (Janela de {(high-low).days} dias)")
        
        if await check_date_has_data(client, tribunal, mid_date):
            high = mid_date
        else:
            low = mid_date

    logger.info(f"[{tribunal}] GÊNESE ENCONTRADA: {high}")
    return high.isoformat()


async def main():
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
            with open(OUTPUT_FILE) as f:
                results = json.load(f)
            logger.info(f"Loaded {len(results)} existing results from {OUTPUT_FILE}")
        except json.JSONDecodeError:
            pass

    async with httpx.AsyncClient(transport=transport, timeout=60.0) as client:
        tribunals_to_check = TRIBUNAIS
        if args.max_tribunals > 0:
            tribunals_to_check = tribunals_to_check[: args.max_tribunals]

        for tribunal in tribunals_to_check:
            known_start = results.get(tribunal)
            
            # Since we implemented the new powerful exponential algorithm,
            # we WANT to re-probe to find if there are older dates behind the 60-day limit.
            # But we use the existing `known_start` as the seed!
            start_date = await find_start_date(client, tribunal, known_oldest=known_start)
            if start_date:
                results[tribunal] = start_date
            else:
                results[tribunal] = None

            # Save incrementally
            OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OUTPUT_FILE, "w") as f:
                json.dump(results, f, indent=2)
            
            # Cool down to avoid 429
            await asyncio.sleep(2.0)

    logger.info(f"Finished processing. Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
