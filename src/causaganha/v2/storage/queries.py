"""Common analytical queries using Ibis."""

from typing import Any
from uuid import UUID

import structlog
from ibis import _
from ibis.backends.duckdb import Backend

from causaganha.v2.analysis.models import DecisionAnalysis
from causaganha.v2.api.client import Intimation, DestinarioAdvogado


logger = structlog.get_logger()


def store_intimations(
    con: Backend,
    intimations: list[Intimation],
) -> int:
    """Store intimations in database.

    Returns count of new records inserted.
    """
    if not intimations:
        return 0

    inserted = 0
    for item in intimations:
        try:
            # We access the underlying DuckDB connection to use parameterized queries
            # con.con is the DuckDBPyConnection
            con.con.execute(
                """
                INSERT INTO intimations (
                    id, numero_processo, numeroprocessocommascara,
                    data_disponibilizacao, sigla_tribunal, id_orgao,
                    tipo_comunicacao, nome_orgao, texto, link,
                    tipo_documento, nome_classe, codigo_classe,
                    hash, status, analyzed
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE
                )
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = NOW(),
                    texto = EXCLUDED.texto,
                    status = EXCLUDED.status,
                    link = EXCLUDED.link
            """,
                [
                    item.id,
                    item.numero_processo,
                    item.numero_processo,  # numeroprocessocommascara fallback
                    item.data_disponibilizacao,
                    item.sigla_tribunal,
                    item.id_orgao,
                    item.tipo_comunicacao,
                    item.nome_orgao,
                    item.texto,
                    item.link,
                    item.tipo_documento,
                    item.nome_classe,
                    item.codigo_classe,
                    item.hash,
                    item.status,
                ],
            )
            inserted += 1
        except Exception as e:
            logger.warning(
                "insert_failed",
                intimation_id=item.id,
                error=str(e),
            )

    logger.info("intimations_stored", inserted=inserted, total=len(intimations))
    return inserted


def store_lawyer_associations(
    con: Backend,
    intimation_id: int,
    lawyers: list[DestinarioAdvogado],
) -> int:
    """Store lawyer associations for an intimation."""
    inserted = 0
    for lawyer_data in lawyers:
        advogado = lawyer_data.advogado

        try:
            con.con.execute(
                """
                INSERT INTO intimation_lawyers (
                    intimation_id, oab_number, oab_state, lawyer_name
                ) VALUES (
                    ?, ?, ?, ?
                )
                ON CONFLICT DO NOTHING
                """,
                [
                    intimation_id,
                    advogado.numero_oab,
                    advogado.uf_oab,
                    advogado.nome,
                ],
            )
            inserted += 1
        except Exception as e:
            logger.warning(
                "lawyer_association_failed",
                intimation_id=intimation_id,
                error=str(e),
            )

    return inserted


