from typing import Any

import structlog
from ibis import _
from ibis.backends.duckdb import Backend


logger = structlog.get_logger()


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
