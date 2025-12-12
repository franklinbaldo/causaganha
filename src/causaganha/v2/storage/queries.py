"""Common analytical queries using Ibis"""

from typing import List

import ibis
import structlog

from ..api.models import Intimation

logger = structlog.get_logger()


def store_intimations(con: ibis.BaseBackend, intimations: List[Intimation]) -> int:
    """
    Store intimations in database

    Returns count of new records inserted
    """
    if not intimations:
        return 0

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