def get_unanalyzed_intimations(
    con: Backend,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get intimations that need PDF analysis."""
    intimations = con.table("intimations")

    result = (
        intimations.filter(_.analyzed == False)  # noqa: E712
        .filter(_.link.notnull())
        .order_by(_.data_disponibilizacao.desc())
        .limit(limit)
    )

    return result.to_pandas().to_dict("records")


def store_analysis(
    con: Backend,
    intimation_id: int,
    analysis: DecisionAnalysis,
) -> None:
    """Store analysis results (supports both LLM and RAG analysis)."""
    import json

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
        analysis
        .filter(_.rated == False)  # noqa: E712
        .order_by(_.created_at.asc())
        .limit(limit)
    )

    return result.to_pandas().to_dict("records")


def get_lawyer_rating(
    con: Backend,
    oab_number: str,
    oab_state: str,
    tribunal: str = "GLOBAL",
) -> dict[str, Any] | None:
    """Get current rating for a lawyer.

    Args:
        con: Database connection.
        oab_number: Lawyer OAB.
        oab_state: Lawyer OAB state.
        tribunal: Optional tribunal code.

    Returns:
        Dictionary with rating info or None if not found.
    """
    ratings = con.table("lawyer_ratings")

    query = (
        ratings
        .filter(_.oab_number == oab_number)
        .filter(_.oab_state == oab_state)
        .filter(_.tribunal == tribunal)
    )

    result = query.to_pandas()

    if result.empty:
        return None

    return result.iloc[0].to_dict()


def update_lawyer_rating(
    con: Backend,
    oab_number: str,
    oab_state: str,
    lawyer_name: str | None,
    mu: float,
    sigma: float,
    wins: int,
    losses: int,
    tribunal: str = "GLOBAL",
) -> None:
    """Update or insert lawyer rating.

    Args:
        con: Database connection.
        oab_number: Lawyer OAB.
        oab_state: Lawyer OAB state.
        lawyer_name: Lawyer name.
        mu: OpenSkill mu.
        sigma: OpenSkill sigma.
        wins: Total wins.
        losses: Total losses.
        tribunal: Optional tribunal code.
    """
    total_cases = wins + losses
    rating = mu - 3 * sigma
    win_rate = (float(wins) / total_cases) if total_cases > 0 else 0.0

    # We use parameter substitution. 'GLOBAL' is default in Python arg,
    # but we should pass it explicitly if None to match schema default logic if needed,
    # or rely on the function caller passing the default.
    # Since we declare it as default arg "GLOBAL", it won't be None unless explicitly passed as None.

    con.con.execute(
        """
        INSERT INTO lawyer_ratings (
            oab_number, oab_state, lawyer_name,
            mu, sigma,
            rating, win_rate,
            total_cases, wins, losses,
            tribunal,
            last_updated
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW()
        )
        ON CONFLICT (oab_number, oab_state, tribunal) DO UPDATE SET
            mu = EXCLUDED.mu,
            sigma = EXCLUDED.sigma,
            rating = EXCLUDED.rating,
            win_rate = EXCLUDED.win_rate,
            total_cases = EXCLUDED.total_cases,
            wins = EXCLUDED.wins,
            losses = EXCLUDED.losses,
            last_updated = NOW()
        """,
        [
            oab_number,
            oab_state,
            lawyer_name,
            mu,
            sigma,
            rating,
            win_rate,
            total_cases,
            wins,
            losses,
            tribunal
        ]
    )


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
        [str(analysis_id)]
    )


def get_lawyer_name(
    con: Backend,
    oab_number: str,
    oab_state: str,
) -> str | None:
    """Get lawyer name from stored associations.

    Args:
        con: Database connection.
        oab_number: Lawyer OAB.
        oab_state: Lawyer OAB state.

    Returns:
        Lawyer name or None.
    """
    lawyers = con.table("intimation_lawyers")
    result = (
        lawyers
        .filter(_.oab_number == oab_number)
        .filter(_.oab_state == oab_state)
        .limit(1)
        .select(_.lawyer_name)
        .to_pandas()
    )
    if result.empty:
        return None
    return result.iloc[0]["lawyer_name"]


def get_unarchived_intimations(
    con: Backend,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get intimations that have not been uploaded to IA.

    Args:
        con: Database connection.
        limit: Max number of records to return.

    Returns:
        List of intimation records.
    """
    intimations = con.table("intimations")

    result = (
        intimations
        .filter(_.ia_url.isnull())
        .filter(_.link.notnull())
        .order_by(_.data_disponibilizacao.desc())
        .limit(limit)
    )

    return result.to_pandas().to_dict("records")


def mark_as_archived(
    con: Backend,
    intimation_id: int | str,
    ia_url: str,
) -> None:
    """Mark intimation as archived with IA URL.

    Args:
        con: Database connection.
        intimation_id: Intimation ID.
        ia_url: Internet Archive URL.
    """
    con.con.execute(
        """
        UPDATE intimations
        SET
            ia_url = ?
        WHERE id = ?
        """,
        [ia_url, intimation_id]
    )
