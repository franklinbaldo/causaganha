"""Dedup for DataJud documents — multi-grau aware.

The same CNJ legitimately appears in separate documents per grau (the ES
``_id`` encodes ``{TRIBUNAL}_{classe}_{grau}_{orgao}_{numero}``), so the
natural key is ``(numeroProcesso, grau, orgaoJulgador.codigo)`` — never the
CNJ alone. Between versions of the same document, the most recent
``dataHoraUltimaAtualizacao`` wins; on ties the later occurrence (i.e. the
freshly fetched row) wins.
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterable

    from datajud.models import ProcessoCapa


CapaKey = tuple[str, str, int | None]


def capa_row_key(row: dict) -> CapaKey:
    """Natural key of a capa parquet row."""
    return (row["numero_processo"], row["grau"], row["orgao_julgador_codigo"])


def dedup_capas(capas: Iterable[ProcessoCapa]) -> list[ProcessoCapa]:
    """Dedup parsed capas by natural key, latest ``dataHoraUltimaAtualizacao`` wins."""
    best: dict[CapaKey, ProcessoCapa] = {}
    for capa in capas:
        key = capa.dedup_key()
        current = best.get(key)
        if current is None or (capa.data_hora_ultima_atualizacao or "") >= (
            current.data_hora_ultima_atualizacao or ""
        ):
            best[key] = capa
    return list(best.values())


def merge_capa_rows(existing: list[dict], new: list[dict]) -> list[dict]:
    """Merge existing parquet rows with freshly fetched ones.

    Same key policy as :func:`dedup_capas`; *new* rows come after *existing*
    so they win ties (``>=``). ISO-8601 strings compare lexicographically.
    """
    best: dict[CapaKey, dict] = {}
    for row in [*existing, *new]:
        key = capa_row_key(row)
        current = best.get(key)
        if current is None or (row.get("ultima_atualizacao") or "") >= (
            current.get("ultima_atualizacao") or ""
        ):
            best[key] = row
    return sorted(best.values(), key=lambda r: (r["numero_processo"], r["grau"]))


def merge_movimento_rows(
    existing: list[dict],
    new: list[dict],
    refreshed_keys: set[CapaKey],
) -> list[dict]:
    """Replace the movimento lines of refreshed documents wholesale.

    Movements of a document are always fetched together with its capa, so any
    old rows belonging to a refreshed ``(numeroProcesso, grau, orgao)`` key
    are dropped — including documents whose new fetch has zero movements.
    """
    kept = [row for row in existing if capa_row_key(row) not in refreshed_keys]
    return sorted(
        [*kept, *new],
        key=lambda r: (r["numero_processo"], r["grau"], r.get("data_hora") or ""),
    )
