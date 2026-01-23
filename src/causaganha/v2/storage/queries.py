"""Common analytical queries using Ibis."""

import ibis
from ibis import _
from datetime import date, timedelta
from typing import Optional, List, Dict, Any
import structlog
from ..api.models import Intimation, DestinarioAdvogado
from ..analysis.models import DecisionAnalysis

logger = structlog.get_logger()

def get_unanalyzed_intimations(
    con: ibis.backends.duckdb.Backend,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get intimations that need PDF analysis."""

    intimations = con.table('intimations')

    result = (
        intimations
        .filter(_.analyzed == False)
        .filter(_.link.notnull())
        .order_by(_.data_disponibilizacao.desc())
        .limit(limit)
    )

    return result.to_pandas().to_dict('records')

def store_intimations(
    con: ibis.backends.duckdb.Backend,
    intimations: List[Intimation]
) -> int:
    """
    Store intimations in database.

    Returns count of new records inserted/updated.
    """
    if not intimations:
        return 0

    inserted = 0
    # Use DuckDB connection directly for parameterized queries
    cursor = con.con.cursor()

    for item in intimations:
        try:
            link_val = item.link if item.link else None

            cursor.execute("""
                INSERT INTO intimations (
                    id, numero_processo, numeroprocessocommascara,
                    data_disponibilizacao, sigla_tribunal, id_orgao,
                    tipo_comunicacao, nome_orgao, texto, link,
                    tipo_documento, nome_classe, codigo_classe,
                    hash, status, analyzed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)
                ON CONFLICT (id) DO UPDATE SET
                    texto = EXCLUDED.texto,
                    status = EXCLUDED.status,
                    updated_at = now()
            """, (
                item.id,
                item.numero_processo,
                item.numeroprocessocommascara or '',
                item.data_disponibilizacao,
                item.siglaTribunal,
                item.idOrgao,
                item.tipoComunicacao,
                item.nomeOrgao,
                item.texto,
                link_val,
                item.tipoDocumento,
                item.nomeClasse,
                item.codigoClasse or '',
                item.hash,
                item.status
            ))
            inserted += 1
        except Exception as e:
            logger.warning("insert_failed",
                          intimation_id=item.id,
                          error=str(e))

    return inserted

def store_lawyer_associations(
    con: ibis.backends.duckdb.Backend,
    intimation_id: int,
    lawyers: List[DestinarioAdvogado]
) -> int:
    """Store lawyer associations for an intimation."""

    inserted = 0
    cursor = con.con.cursor()

    for lawyer_data in lawyers:
        advogado = lawyer_data.advogado

        try:
            cursor.execute("""
                INSERT INTO intimation_lawyers (
                    intimation_id, oab_number, oab_state, lawyer_name
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT DO NOTHING
            """, (
                intimation_id,
                advogado.numero_oab,
                advogado.uf_oab,
                advogado.nome
            ))
            inserted += 1
        except Exception as e:
            logger.warning("lawyer_association_failed",
                          intimation_id=intimation_id,
                          error=str(e))

    return inserted

def store_analysis(
    con: ibis.backends.duckdb.Backend,
    intimation_id: int,
    analysis: DecisionAnalysis
) -> None:
    """Store analysis results."""
    cursor = con.con.cursor()

    cursor.execute("""
        INSERT INTO decision_analysis (
            intimation_id,
            winner_lawyer_oab, winner_lawyer_state, winner_party_name,
            loser_lawyer_oab, loser_lawyer_state, loser_party_name,
            decision_type, outcome, judge_name,
            decision_reasoning, confidence_score,
            model_used, model_provider
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (intimation_id) DO UPDATE SET
            winner_lawyer_oab = EXCLUDED.winner_lawyer_oab,
            winner_lawyer_state = EXCLUDED.winner_lawyer_state,
            confidence_score = EXCLUDED.confidence_score,
            outcome = EXCLUDED.outcome
    """, (
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
        'gemini-2.5-flash',
        'google'
    ))

def mark_as_analyzed(
    con: ibis.backends.duckdb.Backend,
    intimation_id: int,
    success: bool,
    error: str = None
) -> None:
    """Mark intimation as analyzed."""
    cursor = con.con.cursor()

    analyzed_val = str(success).upper()

    # Using parameterized query for error message and timestamp logic is tricky with SQL string building.
    # But we can parameterize the error.

    # We construct the UPDATE statement.
    # analyzed_at = now() if success else NULL
    # analyzed is TRUE/FALSE (boolean literal in DuckDB or 1/0)

    # DuckDB accepts boolean parameters.

    if success:
        sql = """
            UPDATE intimations
            SET
                analyzed = ?,
                analyzed_at = now(),
                analysis_attempted_at = now(),
                analysis_error = ?
            WHERE id = ?
        """
        cursor.execute(sql, (success, error, intimation_id))
    else:
        sql = """
            UPDATE intimations
            SET
                analyzed = ?,
                analyzed_at = NULL,
                analysis_attempted_at = now(),
                analysis_error = ?
            WHERE id = ?
        """
        cursor.execute(sql, (success, error, intimation_id))


def get_unrated_analyses(
    con: ibis.backends.duckdb.Backend
) -> List[Dict[str, Any]]:
    """Get analyses that haven't been rated yet."""

    analysis = con.table('decision_analysis')

    result = (
        analysis
        .filter(_.rated == False)
    )

    return result.to_pandas().to_dict('records')

def update_lawyer_rating(
    con: ibis.backends.duckdb.Backend,
    oab_number: str,
    oab_state: str,
    lawyer_name: str,
    mu: float,
    sigma: float,
    wins: int,
    losses: int,
    tribunal: str = 'GLOBAL'
) -> None:
    """Update lawyer rating."""
    cursor = con.con.cursor()

    cursor.execute("""
        INSERT INTO lawyer_ratings (
            oab_number, oab_state, lawyer_name,
            mu, sigma, wins, losses, tribunal,
            total_cases
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (oab_number, oab_state, tribunal) DO UPDATE SET
            mu = EXCLUDED.mu,
            sigma = EXCLUDED.sigma,
            wins = EXCLUDED.wins,
            losses = EXCLUDED.losses,
            total_cases = EXCLUDED.total_cases,
            last_updated = now()
    """, (
        oab_number,
        oab_state,
        lawyer_name,
        mu,
        sigma,
        wins,
        losses,
        tribunal,
        wins + losses
    ))

def get_lawyer_rating(
    con: ibis.backends.duckdb.Backend,
    oab_number: str,
    oab_state: str,
    tribunal: str = 'GLOBAL'
) -> Optional[Dict[str, Any]]:
    """Get current rating for a lawyer."""
    ratings = con.table('lawyer_ratings')

    result = (
        ratings
        .filter(_.oab_number == oab_number)
        .filter(_.oab_state == oab_state)
        .filter(_.tribunal == tribunal)
    ).to_pandas().to_dict('records')

    if result:
        return result[0]
    return None

def mark_analysis_as_rated(
    con: ibis.backends.duckdb.Backend,
    analysis_id: str
) -> None:
    """Mark analysis as rated."""
    # Assuming analysis_id is UUID string
    # Using parameterized query
    cursor = con.con.cursor()
    cursor.execute("""
        UPDATE decision_analysis
        SET rated = TRUE
        WHERE id = ?
    """, (analysis_id,))

def get_lawyer_name(
    con: ibis.backends.duckdb.Backend,
    oab_number: str,
    oab_state: str
) -> Optional[str]:
    """Get lawyer name from stored associations."""
    # Try to find from intimation_lawyers first as it's the source of truth for names
    lawyers = con.table('intimation_lawyers')

    result = (
        lawyers
        .filter(_.oab_number == oab_number)
        .filter(_.oab_state == oab_state)
        .limit(1)
    ).to_pandas().to_dict('records')

    if result:
        return result[0]['lawyer_name']

    # Fallback to ratings table
    ratings = con.table('lawyer_ratings')
    result = (
        ratings
        .filter(_.oab_number == oab_number)
        .filter(_.oab_state == oab_state)
        .limit(1)
    ).to_pandas().to_dict('records')

    if result:
        return result[0]['lawyer_name']

    return None

def get_unarchived_intimations(
    con: ibis.backends.duckdb.Backend,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get intimations that haven't been archived."""
    intimations = con.table('intimations')

    result = (
        intimations
        .filter(_.ia_url.isnull())
        .filter(_.link.notnull())
        .limit(limit)
    )

    return result.to_pandas().to_dict('records')

def mark_as_archived(
    con: ibis.backends.duckdb.Backend,
    intimation_id: int,
    ia_url: str
) -> None:
    """Mark intimation as archived."""
    cursor = con.con.cursor()
    cursor.execute("""
        UPDATE intimations
        SET ia_url = ?
        WHERE id = ?
    """, (ia_url, intimation_id))
