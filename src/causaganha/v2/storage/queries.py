"""Common analytical queries using Ibis."""

from typing import Any

import ibis
import structlog


logger = structlog.get_logger()


def store_intimations(
    con: ibis.BaseBackend,
    intimations: list,
) -> int:
    """Store intimations in database.

    Returns count of new records inserted.
    """
    if not intimations:
        return 0

    # Prepare records
    records = []
    for item in intimations:
        records.append(
            {
                "id": item.id,
                "numero_processo": item.numero_processo,
                "numeroprocessocommascara": item.numeroprocessocommascara,
                "data_disponibilizacao": item.data_disponibilizacao,
                "sigla_tribunal": item.siglaTribunal,
                "id_orgao": item.idOrgao,
                "tipo_comunicacao": item.tipoComunicacao,
                "nome_orgao": item.nomeOrgao,
                "texto": item.texto,
                "link": item.link,
                "tipo_documento": item.tipoDocumento,
                "nome_classe": item.nomeClasse,
                "codigo_classe": item.codigoClasse,
                "hash": item.hash,
                "status": item.status,
                "analyzed": False,
            }
        )

    # Use raw SQL for upsert (Ibis doesn't have native upsert yet)
    inserted = 0
    for record in records:
        try:
            # Note: Explicitly handling None/NULL for id_orgao and numeroprocessocommascara
            id_orgao = record["id_orgao"] if record["id_orgao"] is not None else "NULL"
            numero_formatado = (
                f"'{record['numeroprocessocommascara']}'"
                if record["numeroprocessocommascara"]
                else "NULL"
            )
            codigo_classe = f"'{record['codigo_classe']}'" if record["codigo_classe"] else "NULL"

            # Escape strings to prevent SQL injection (basic)
            # In production, use parameterized queries if possible, but DuckDB python raw_sql might not support it easily via Ibis
            # Or use connection.con.execute(sql, params) directly

            nome_orgao = record["nome_orgao"].replace("'", "''")
            texto = record["texto"].replace("'", "''")

            sql = f"""
                INSERT INTO intimations (
                    id, numero_processo, numeroprocessocommascara,
                    data_disponibilizacao, sigla_tribunal, id_orgao,
                    tipo_comunicacao, nome_orgao, texto, link,
                    tipo_documento, nome_classe, codigo_classe,
                    hash, status, analyzed
                ) VALUES (
                    {record["id"]},
                    '{record["numero_processo"]}',
                    {numero_formatado},
                    '{record["data_disponibilizacao"]}',
                    '{record["sigla_tribunal"]}',
                    {id_orgao},
                    '{record["tipo_comunicacao"]}',
                    '{nome_orgao}',
                    '{texto}',
                    '{record["link"]}',
                    '{record["tipo_documento"]}',
                    '{record["nome_classe"]}',
                    {codigo_classe},
                    '{record["hash"]}',
                    '{record["status"]}',
                    FALSE
                )
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = now()
            """
            con.raw_sql(sql)
            inserted += 1
        except Exception as e:
            logger.warning("insert_failed", intimation_id=record["id"], error=str(e))

    logger.info("intimations_stored", inserted=inserted, total=len(records))
    return inserted


def get_unanalyzed_intimations(
    con: ibis.BaseBackend,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get intimations that need PDF analysis."""
    intimations = con.table("intimations")

    # Filter for unanalyzed items that have a link
    result = (
        intimations.filter(not intimations.analyzed)
        .filter(intimations.link.notnull())
        .order_by(intimations.data_disponibilizacao.desc())
        .limit(limit)
    )

    return result.to_pandas().to_dict("records")
