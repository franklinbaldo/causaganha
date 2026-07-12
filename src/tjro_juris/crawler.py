"""JURIS TJRO crawler — paginate documents by tipo and month.

The backend caps pagination at the Elasticsearch result window
(``from + size <= MAX_RESULT_WINDOW``, currently 10 000) — a full-corpus
``from``/``size`` sweep per tipo is impossible (e.g. SENTENÇA alone has
~1.9M docs). Instead, each (tipo, month) is fetched with server-side
``dtjulgamento`` date filters; windows whose totals still exceed the result
window are bisected into smaller date ranges.
"""

from __future__ import annotations

import calendar
import time
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator

import structlog

from tjro_juris.client import (
    MAX_RESULT_WINDOW,
    PAGE_SIZE,
    TIPOS,
    clean_html,
    doc_url,
    search,
)


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


def _hits(data: dict) -> list[dict]:
    """Extract hit list from an ES-shaped response (or legacy ``results``)."""
    return data.get("hits", {}).get("hits", data.get("results", []))


def _total(data: dict) -> int:
    """Extract total hit count from an ES-shaped response."""
    total = data.get("hits", {}).get("total", {})
    if isinstance(total, dict):
        return int(total.get("value", 0))
    return int(total or 0)


def _month_bounds(year_month: str) -> tuple[str, str]:
    """``"2024-03"`` -> ``("2024-03-01", "2024-03-31")`` (inclusive)."""
    year, month = int(year_month[:4]), int(year_month[5:7])
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def _split_range(date_start: str, date_end: str) -> tuple[str, str]:
    """Bisect an inclusive date range into two non-overlapping halves.

    Returns ``(mid, mid_plus_one)`` so callers fetch ``[start, mid]`` and
    ``[mid_plus_one, end]``.
    """
    start = date.fromisoformat(date_start)
    end = date.fromisoformat(date_end)
    mid = start + (end - start) // 2
    return mid.isoformat(), (mid + timedelta(days=1)).isoformat()


def _fetch_pages(tipo: str, date_start: str, date_end: str) -> list[dict]:
    """Paginate one date window, never exceeding the ES result window."""
    results: list[dict] = []
    from_ = 0
    while from_ < MAX_RESULT_WINDOW:
        size = min(PAGE_SIZE, MAX_RESULT_WINDOW - from_)
        time.sleep(_REQUEST_INTERVAL)
        data = search(tipo, from_=from_, size=size, date_start=date_start, date_end=date_end)
        hits = _hits(data)
        if not hits:
            break
        results.extend(_extract_doc(raw) for raw in hits)
        log.debug(
            "fetch_window_page", tipo=tipo, date_start=date_start, from_=from_, page_hits=len(hits)
        )
        if len(hits) < size:
            break
        from_ += size
    return results


def fetch_tipo_window(tipo: str, date_start: str, date_end: str) -> list[dict]:
    """Fetch all docs of ``tipo`` with dtjulgamento in [date_start, date_end].

    Probes the window total first (1-doc request); windows larger than the
    ES result window are bisected recursively down to single days.
    """
    time.sleep(_REQUEST_INTERVAL)
    probe = search(tipo, from_=0, size=1, date_start=date_start, date_end=date_end)
    total = _total(probe)
    if total == 0:
        return []
    if total > MAX_RESULT_WINDOW:
        if date_start < date_end:
            mid, mid_next = _split_range(date_start, date_end)
            log.info(
                "juris_window_split",
                tipo=tipo,
                date_start=date_start,
                date_end=date_end,
                total=total,
            )
            left = fetch_tipo_window(tipo, date_start, mid)
            right = fetch_tipo_window(tipo, mid_next, date_end)
            return left + right
        log.warning("juris_window_truncated", tipo=tipo, date=date_start, total=total)
    return _fetch_pages(tipo, date_start, date_end)


def fetch_tipo_month(tipo: str, year_month: str) -> list[dict]:
    """Fetch all docs of a given tipo julgados in ``year_month`` (AAAA-MM)."""
    date_start, date_end = _month_bounds(year_month)
    docs = fetch_tipo_window(tipo, date_start, date_end)
    log.info("fetch_tipo_month_done", tipo=tipo, year_month=year_month, total=len(docs))
    return docs


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
    """Yield (tipo, year_month, docs), fetching each month with date filters.

    Server-side ``dtjulgamento`` windows keep every request inside the ES
    result window, so cost is O(docs in range) regardless of corpus size.
    """
    if end_year_month is None:
        end_year_month = datetime.now(UTC).strftime("%Y-%m")
    for tipo in tipos or TIPOS:
        log.info("crawl_tipo_start", tipo=tipo)
        for year_month in _iter_year_months(start_year, end_year_month):
            yield tipo, year_month, fetch_tipo_month(tipo, year_month)
