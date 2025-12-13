from typing import Any

import structlog
from ibis import BaseBackend

from causaganha.api.models import DestinatarioAdvogado, Intimation


logger = structlog.get_logger()


def store_intimations(con: BaseBackend, intimations: list[Intimation]) -> int:
    """Store intimations in database.

    Args:
        con: Ibis backend connection
        intimations: List of Intimation objects

    Returns:
        Number of inserted records
    """
    if not intimations:
        return 0

    inserted = 0
    # Access underlying DuckDB connection for parameterized queries
    # Ibis DuckDB backend exposes it as 'con'
    if not hasattr(con, "con"):
        logger.error("backend_not_duckdb_compatible", backend=type(con))
        return 0

    db_con = con.con

    for item in intimations:
        try:
            # We use RETURNING id to verify insertion/update
            # ON CONFLICT update ensures we don't duplicate but keep track of updates
            cursor = db_con.execute(
                """
                INSERT INTO intimations (
                    id, numero_processo, numeroprocessocommascara,
                    data_disponibilizacao, sigla_tribunal, id_orgao,
                    tipo_comunicacao, nome_orgao, texto, link,
                    tipo_documento, nome_classe, codigo_classe,
                    hash, status, analyzed
                ) VALUES (?, ?, ?, CAST(? AS DATE), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = now()
                RETURNING id
            """,
                [
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
                ],
            )

            if cursor.fetchone():
                inserted += 1

        except Exception as e:
            logger.warning("insert_failed", intimation_id=item.id, error=str(e))

    logger.info("intimations_stored", inserted=inserted, total=len(intimations))
    return inserted


def store_lawyer_associations(
    con: BaseBackend, intimation_id: int, lawyers: list[DestinatarioAdvogado],
) -> int:
    """Store lawyer associations.

    Args:
        con: Ibis backend connection
        intimation_id: ID of the intimation
        lawyers: List of DestinatarioAdvogado objects

    Returns:
        Number of inserted records
    """
    if not lawyers:
        return 0

    if not hasattr(con, "con"):
        return 0
    db_con = con.con

    inserted = 0
    for lawyer_data in lawyers:
        advogado = lawyer_data.advogado

        try:
            cursor = db_con.execute(
                """
                INSERT INTO intimation_lawyers (
                    intimation_id, oab_number, oab_state, lawyer_name
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                RETURNING intimation_id
            """,
                [intimation_id, advogado.numero_oab, advogado.uf_oab, advogado.nome],
            )

            if cursor.fetchone():
                inserted += 1
        except Exception as e:
            logger.warning("lawyer_association_failed", intimation_id=intimation_id, error=str(e))

    return inserted


def get_unanalyzed_intimations(con: BaseBackend, limit: int = 100) -> list[dict[str, Any]]:
    """Get intimations that need PDF analysis.

    Args:
        con: Ibis backend connection
        limit: Max number of records

    Returns:
        List of dicts representing intimations
    """
    intimations = con.table("intimations")

    # Filter analyzed == False AND link IS NOT NULL
    result = (
        intimations.filter(intimations.analyzed == False)
        .filter(intimations.link.notnull())
        .order_by(intimations.data_disponibilizacao.desc())
        .limit(limit)
    )

    return result.to_pandas().to_dict("records")
