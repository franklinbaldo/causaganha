import tempfile
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from ibis import BaseBackend

from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.domain.models import Intimation
from causaganha.pipeline.analyze import run_analysis
from causaganha.pipeline.archive import run_archive
from causaganha.pipeline.collect import run_collection
from causaganha.pipeline.score import run_scoring
from causaganha.services.document import DocumentService
from causaganha.storage.connection import get_connection
from causaganha.storage.repository import IntimationRepository
from causaganha.storage.schema import create_schema

# Mock Data
MOCK_INTIMATION_ID = 12345
MOCK_OAB = "12345"
MOCK_STATE = "SP"
MOCK_PROCESS = "0000000-00.0000.8.26.0000"

@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """Provides a temporary DuckDB database file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.duckdb")
        yield db_path

@pytest.fixture
def db_connection(temp_db_path: str) -> BaseBackend:
    """Initializes the database schema."""
    con = get_connection(temp_db_path)
    create_schema(con)
    return con

@pytest.fixture
def repository(db_connection: BaseBackend) -> IntimationRepository:
    return IntimationRepository(db_connection)

@pytest.fixture
def mock_pje_client() -> MagicMock:
    client = MagicMock()

    # Mock response data matching api.schemas.Intimation format (which is dict-like or object)
    # The client returns Domain Models (Intimation)
    mock_intimation = Intimation(
        id=MOCK_INTIMATION_ID,
        numero_processo=MOCK_PROCESS,
        meio_completo="Diário da Justiça Eletrônico",
        data_disponibilizacao=datetime.now(timezone.utc).date(),
        texto_publicacao="Decisão de teste favorável.",
        link="http://example.com/doc.pdf",
        sigla_tribunal="TJSP",
        orgao="Vara Cível",
        # Default flags
        analyzed=False,
        needs_download=True,
        # Mandatory fields
        tipo_comunicacao="INTIMAÇÃO",
        nome_orgao="Vara Cível",
        texto="Texto da intimação",
        tipo_documento="DESPACHO",
        nome_classe="PROCEDIMENTO COMUM",
        codigo_classe="7",
        hash="mock_hash_123456",
        status="PENDING",
    )

    client.get_intimations_by_court = AsyncMock(return_value=[mock_intimation])
    client.close = AsyncMock()
    return client

@pytest.fixture
def mock_doc_service() -> MagicMock:
    service = MagicMock(spec=DocumentService)
    service.download_pdf = AsyncMock(return_value=b"%PDF-1.4 mock content")
    return service

@pytest.fixture
def mock_analyzer() -> MagicMock:
    analyzer = MagicMock()

    analysis_result = DecisionAnalysis(
        summary="Ação julgada procedente.",
        outcome=Outcome.WIN,
        winner_lawyer_oab=MOCK_OAB,
        winner_lawyer_state=MOCK_STATE,
        loser_lawyer_oab="99999",
        loser_lawyer_state="RJ",
    )

    analyzer.analyze_decision = AsyncMock(return_value=analysis_result)
    return analyzer

@pytest.fixture
def mock_archive_service() -> MagicMock:
    service = MagicMock()
    service.upload_file = AsyncMock(return_value="https://archive.org/details/mock-item")
    return service

@pytest.mark.asyncio
async def test_full_lifecycle(
    repository: IntimationRepository,
    mock_pje_client: MagicMock,
    mock_doc_service: MagicMock,
    mock_analyzer: MagicMock,
    mock_archive_service: MagicMock,
) -> None:
    """E2E Test.

    1. Collect: Fetch mock intimation from PJe Client -> DB
    2. Archive: Upload PDF to Internet Archive -> DB (ia_url)
    3. Analyze: Send PDF to Analyzer -> DB (analysis results)
    4. Score: Calculate ratings -> DB (lawyer ratings)
    """
    # --- Step 1: Collect ---
    await run_collection(
        repository,
        mock_pje_client,
        start_date="2024-01-01",
        end_date="2024-01-01",
        courts=["TJSP"],
    )

    # Verify Collection
    t_intimations = repository.con.table("intimations")
    results = t_intimations.filter(t_intimations.id == MOCK_INTIMATION_ID).execute()
    assert len(results) == 1
    assert results.iloc[0]["numero_processo"] == MOCK_PROCESS
    assert results.iloc[0]["needs_download"]

    # --- Step 2: Archive ---
    await run_archive(
        repository,
        mock_doc_service,
        mock_archive_service,
        limit=10,
        dry_run=False,
    )

    # Verify Archive
    results = t_intimations.filter(t_intimations.id == MOCK_INTIMATION_ID).execute()
    assert results.iloc[0]["ia_url"] == "https://archive.org/details/mock-item"
    # needs_download might stay True or become False depending on implementation logic,
    # but archived_at should be set.
    assert results.iloc[0]["archived_at"] is not None

    # --- Step 3: Analyze ---
    await run_analysis(
        repository,
        mock_doc_service,
        mock_analyzer,
        limit=10,
    )

    # Verify Analysis
    # Check analysis_results table
    t_analysis = repository.con.table("analysis_results")
    analysis_rows = t_analysis.filter(t_analysis.intimation_id == MOCK_INTIMATION_ID).execute()
    assert len(analysis_rows) == 1
    # Enum stored as string or whatever ibis mapping does
    assert analysis_rows.iloc[0]["outcome"] == "Outcome.WIN"

    # Check intimation update
    results = t_intimations.filter(t_intimations.id == MOCK_INTIMATION_ID).execute()
    assert results.iloc[0]["analyzed"]

    # --- Step 4: Score ---
    await run_scoring(repository, limit=100)

    # Verify Score
    t_ratings = repository.con.table("lawyer_ratings")
    ratings = t_ratings.filter(
        (t_ratings.oab_number == MOCK_OAB) &
        (t_ratings.oab_state == MOCK_STATE),
    ).execute()

    assert len(ratings) == 1
    assert ratings.iloc[0]["mu"] > 25.0 # Should have increased from default 25
    assert ratings.iloc[0]["matches"] == 1
