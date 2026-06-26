"""JURIS TJRO crawler — paginate documents by tipo and month."""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator

import structlog

from tjro_juris.client import PAGE_SIZE, TIPOS, clean_html, doc_url, search


log = structlog.get_logger()

_MONTHS_PER_YEAR = 12
_REQUEST_INTERVAL = 0.5  # seconds between requests


def _extract_doc(raw: dict) -> dict:
    """Normalize a raw JURIS hit into a flat, cleaned dict."""
    src = raw.get("_source", raw)
    orgao = src.get("ds_orgao_julgador_colegiado") or src.get("ds_orgao_julgador", "")
    relator = src.get("nome_relator_acordao") or src.get("ds_nome", "")
    id_doc = src.get("id_processo_documento")
    id_principal = src.get("id_documento_principal")
    sistema = src.get("sistema_origem", "")
    tipo_val = src.get("tipo", "")

    url = doc_url(
        id_doc, sistema_origem=sistema, tipo=tipo_val, id_documento_principal=id_principal
    )

    return {
        "id_documento": int(id_doc) if id_doc is not None else None,
        "nr_processo": src.get("nr_processo", ""),
        "tipo": tipo_val,
        "classe_judicial": src.get("ds_classe_judicial", ""),
        "orgao": orgao,
        "relator": relator,
        "sistema_origem": sistema,
        "data_julgamento": src.get("dtjulgamento", ""),
        "texto_limpo": clean_html(src.get("ds_modelo_documento", "") or ""),
        "url_portal": url,
        "extraido_em": datetime.now(UTC).isoformat(),
    }


def fetch_tipo_all(tipo: str) -> list[dict]:
    """Fetch ALL documents of a given tipo in a single paginated sweep.

    Returns cleaned docs. Called once per tipo; caller buckets by month.
    """
    results: list[dict] = []
    from_ = 0
    while True:
        time.sleep(_REQUEST_INTERVAL)
        data = search(tipo, from_=from_, size=PAGE_SIZE)
        # JURIS returns hits nested under "hits.hits" or directly as "results"
        hits = data.get("hits", {}).get("hits", data.get("results", []))
        if not hits:
            break
        for raw in hits:
            results.append(_extract_doc(raw))
        log.debug("fetch_tipo_page", tipo=tipo, from_=from_, page_hits=len(hits))
        if len(hits) < PAGE_SIZE:
            break
        from_ += PAGE_SIZE
    log.info("fetch_tipo_done", tipo=tipo, total=len(results))
    return results


def crawl_tipo_by_month(tipo: str) -> dict[str, list[dict]]:
    """Fetch all docs of tipo once, bucket by AAAA-MM of dtjulgamento."""
    all_docs = fetch_tipo_all(tipo)
    buckets: dict[str, list[dict]] = defaultdict(list)
    for doc in all_docs:
        dj = (doc.get("data_julgamento") or "")[:7]  # AAAA-MM
        if dj:
            buckets[dj].append(doc)
    return dict(buckets)


def _iter_year_months(start_year: int, end_year_month: str) -> Iterator[str]:
    y, m = start_year, 1
    while True:
        ym = f"{y:04d}-{m:02d}"
        yield ym
        if ym >= end_year_month:
            break
        m += 1
        if m > _MONTHS_PER_YEAR:
            m, y = 1, y + 1


def crawl_all(
    start_year: int = 2010,
    end_year_month: str | None = None,
    tipos: list[str] | None = None,
) -> Iterator[tuple[str, str, list[dict]]]:
    """Yield (tipo, year_month, docs) fetching each tipo only once.

    For each tipo, the entire corpus is fetched in one paginated sweep and
    then bucketed by month client-side — avoids re-crawling the corpus once
    per month (which would be O(months * corpus) requests).
    """
    if end_year_month is None:
        end_year_month = datetime.now(UTC).strftime("%Y-%m")
    for tipo in tipos or TIPOS:
        log.info("crawl_tipo_start", tipo=tipo)
        buckets = crawl_tipo_by_month(tipo)
        for year_month in _iter_year_months(start_year, end_year_month):
            yield tipo, year_month, buckets.get(year_month, [])
