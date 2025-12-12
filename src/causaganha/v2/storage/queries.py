"""Common analytical queries using Ibis"""

import ibis
from ibis import _
from datetime import date, timedelta
import structlog

logger = structlog.get_logger()

def get_unanalyzed_intimations(
    con: ibis.BaseBackend,
    limit: int = 100
) -> list:
    """Get intimations that need PDF analysis"""

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
    con: ibis.BaseBackend,
    intimations: list
) -> int:
    """
    Store intimations in database

    Returns count of new records inserted
    """
    if not intimations:
        return 0

    # Use native DuckDB connection for parameterized queries
    if hasattr(con, 'con'):
        duck_con = con.con
    else:
        logger.error("backend_not_duckdb", backend=type(con))
        return 0

    inserted = 0
    sql = """
        INSERT INTO intimations (
            id, numero_processo, numeroprocessocommascara,
            data_disponibilizacao, sigla_tribunal, id_orgao,
            tipo_comunicacao, nome_orgao, texto, link,
            tipo_documento, nome_classe, codigo_classe,
            hash, status, analyzed
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (id) DO UPDATE SET
            updated_at = now()
    """

    for item in intimations:
        # Prepare values
        params = (
            item.id,
            item.numero_processo,
            item.numeroprocessocommascara or '',
            item.data_disponibilizacao,
            item.siglaTribunal,
            item.idOrgao, # DuckDB handles None as NULL
            item.tipoComunicacao,
            item.nomeOrgao,
            item.texto,
            item.link,
            item.tipoDocumento,
            item.nomeClasse,
            item.codigoClasse or '',
            item.hash,
            item.status,
            False
        )

        try:
            duck_con.execute(sql, params)
            inserted += 1
        except Exception as e:
            logger.warning("insert_failed",
                          intimation_id=item.id,
                          error=str(e))

    logger.info("intimations_stored", inserted=inserted, total=len(intimations))
    return inserted

def store_lawyer_associations(
    con: ibis.BaseBackend,
    intimation_id: int,
    lawyers: list
) -> int:
    """Store lawyer associations for an intimation"""

    if hasattr(con, 'con'):
        duck_con = con.con
    else:
        return 0

    inserted = 0
    sql = """
        INSERT INTO intimation_lawyers (
            intimation_id, oab_number, oab_state, lawyer_name
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT DO NOTHING
    """

    for lawyer_wrapper in lawyers:
        advogado = lawyer_wrapper.advogado

        params = (
            intimation_id,
            advogado.numero_oab,
            advogado.uf_oab,
            advogado.nome
        )

        try:
            duck_con.execute(sql, params)
            inserted += 1
        except Exception as e:
            logger.warning("lawyer_association_failed",
                          intimation_id=intimation_id,
                          error=str(e))

    return inserted

def get_recent_analyses(
    con: ibis.BaseBackend,
    days: int = 7
) -> list:
    """Get recent decision analyses"""

    analysis = con.table('decision_analysis')

    cutoff = date.today() - timedelta(days=days)

    result = (
        analysis
        .filter(_.created_at >= cutoff)
        .order_by(_.created_at.desc())
    )

    return result.to_pandas().to_dict('records')

def get_lawyer_stats(
    con: ibis.BaseBackend,
    oab_number: str,
    oab_state: str
) -> dict:
    """Get statistics for a specific lawyer"""

    analysis = con.table('decision_analysis')

    # Wins
    wins = (
        analysis
        .filter(_.winner_lawyer_oab == oab_number)
        .filter(_.winner_lawyer_state == oab_state)
        .count()
        .execute()
    )

    # Losses
    losses = (
        analysis
        .filter(_.loser_lawyer_oab == oab_number)
        .filter(_.loser_lawyer_state == oab_state)
        .count()
        .execute()
    )

    return {
        'oab_number': oab_number,
        'oab_state': oab_state,
        'wins': wins,
        'losses': losses,
        'total': wins + losses,
        'win_rate': wins / (wins + losses) if (wins + losses) > 0 else 0
    }
