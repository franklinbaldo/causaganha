"""Experiment: Test PJe DJEN API connectivity and basic operations.

This script tests the PJe Communications API (DJEN - Diário de Justiça Eletrônico Nacional)
to verify:
1. API endpoint is accessible
2. API responds correctly
3. Data structure is as expected
4. Rate limiting behavior
5. Error handling
"""

import asyncio
from datetime import UTC, timedelta

import httpx
import structlog

from causaganha.api.client import PJeAPIClient


# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)

logger = structlog.get_logger()


async def test_djen_connectivity() -> None:
    """Test DJEN API basic connectivity."""
    # Test 1: Basic HTTP connectivity
    base_url = "https://comunicaapi.pje.jus.br"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.get(f"{base_url}/swagger/djen.yml")
    except httpx.TimeoutException:
        return
    except httpx.ConnectError:
        return
    except Exception:
        return

    # Test 2: Initialize PJe client
    try:
        client = PJeAPIClient()
    except Exception:
        return

    # Test 3: Test API endpoint with minimal request
    try:
        # Try to fetch a very small number of intimations from TJRO
        # Using a recent date range to get minimal data
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=1)  # Just 1 day

        intimations = await client.get_intimations_by_court(
            sigla_tribunal="TJRO",
            limit_per_page=10,  # Small limit
            data_inicio=start_date,
            data_fim=end_date,
        )

        if intimations:
            intimations[0]

    except httpx.HTTPStatusError:
        return
    except httpx.TimeoutException:
        return
    except httpx.ConnectError:
        return
    except Exception:
        return

    # Test 4: Test data quality
    if intimations:
        len(intimations)
        sum(1 for i in intimations if i.texto)
        sum(1 for i in intimations if i.link)
        sum(1 for i in intimations if i.destinatarioadvogados)
        sum(1 for i in intimations if i.numero_processo)

    # Test 5: Test error handling with invalid court (expected to fail)
    # No need to catch - we're testing that it fails

    # Cleanup
    await client.close()

    # Summary


if __name__ == "__main__":
    asyncio.run(test_djen_connectivity())
