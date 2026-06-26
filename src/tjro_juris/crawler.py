"""JURIS TJRO crawler — paginate documents by tipo and month."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Iterator

import structlog

from tjro_juris.client import PAGE_SIZE, TIPOS, clean_html, search


log = structlog.get_logger()

_MONTHS_PER_YEAR = 12


def crawl_tipo_month(tipo: str, year_month: str) -> list[dict]:
    """Paginate all docs of tipo, filter client-side by year_month, clean texto."""
    docs: list[dict] = []
    from_ = 0

    while True:
        data = search(tipo, from_=from_, size=PAGE_SIZE)
        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            break

        for h in hits:
            src = h.get("_source", {})
            dt = src.get("dtjulgamento", "") or ""
            if not dt.startswith(year_month):
                continue
            src = dict(src)
            src["texto_limpo"] = clean_html(src.get("ds_modelo_documento", "") or "")
            docs.append(src)

        if len(hits) < PAGE_SIZE:
            break

        from_ += PAGE_SIZE
        log.debug("crawl_tipo_month_page", tipo=tipo, year_month=year_month, from_=from_)

    log.info("crawl_tipo_month_done", tipo=tipo, year_month=year_month, count=len(docs))
    return docs


def crawl_all(
    start_year: int = 2010,
    end_year_month: str | None = None,
) -> Iterator[tuple[str, str, list[dict]]]:
    """Yield (tipo, year_month, docs) for all combinations."""
    now = datetime.now(UTC)
    if end_year_month is None:
        end_year_month = now.strftime("%Y-%m")

    year_months: list[str] = []
    y = start_year
    m = 1
    while True:
        ym = f"{y:04d}-{m:02d}"
        year_months.append(ym)
        if ym >= end_year_month:
            break
        m += 1
        if m > _MONTHS_PER_YEAR:
            m = 1
            y += 1

    for tipo in TIPOS:
        for year_month in year_months:
            log.info("crawling", tipo=tipo, year_month=year_month)
            docs = crawl_tipo_month(tipo, year_month)
            yield tipo, year_month, docs
