"""Common analytical queries using Ibis"""

from datetime import date, timedelta
from typing import Any, Dict, List

import ibis
import structlog

from ..api.models import DestinatarioAdvogado, Intimation

logger = structlog.get_logger()


def store_intimations(con: ibis.BaseBackend, intimations: List[Intimation]) -> int:
    """
    Store intimations in database

    Returns count of new records inserted
    """
    if not intimations:
        return 0

    # Try bulk insert via underlying connection
    if hasattr(con, "con"):
        try:
            data = []
            for item in intimations:
                data.append((
                    item.id,
                    item.numero_processo,
                    item.numeroprocessocommascara,
                    item.data_disponibilizacao,
                    item.siglaTribunal,
                    item.idOrgao,
                    item.tipoComunicacao,
                    item.nomeOrgao,
                    item.texto,
                    item.link,
                    item.tipoDocumento,
                    item.nomeClasse,
                    item.codigoClasse,
                    item.hash,
                    item.status,
                ))

            # Use now() instead of CURRENT_TIMESTAMP
            sql = """
                INSERT INTO intimations (
                    id, numero_processo, numeroprocessocommascara,
                    data_disponibilizacao, sigla_tribunal, id_orgao,
                    tipo_comunicacao, nome_orgao, texto, link,
                    tipo_documento, nome_classe, codigo_classe,
                    hash, status, analyzed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = now()
            """

            con.con.executemany(sql, data)
            logger.info("intimations_stored_bulk", count=len(data))
            return len(data)

        except Exception as e:
            logger.warning("bulk_insert_failed_fallback_to_row", error=str(e))

    return _store_intimations_row_by_row(con, intimations)


def _store_intimations_row_by_row(
    con: ibis.BaseBackend, intimations: List[Intimation]
) -> int:
    # Prepare records
    inserted = 0
    for item in intimations:
        try:
            # Escape strings for SQL
            def escape(s):
                if s is None:
                    return "NULL"
                return "'" + str(s).replace("'", "''") + "'"

            # Use now() instead of CURRENT_TIMESTAMP per memory guidelines
            sql = f"""
                INSERT INTO intimations (
                    id, numero_processo, numeroprocessocommascara,
                    data_disponibilizacao, sigla_tribunal, id_orgao,
                    tipo_comunicacao, nome_orgao, texto, link,
                    tipo_documento, nome_classe, codigo_classe,
                    hash, status, analyzed
                ) VALUES (
                    {item.id},
                    {escape(item.numero_processo)},
                    {escape(item.numeroprocessocommascara)},
                    {escape(item.data_disponibilizacao)},
                    {escape(item.siglaTribunal)},
                    {item.idOrgao or "NULL"},
                    {escape(item.tipoComunicacao)},
                    {escape(item.nomeOrgao)},
                    {escape(item.texto)},
                    {escape(item.link)},
                    {escape(item.tipoDocumento)},
                    {escape(item.nomeClasse)},
                    {escape(item.codigoClasse)},
                    {escape(item.hash)},
                    {escape(item.status)},
                    FALSE
                )
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = now()
            """

            con.raw_sql(sql)
            inserted += 1
        except Exception as e:
            logger.warning("insert_failed", intimation_id=item.id, error=str(e))

    logger.info("intimations_stored", inserted=inserted, total=len(intimations))
    return inserted


def store_lawyer_associations(
    con: ibis.BaseBackend, intimation_id: int, lawyers: List[DestinatarioAdvogado]
) -> int:
    """Store lawyer associations for an intimation"""

    if not lawyers:
        return 0

    if hasattr(con, "con"):
        try:
            data = []
            for lawyer_data in lawyers:
                advogado = lawyer_data.advogado
                data.append((
                    intimation_id,
                    advogado.numero_oab,
                    advogado.uf_oab,
                    advogado.nome,
                ))

            sql = """
                INSERT INTO intimation_lawyers (
                    intimation_id, oab_number, oab_state, lawyer_name
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT DO NOTHING
            """

            con.con.executemany(sql, data)
            return len(data)
        except Exception as e:
            logger.warning("bulk_association_failed_fallback", error=str(e))

    return _store_lawyer_associations_row_by_row(con, intimation_id, lawyers)


def _store_lawyer_associations_row_by_row(
    con: ibis.BaseBackend, intimation_id: int, lawyers: List[DestinatarioAdvogado]
) -> int:
    inserted = 0
    for lawyer_data in lawyers:
        advogado = lawyer_data.advogado

        try:
            sql = f"""
                INSERT INTO intimation_lawyers (
                    intimation_id, oab_number, oab_state, lawyer_name
                ) VALUES (
                    {intimation_id},
                    '{advogado.numero_oab}',
                    '{advogado.uf_oab}',
                    '{advogado.nome.replace("'", "''")}'
                )
                ON CONFLICT DO NOTHING
            """
            con.raw_sql(sql)
            inserted += 1
        except Exception as e:
            logger.warning(
                "lawyer_association_failed", intimation_id=intimation_id, error=str(e)
            )

    return inserted


def get_unanalyzed_intimations(
    con: ibis.BaseBackend, limit: int = 100
) -> List[Dict[str, Any]]:
    """Get intimations that need PDF analysis"""

    intimations = con.table("intimations")

    result = (
        intimations.filter(intimations.analyzed == False)
        .filter(intimations.link.notnull())
        .order_by(intimations.data_disponibilizacao.desc())
        .limit(limit)
    )

    return result.to_pandas().to_dict("records")


def get_recent_analyses(con: ibis.BaseBackend, days: int = 7) -> List[Dict[str, Any]]:
    """Get recent decision analyses"""

    analysis = con.table("decision_analysis")

    result = analysis.order_by(analysis.created_at.desc())

    return result.to_pandas().to_dict("records")


def get_lawyer_stats(
    con: ibis.BaseBackend, oab_number: str, oab_state: str
) -> Dict[str, Any]:
    """Get statistics for a specific lawyer"""

    analysis = con.table("decision_analysis")

    # Wins
    wins = (
        analysis.filter(analysis.winner_lawyer_oab == oab_number)
        .filter(analysis.winner_lawyer_state == oab_state)
        .count()
        .to_pyarrow()  # Scalar
        .as_py()
    )

    # Losses
    losses = (
        analysis.filter(analysis.loser_lawyer_oab == oab_number)
        .filter(analysis.loser_lawyer_state == oab_state)
        .count()
        .to_pyarrow()  # Scalar
        .as_py()
    )

    return {
        "oab_number": oab_number,
        "oab_state": oab_state,
        "wins": wins,
        "losses": losses,
        "total": wins + losses,
        "win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0,
    }
