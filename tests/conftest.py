"""
Shared test fixtures following TDD principles
Fixtures are written as tests are written
"""

import pytest
from causaganha.api.client import PJeAPIClient
from causaganha.storage.connection import get_connection
# from causaganha.analysis.analyzer import DecisionAnalyzer

@pytest.fixture
async def api_client():
    """Provide a clean API client for tests"""
    client = PJeAPIClient()
    yield client
    await client.close()

@pytest.fixture
def db_connection():
    """Provide an in-memory database for tests"""
    # Using :memory: for DuckDB in tests
    con = get_connection(":memory:")
    yield con
    # Connection closed automatically with DuckDB, but we might want to ensure it's closed if needed
    # However, get_connection is a singleton in implementation, so we might need to handle that.
    # For now, let's assume get_connection can handle :memory: correctly.

# @pytest.fixture
# def analyzer():
#     """Provide a decision analyzer for tests"""
#     return DecisionAnalyzer(model_name="gemini-2.5-flash")

@pytest.fixture
def sample_intimation():
    """Sample intimation data for testing"""
    return {
        "id": 123456,
        "numero_processo": "0001234-56.2024.8.22.0001",
        "siglaTribunal": "TJRO",
        "data_disponibilizacao": "2024-12-01",
        "link": "https://example.com/doc.pdf",
        "hash": "abc123",
        "destinatarioadvogados": [
            {
                "advogado": {
                    "id": 1,
                    "nome": "FRANKLIN SILVEIRA BALDO",
                    "numero_oab": "5733",
                    "uf_oab": "RO"
                }
            }
        ]
    }
