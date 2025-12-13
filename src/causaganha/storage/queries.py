"""Database queries."""

import asyncio

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
