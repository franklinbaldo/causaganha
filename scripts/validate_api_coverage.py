from datetime import timezone
#!/usr/bin/env python3
"""Script to validate PJe API coverage across different Brazilian courts.

This script attempts to fetch intimations from a list of courts to determine
which ones are accessible via the API.
"""

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import structlog


# Ensure src is in pythonpath
sys.path.append(str(Path(__file__).parent.parent / "src"))

from causaganha.integrations.pje.client import PJeAPIClient


logger = structlog.get_logger()

# List of courts to check
COURTS = [
    # State Courts (TJ)
    "TJRO",
    "TJAC",
    "TJAM",
    "TJRR",
    "TJPA",
    "TJAP",
    "TJTO",
    "TJMA",
    "TJPI",
    "TJCE",
    "TJRN",
    "TJPB",
    "TJPE",
    "TJAL",
    "TJSE",
    "TJBA",
    "TJMG",
    "TJES",
    "TJRJ",
    "TJSP",
    "TJPR",
    "TJSC",
    "TJRS",
    "TJMS",
    "TJMT",
    "TJGO",
    "TJDFT",
    # Federal Courts (TRF)
    "TRF1",
    "TRF2",
    "TRF3",
    "TRF4",
    "TRF5",
    "TRF6",
]


async def check_court(client: PJeAPIClient, tribunal: str) -> dict[str, Any]:
    """Check if a specific court API is accessible."""
    try:
        # Try to fetch data from the last 7 days
        today = datetime.now(timezone.utc).date()
        start_date = today - timedelta(days=7)

        logger.info("Checking %s...", tribunal, tribunal=tribunal)

        intimations = await client.get_intimations_by_court(
            sigla_tribunal=tribunal,
            data_disponibilizacao_inicio=start_date,
            data_disponibilizacao_fim=today,
            itens_por_pagina=1,  # We only need to check if it returns something or no error
        )

        count = len(intimations)
        logger.info("Court %s accessible", tribunal, count=count)

        result = {
            "tribunal": tribunal,
            "status": "OK",
            "count": count,
            "error": None,
        }

    except Exception as e:
        logger.warning("Court %s failed", tribunal, error=str(e))
        return {
            "tribunal": tribunal,
            "status": "ERROR",
            "count": 0,
            "error": str(e),
        }
    else:
        return result


async def validate_coverage() -> None:
    """Validate API coverage for all defined courts."""
    logger.info("Starting API coverage validation", total_courts=len(COURTS))

    client = PJeAPIClient()

    tasks = [check_court(client, court) for court in COURTS]
    results = await asyncio.gather(*tasks)

    await client.close()

    # Report results

    accessible = [r for r in results if r["status"] == "OK"]
    failed = [r for r in results if r["status"] == "ERROR"]

    for _r in sorted(accessible, key=lambda x: x["tribunal"]):
        pass

    for _r in sorted(failed, key=lambda x: x["tribunal"]):
        pass


if __name__ == "__main__":
    asyncio.run(validate_coverage())
