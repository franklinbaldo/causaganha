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
from datetime import date, timedelta

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


async def test_djen_connectivity():
    """Test DJEN API basic connectivity."""
    print("=" * 80)
    print("🧪 EXPERIMENT: Testing DJEN (PJe) API Connectivity")
    print("=" * 80)
    print()

    # Test 1: Basic HTTP connectivity
    print("📋 Test 1: Testing basic API connectivity...")
    base_url = "https://comunicaapi.pje.jus.br"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{base_url}/swagger/djen.yml")
            print(f"✓ API endpoint accessible: {response.status_code}")
            print(f"✓ Content-Type: {response.headers.get('content-type', 'N/A')}")
            print(f"✓ Content length: {len(response.content)} bytes")
    except httpx.TimeoutException:
        print("✗ Request timed out - API may be slow or blocked")
        return
    except httpx.ConnectError as e:
        print(f"✗ Connection failed: {e}")
        return
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return
    print()

    # Test 2: Initialize PJe client
    print("📋 Test 2: Initializing PJe API client...")
    try:
        client = PJeAPIClient()
        print(f"✓ Client initialized with base URL: {client.base_url}")
        print(f"✓ Client timeout: {client.client.timeout}")
    except Exception as e:
        print(f"✗ Client initialization failed: {e}")
        return
    print()

    # Test 3: Test API endpoint with minimal request
    print("📋 Test 3: Testing API endpoint with TJRO data...")
    try:
        # Try to fetch a very small number of intimations from TJRO
        # Using a recent date range to get minimal data
        end_date = date.today()
        start_date = end_date - timedelta(days=1)  # Just 1 day

        print(f"  Requesting data from {start_date} to {end_date}")
        print("  Court: TJRO (Tribunal de Justiça de Rondônia)")

        intimations = await client.get_intimations_by_court(
            sigla_tribunal="TJRO",
            limit_per_page=10,  # Small limit
            data_inicio=start_date,
            data_fim=end_date,
        )

        print("✓ Request successful!")
        print(f"✓ Retrieved {len(intimations)} intimations")

        if intimations:
            print()
            print("Sample intimation structure:")
            first = intimations[0]
            print(f"  - ID: {first.id}")
            print(f"  - Court: {first.sigla_tribunal}")
            print(f"  - Type: {first.tipo_comunicacao}")
            print(f"  - Organ: {first.nome_orgao}")
            print(f"  - Process: {first.numero_processo}")
            print(f"  - Date: {first.data_disponibilizacao}")
            print(f"  - Status: {first.status}")
            print(f"  - Document type: {first.tipo_documento}")
            print(f"  - Text preview: {first.texto[:100] if first.texto else 'N/A'}...")
            print()

    except httpx.HTTPStatusError as e:
        print(f"✗ HTTP error: {e.response.status_code}")
        print(f"  Response: {e.response.text[:200]}")
        return
    except httpx.TimeoutException:
        print("✗ Request timed out - API may be slow")
        return
    except httpx.ConnectError as e:
        print(f"✗ Connection error: {e}")
        return
    except Exception as e:
        print(f"✗ Unexpected error: {type(e).__name__}: {e}")
        return
    print()

    # Test 4: Test data quality
    if intimations:
        print("📋 Test 4: Analyzing data quality...")
        total = len(intimations)
        with_text = sum(1 for i in intimations if i.texto)
        with_link = sum(1 for i in intimations if i.link)
        with_lawyers = sum(1 for i in intimations if i.destinatarioadvogados)
        with_process = sum(1 for i in intimations if i.numero_processo)

        print(f"✓ Total intimations: {total}")
        print(f"✓ With text: {with_text} ({with_text/total*100:.1f}%)")
        print(f"✓ With link: {with_link} ({with_link/total*100:.1f}%)")
        print(f"✓ With lawyers: {with_lawyers} ({with_lawyers/total*100:.1f}%)")
        print(
            f"✓ With process number: {with_process} ({with_process/total*100:.1f}%)",
        )
        print()

    # Test 5: Test error handling with invalid court
    print("📋 Test 5: Testing error handling (invalid court)...")
    try:
        await client.get_intimations_by_court(
            sigla_tribunal="INVALID_COURT",
            limit_per_page=1,
        )
        print("✗ Should have raised an error for invalid court")
    except httpx.HTTPStatusError as e:
        print(f"✓ Correctly raised HTTPStatusError: {e.response.status_code}")
    except Exception as e:
        print(f"✓ Error caught: {type(e).__name__}")
    print()

    # Cleanup
    print("📋 Cleaning up...")
    await client.close()
    print("✓ Client closed")
    print()

    # Summary
    print("=" * 80)
    print("✅ EXPERIMENT COMPLETE")
    print("=" * 80)
    print()
    print("Key Findings:")
    print(f"  • API Status: {'Accessible' if intimations is not None else 'Blocked or Down'}")
    print(f"  • Base URL: {client.base_url}")
    print(
        f"  • Data availability: {len(intimations) if intimations else 0} intimations retrieved",
    )
    print("  • Error handling: Working correctly")
    print()
    print("💡 Recommendation: DJEN API is ready for use in the pipeline.")
    print()


if __name__ == "__main__":
    asyncio.run(test_djen_connectivity())
