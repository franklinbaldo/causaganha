from typing import Any

from ibis import _
from ibis.backends.duckdb import Backend


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
