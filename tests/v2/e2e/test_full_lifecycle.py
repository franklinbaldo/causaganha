"""End-to-end lifecycle test for V2."""

from unittest.mock import AsyncMock, patch

import pytest
from ibis.backends.duckdb import Backend

from causaganha.v2.analysis.models import DecisionAnalysis
from causaganha.v2.pipeline.analyze import analyze_pending_decisions
from causaganha.v2.pipeline.archive import archive_documents
from causaganha.v2.pipeline.score import calculate_ratings


@pytest.mark.asyncio
async def test_full_lifecycle(
    db_connection: Backend,
) -> None:
    """Test the full lifecycle: Collect -> Archive -> Analyze -> Score.

    Simulates collection by inserting directly into DB.
    Mocks external services (Archive, LLM).
    Verifies DB state at each step.
    """

    # -------------------------------------------------------------------------
    # 1. Simulate Collection
    # -------------------------------------------------------------------------

    # Insert Intimation
    db_connection.con.execute(
        """
        INSERT INTO intimations (
            id, numero_processo, numeroprocessocommascara,
            data_disponibilizacao, sigla_tribunal, id_orgao,
            tipo_comunicacao, nome_orgao, texto, link,
            tipo_documento, nome_classe, codigo_classe,
            hash, status, analyzed
        ) VALUES (
            1, '1111111-11.2024.8.22.0001', '1111111-11.2024.8.22.0001',
            '2024-01-01', 'TJRO', 1,
            'Intimação', 'Vara 1', 'Texto da decisão...', 'http://example.com/doc.pdf',
            'Decisão', 'Procedimento', 1,
            'hash123', 'NEW', FALSE
        )
        """
    )

    # Insert Lawyer Associations (Lawyer A and Lawyer B)
    # Lawyer A: OAB 12345/RO (Will be winner)
    # Lawyer B: OAB 67890/RO (Will be loser)
    db_connection.con.execute(
        """
        INSERT INTO intimation_lawyers (
            intimation_id, oab_number, oab_state, lawyer_name
        ) VALUES
        (1, '12345', 'RO', 'Lawyer A'),
        (1, '67890', 'RO', 'Lawyer B')
        """
    )

    # -------------------------------------------------------------------------
    # 2. Archive Pipeline
    # -------------------------------------------------------------------------

    with patch("causaganha.v2.pipeline.archive.PreservationService") as mock_preservation_cls:
        preservation_instance = mock_preservation_cls.return_value
        preservation_instance.preserve_document = AsyncMock(
            return_value="https://archive.org/details/causaganha-tjro-1"
        )

        # We need mock services to pass to archive_documents, even if unused by PreservationService mock
        mock_doc_service = AsyncMock()
        mock_archive_service = AsyncMock()
        mock_archive_service.generate_metadata.return_value = {}

        await archive_documents(mock_doc_service, mock_archive_service, limit=10)

    # Verify DB updated with IA URL
    row = db_connection.table("intimations").filter(db_connection.table("intimations").id == 1).execute().iloc[0]
    assert row["ia_url"] == "https://archive.org/details/causaganha-tjro-1"

    # -------------------------------------------------------------------------
    # 3. Analyze Pipeline
    # -------------------------------------------------------------------------

    mock_analysis_result = DecisionAnalysis(
        winner_lawyer_oab="12345",
        winner_lawyer_state="RO",
        winner_party_name="Party A",
        loser_lawyer_oab="67890",
        loser_lawyer_state="RO",
        loser_party_name="Party B",
        decision_type="sentença",
        outcome="procedente",  # Implies winner won
        judge_name="Judge Dredd",
        decision_reasoning="Reasoning...",
        confidence_score=0.95,
        analysis_method="llm"
    )

    # Patch DecisionAnalyzer for 'llm' strategy
    with patch("causaganha.v2.pipeline.analyze.DecisionAnalyzer") as mock_analyzer_cls:
        analyzer_instance = mock_analyzer_cls.return_value
        analyzer_instance.analyze_batch = AsyncMock(return_value=[mock_analysis_result])

        # Use strategy='llm' to ensure DecisionAnalyzer is used
        await analyze_pending_decisions(strategy="llm", batch_size=10)

    # Verify decision_analysis table
    da_table = db_connection.table("decision_analysis")
    assert da_table.count().execute() == 1

    analysis_row = da_table.execute().iloc[0]
    assert analysis_row["winner_lawyer_oab"] == "12345"
    assert analysis_row["intimation_id"] == 1
    assert not analysis_row["rated"] # Should be False initially

    # Verify intimation marked as analyzed
    row = db_connection.table("intimations").filter(db_connection.table("intimations").id == 1).execute().iloc[0]
    assert bool(row["analyzed"]) is True

    # -------------------------------------------------------------------------
    # 4. Score Pipeline
    # -------------------------------------------------------------------------

    await calculate_ratings(batch_size=10)

    # Verify lawyer_ratings
    ratings_table = db_connection.table("lawyer_ratings")
    assert ratings_table.count().execute() == 2 # A and B

    ratings_df = ratings_table.execute()

    # Lawyer A (Winner)
    lawyer_a = ratings_df[
        (ratings_df["oab_number"] == "12345") &
        (ratings_df["oab_state"] == "RO")
    ].iloc[0]

    assert lawyer_a["wins"] == 1
    assert lawyer_a["losses"] == 0
    assert lawyer_a["total_cases"] == 1
    assert lawyer_a["mu"] > 25.0 # Should increase from default 25

    # Lawyer B (Loser)
    lawyer_b = ratings_df[
        (ratings_df["oab_number"] == "67890") &
        (ratings_df["oab_state"] == "RO")
    ].iloc[0]

    assert lawyer_b["wins"] == 0
    assert lawyer_b["losses"] == 1
    assert lawyer_b["total_cases"] == 1
    assert lawyer_b["mu"] < 25.0 # Should decrease

    # Verify analysis marked as rated
    analysis_row = da_table.execute().iloc[0]
    assert bool(analysis_row["rated"]) is True
