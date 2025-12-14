"""Database queries."""

import asyncio
from typing import Any

import ibis
from ibis import BaseBackend

from causaganha.domain.models import Intimation


def _intimation_to_db(intimation: Intimation) -> dict[str, object]:
    """Convert Intimation model to database schema dict."""
    return {
        "id": intimation.id,
        "numero_processo": intimation.numero_processo,
        "data_disponibilizacao": intimation.data_disponibilizacao.isoformat(),
        "sigla_tribunal": intimation.sigla_tribunal,
        "tipo_comunicacao": intimation.tipo_comunicacao,
        "nome_orgao": intimation.nome_orgao,
        "texto": intimation.texto,
        "link": intimation.link,
        "tipo_documento": intimation.tipo_documento,
        "nome_classe": intimation.nome_classe,
        "codigo_classe": intimation.codigo_classe,
        "hash": intimation.hash,
        "status": intimation.status,
    }


def _sync_store_intimations(con: BaseBackend, intimations: list[Intimation]) -> None:
    """Synchronous implementation of storing intimations."""
    if not intimations:
        return

    data = [_intimation_to_db(i) for i in intimations]

    # Using memtable to insert data
    t = ibis.memtable(data)
    con.insert("intimations", t)


async def store_intimations(con: BaseBackend, intimations: list[Intimation]) -> None:
    """Store a list of intimations in the database asynchronously.

    Args:
        con: Ibis DuckDB connection backend.
        intimations: List of Intimation objects to store.
    """
    await asyncio.to_thread(_sync_store_intimations, con, intimations)


def _sync_get_unanalyzed_intimations(con: BaseBackend, limit: int = 100) -> list[dict[str, Any]]:
    """Synchronous implementation of fetching unanalyzed intimations."""
    t_int = con.table("intimations")
    t_res = con.table("analysis_results")

    # Left join to find intimations without analysis
    # Filter where analysis_results.id is NULL

    # Ibis join syntax: t1.left_join(t2, predicates)
    joined = t_int.left_join(t_res, t_int.id == t_res.intimation_id)

    # Filter where analysis result is missing
    # Note: t_res['id'] might be ambiguous after join if not handled carefully,
    # but Ibis usually handles this.
    # Actually, left join keeps t_int columns. t_res columns will be null.

    filtered = joined.filter(t_res["id"].isnull())

    # Select only intimation columns and limit
    # We select all columns from t_int.
    # To do this in Ibis, we can just select the table expression or specific columns.
    # Selecting columns explicitly is safer.

    # Actually, assuming 'id' is unique, we can just project t_int columns.
    # But wait, joined table has columns from both.

    # Let's verify we only fetch rows that have a link (to download PDF)
    filtered = filtered.filter(t_int.link.notnull())

    query = filtered.select(t_int).limit(limit)

    return query.execute().to_dict(orient="records")


async def get_unanalyzed_intimations(con: BaseBackend, limit: int = 100) -> list[dict[str, Any]]:
    """Fetch intimations that have not been analyzed yet.

    Args:
        con: Ibis connection.
        limit: Max number of records to fetch.

    Returns:
        List of dicts representing intimations.
    """
    return await asyncio.to_thread(_sync_get_unanalyzed_intimations, con, limit)


def _sync_store_analysis_result(con: BaseBackend, result: dict[str, Any]) -> None:
    """Synchronous store analysis result."""
    t = ibis.memtable([result])
    con.insert("analysis_results", t)

async def store_analysis_result(con: BaseBackend, result: dict[str, Any]) -> None:
    """Store analysis result.

    Args:
        con: Ibis connection.
        result: Dict matching analysis_results schema.
    """
    await asyncio.to_thread(_sync_store_analysis_result, con, result)
