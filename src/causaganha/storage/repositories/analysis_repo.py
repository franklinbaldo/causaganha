import json
from typing import Any
from uuid import UUID

import structlog
from ibis import _
from ibis.backends.duckdb import Backend

from causaganha.analysis.models import DecisionAnalysis


logger = structlog.get_logger()


def store_analysis(
    con: Backend,
    intimation_id: int,
    analysis: DecisionAnalysis,
) -> None:
    """Store analysis results (supports both LLM and RAG analysis)."""
    # Determine model info based on analysis method
    if analysis.analysis_method == "rag":
        model_used = "rag-embedding-004"
        model_provider = "google"
    elif analysis.analysis_method == "hybrid":
        model_used = "hybrid-rag-llm"
        model_provider = "google"
    else:  # llm
        model_used = "gemini-2.5-flash"
        model_provider = "google"

    # Serialize rag_votes to JSON if present
    rag_votes_json = json.dumps(analysis.rag_votes) if analysis.rag_votes else None

    # Use underlying DuckDB connection for parameterized query
    con.con.execute(
        """
        INSERT INTO decision_analysis (
            intimation_id,
            winner_lawyer_oab, winner_lawyer_state, winner_party_name,
            loser_lawyer_oab, loser_lawyer_state, loser_party_name,
            decision_type, outcome, judge_name,
            decision_reasoning, confidence_score,
            analysis_method, rag_confidence, rag_votes_json,
            model_used, model_provider
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT (intimation_id) DO UPDATE SET
            winner_lawyer_oab = EXCLUDED.winner_lawyer_oab,
            winner_lawyer_state = EXCLUDED.winner_lawyer_state,
            confidence_score = EXCLUDED.confidence_score,
            analysis_method = EXCLUDED.analysis_method,
            rag_confidence = EXCLUDED.rag_confidence,
            rag_votes_json = EXCLUDED.rag_votes_json,
            model_used = EXCLUDED.model_used
        """,
        [
            intimation_id,
            analysis.winner_lawyer_oab,
            analysis.winner_lawyer_state,
            analysis.winner_party_name,
            analysis.loser_lawyer_oab,
            analysis.loser_lawyer_state,
            analysis.loser_party_name,
            analysis.decision_type,
            analysis.outcome,
            analysis.judge_name,
            analysis.decision_reasoning,
            analysis.confidence_score,
            analysis.analysis_method,
            analysis.rag_confidence,
            rag_votes_json,
            model_used,
            model_provider,
        ],
    )


def mark_as_analyzed(
    con: Backend,
    intimation_id: int,
    success: bool,
    error: str | None = None,
) -> None:
    """Mark intimation as analyzed."""
    if success:
        con.con.execute(
            """
            UPDATE intimations
            SET
                analyzed = TRUE,
                analyzed_at = NOW(),
                analysis_attempted_at = NOW(),
                analysis_error = NULL
            WHERE id = ?
            """,
            [intimation_id],
        )
    else:
        con.con.execute(
            """
            UPDATE intimations
            SET
                analyzed = FALSE,
                analyzed_at = NULL,
                analysis_attempted_at = NOW(),
                analysis_error = ?
            WHERE id = ?
            """,
            [error, intimation_id],
        )


def get_unrated_analyses(
    con: Backend,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get analyses that haven't been processed for ratings yet.

    Args:
        con: Database connection.
        limit: Max number of records to return.

    Returns:
        List of analysis records.
    """
    analysis = con.table("decision_analysis")

    result = (
        analysis.filter(_.rated == False)  # noqa: E712
        .order_by(_.created_at.asc())
        .limit(limit)
    )

    return result.to_pandas().to_dict("records")


def mark_analysis_as_rated(
    con: Backend,
    analysis_id: str | UUID,
) -> None:
    """Mark analysis as rated.

    Args:
        con: Database connection.
        analysis_id: Analysis UUID.
    """
    con.con.execute(
        """
        UPDATE decision_analysis
        SET
            rated = TRUE,
            rated_at = NOW()
        WHERE id = ?
        """,
        [str(analysis_id)],
    )
