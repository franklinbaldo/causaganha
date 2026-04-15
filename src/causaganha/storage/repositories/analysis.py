"""Analysis storage repository."""

import json
from typing import Any
from uuid import UUID

from ibis.backends.duckdb import Backend

from causaganha.analysis.models import DecisionAnalysis


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


# Outcomes that actually produce a winner/loser and therefore can update
# OpenSkill ratings. "unknown" and non-ratable outcomes are excluded so the
# rating isn't polluted by cases the classifier couldn't resolve.
RATABLE_OUTCOMES = ("procedente", "parcialmente procedente", "improcedente", "acordo")

# Decision types that we do NOT feed into the rating system. Interim orders
# (decisões interlocutórias) are procedural and rarely mark a definitive
# winner; dropping them reduces noise in the OpenSkill updates.
EXCLUDED_DECISION_TYPES = ("decisão interlocutória",)


def get_unrated_analyses(
    con: Backend,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get analyses that haven't been processed for ratings yet.

    Joins with ``intimations`` so callers can segment ratings per tribunal
    (``sigla_tribunal`` is included in the returned dicts). Also filters out
    non-ratable outcomes and interim orders upfront so the rating pipeline
    never has to re-check those conditions.

    Args:
        con: Database connection.
        limit: Max number of records to return.

    Returns:
        List of analysis records, each augmented with ``sigla_tribunal``.
    """
    analysis = con.table("decision_analysis")
    intimations = con.table("intimations")

    joined = analysis.join(
        intimations,
        analysis.intimation_id == intimations.id,
    )

    result = (
        joined.filter(~analysis.rated)
        .filter(analysis.outcome.isin(RATABLE_OUTCOMES))
        .filter(analysis.decision_type.notin(EXCLUDED_DECISION_TYPES))
        .select(
            id=analysis.id,
            intimation_id=analysis.intimation_id,
            winner_lawyer_oab=analysis.winner_lawyer_oab,
            winner_lawyer_state=analysis.winner_lawyer_state,
            loser_lawyer_oab=analysis.loser_lawyer_oab,
            loser_lawyer_state=analysis.loser_lawyer_state,
            decision_type=analysis.decision_type,
            outcome=analysis.outcome,
            confidence_score=analysis.confidence_score,
            created_at=analysis.created_at,
            sigla_tribunal=intimations.sigla_tribunal,
        )
        .order_by(analysis.created_at.asc())
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
