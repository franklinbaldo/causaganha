from typing import Any

import structlog
from ibis import _
from ibis.backends.duckdb import Backend


logger = structlog.get_logger()


def store_intimations(
    con: Backend,
    intimations: list[Any],
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
