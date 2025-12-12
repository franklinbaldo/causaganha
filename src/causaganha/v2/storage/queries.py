"""Database queries."""

import asyncio
from datetime import UTC, datetime

import ibis
from ibis import BaseBackend

from causaganha.api.models import Intimation


async def store_intimations(con: BaseBackend, intimations: list[Intimation]) -> None:
    """Store intimations in the database.

    Args:
        con: Ibis DuckDB connection backend.
        intimations: List of Intimation objects to store.
    """
    if not intimations:
        return

    # Map Intimation objects to schema dictionary
    data = []
    now = datetime.now(UTC)

    for i in intimations:
        row = {
            "id": i.id,
            "numero_processo": i.numero_processo,
            "data_disponibilizacao": i.data_disponibilizacao,
            "sigla_tribunal": i.siglaTribunal,
            "tipo_comunicacao": i.tipoComunicacao,
            "nome_orgao": i.nomeOrgao,
            "texto": i.texto,
            "link": i.link,
            "tipo_documento": i.tipoDocumento,
            "nome_classe": i.nomeClasse,
            "hash": i.hash,
            "status": i.status,
            "created_at": now,
        }
        data.append(row)

    def _sync_insert() -> None:
        t_mem = ibis.memtable(data)
        con.insert("intimations", t_mem)

    await asyncio.to_thread(_sync_insert)
