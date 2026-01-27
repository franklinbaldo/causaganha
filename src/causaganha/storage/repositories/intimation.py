"""Intimation storage repository."""

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


def store_lawyer_associations(
    con: Backend,
    intimation_id: int,
    lawyers: list[Any],
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
        lawyers.filter(_.oab_number == oab_number)
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
        intimations.filter(_.ia_url.isnull())
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
        [ia_url, intimation_id],
    )
