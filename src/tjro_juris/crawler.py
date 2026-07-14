"""JURIS TJRO crawler — paginate documents by tipo and month.

The backend caps pagination at the Elasticsearch result window
(``from + size <= MAX_RESULT_WINDOW``, currently 10 000) — a full-corpus
``from``/``size`` sweep per tipo is impossible (e.g. SENTENÇA alone has
~1.9M docs). Instead, each (tipo, month) is fetched with server-side
``dtjulgamento`` date filters; windows whose totals still exceed the result
window are bisected into smaller date ranges. A single day that STILL
exceeds the window is subdivided by ``ds_orgao_julgador.raw`` buckets; when
even that cannot provably cover the window, the crawl FAILS LOUD
(:class:`JurisWindowOverflowError`) — for an archival corpus, "finished
successfully but lost documents" is worse than failing.
"""

from __future__ import annotations

import calendar
import time
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

import structlog

from tjro_juris.client import (
    MAX_RESULT_WINDOW,
    PAGE_SIZE,
    TIPOS,
    clean_html,
    doc_url,
    get_aggregations,
    search,
)


log = structlog.get_logger()

_MONTHS_PER_YEAR = 12
_REQUEST_INTERVAL = 0.5  # seconds between requests

# Aggregation bucket used to subdivide a single-day window that exceeds the
# ES result window. Verified live (2026-07-12): the search endpoint honors
# ``ds_orgao_julgador.raw`` as a ``fields`` filter, and the aggregations
# endpoint exposes the corresponding ``orgaos_julgadores`` buckets per tipo.
_ORGAO_FIELD = "ds_orgao_julgador.raw"
_ORGAO_AGG_KEY = "orgaos_julgadores"


class JurisWindowOverflowError(RuntimeError):
    """A window exceeds the ES result window and cannot be provably subdivided.

    Raised instead of silently truncating: recording a truncated window as
    complete would permanently lose documents from the archive.
    """


def _int_or_none(value: object) -> int | None:
    """Coerce a raw ES field to int, tolerating None/empty-string (both observed live)."""
    if value is None or value == "":
        return None
    return int(value)


def _extract_doc(raw: dict) -> dict:
    """Normalize a raw JURIS hit into a flat, cleaned dict.

    Captures the subset of the ~29 raw ES fields with clear analytical value
    beyond the original 11 (case grouping, subject classification, secrecy
    flag, content hash, instance level, stable órgão IDs) — see the
    2026-07-14 field audit. Deliberately excludes clearly redundant/
    low-value fields (``dtjulgamento_str`` duplicates ``dtjulgamento``,
    ``datarodape``/``cod_ini`` are display-only, etc).
    """
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
        "id_processo": _int_or_none(src.get("id_processo")),
        "cd_assunto_trf": src.get("cd_assunto_trf") or "",
        "ds_assunto_trf": src.get("ds_assunto_trf") or "",
        "cd_classe_judicial": src.get("cd_classe_judicial") or "",
        "nivel_sigilo_processo": _int_or_none(src.get("nivel_sigilo_processo")),
        "grau_jurisdicao": _int_or_none(src.get("grau_jurisdicao")),
        "ds_md5_documento": src.get("ds_md5_documento") or "",
        "id_orgao_julgador": _int_or_none(src.get("id_orgao_julgador")),
        "id_orgao_julgador_colegiado": _int_or_none(src.get("id_orgao_julgador_colegiado")),
    }


def _hits(data: dict) -> list[dict]:
    """Extract hit list from an ES-shaped response (or legacy ``results``)."""
    return data.get("hits", {}).get("hits", data.get("results", []))


def _total(data: dict) -> tuple[int, str]:
    """Extract ``(value, relation)`` from ``hits.total``.

    ``relation`` is ``"eq"`` (exact) or ``"gte"`` (lower bound — Elasticsearch
    stops counting at ``track_total_hits``). A ``gte`` total must be treated
    as potentially exceeding any cap it touches, never as an exact count.
    """
    total = data.get("hits", {}).get("total", {})
    if isinstance(total, dict):
        return int(total.get("value", 0)), str(total.get("relation", "eq"))
    return int(total or 0), "eq"


def _exceeds_window(value: int, relation: str) -> bool:
    """True when a ``hits.total`` may exceed the ES result window.

    ``{"value": 10000, "relation": "gte"}`` means ">= 10 000" — the real
    total is unknown, so any non-``eq`` relation is treated as exceeding.
    """
    return value > MAX_RESULT_WINDOW or relation != "eq"


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


def _fetch_pages(
    tipo: str,
    date_start: str,
    date_end: str,
    extra_fields: dict | None = None,
) -> list[dict]:
    """Paginate one date window, never exceeding the ES result window."""
    results: list[dict] = []
    from_ = 0
    while from_ < MAX_RESULT_WINDOW:
        size = min(PAGE_SIZE, MAX_RESULT_WINDOW - from_)
        time.sleep(_REQUEST_INTERVAL)
        data = search(
            tipo,
            from_=from_,
            size=size,
            date_start=date_start,
            date_end=date_end,
            extra_fields=extra_fields,
        )
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


def _orgao_buckets(tipo: str) -> list[str]:
    """Return the ``ds_orgao_julgador`` bucket keys for *tipo* (corpus-wide).

    The aggregations endpoint ignores date filters, so buckets are fetched
    for the whole tipo and each bucket is then probed with the day filter.
    """
    time.sleep(_REQUEST_INTERVAL)
    aggs = get_aggregations({"tipo.raw": [tipo]})
    buckets = aggs.get("aggregations", aggs).get(_ORGAO_AGG_KEY, {}).get("buckets", [])
    return [str(b["key"]) for b in buckets if b.get("key")]


def _fetch_day_by_orgao(tipo: str, day: str, day_total: int) -> list[dict]:
    """Subdivide a single-day window by órgão julgador buckets.

    Every bucket must individually fit the ES result window, and the bucket
    totals must sum EXACTLY to the day's total (proving no document falls
    outside the buckets). Any shortfall raises
    :class:`JurisWindowOverflowError` — never a silent truncation.
    """
    orgaos = _orgao_buckets(tipo)
    if not orgaos:
        msg = (
            f"JURIS window overflow: {tipo} {day} has {day_total} docs "
            f"(> {MAX_RESULT_WINDOW}) and no {_ORGAO_AGG_KEY} buckets are "
            "available to subdivide it"
        )
        raise JurisWindowOverflowError(msg)

    docs: list[dict] = []
    covered = 0
    for orgao in orgaos:
        extra = {_ORGAO_FIELD: [orgao]}
        time.sleep(_REQUEST_INTERVAL)
        probe = search(tipo, from_=0, size=1, date_start=day, date_end=day, extra_fields=extra)
        value, relation = _total(probe)
        if _exceeds_window(value, relation):
            msg = (
                f"JURIS window overflow: {tipo} {day} orgao={orgao!r} still has "
                f"{value} ({relation}) docs — no further subdivision axis available"
            )
            raise JurisWindowOverflowError(msg)
        if value == 0:
            continue
        covered += value
        docs.extend(_fetch_pages(tipo, day, day, extra_fields=extra))

    if covered != day_total:
        msg = (
            f"JURIS window overflow: {tipo} {day} orgao buckets cover {covered} "
            f"of {day_total} docs — the remainder would be silently lost"
        )
        raise JurisWindowOverflowError(msg)
    log.info("juris_window_split_by_orgao", tipo=tipo, date=day, total=day_total, docs=len(docs))
    return docs


def fetch_tipo_window(tipo: str, date_start: str, date_end: str) -> list[dict]:
    """Fetch all docs of ``tipo`` with dtjulgamento in [date_start, date_end].

    Probes the window total first (1-doc request); windows larger than the
    ES result window are bisected recursively down to single days. A single
    day that still exceeds the window is subdivided by órgão julgador; if
    that cannot provably cover the day, :class:`JurisWindowOverflowError`
    is raised (a truncated window must NEVER be recorded as complete).
    """
    time.sleep(_REQUEST_INTERVAL)
    probe = search(tipo, from_=0, size=1, date_start=date_start, date_end=date_end)
    total, relation = _total(probe)
    if total == 0 and relation == "eq":
        return []
    if _exceeds_window(total, relation):
        if date_start < date_end:
            mid, mid_next = _split_range(date_start, date_end)
            log.info(
                "juris_window_split",
                tipo=tipo,
                date_start=date_start,
                date_end=date_end,
                total=total,
                relation=relation,
            )
            left = fetch_tipo_window(tipo, date_start, mid)
            right = fetch_tipo_window(tipo, mid_next, date_end)
            return left + right
        log.warning(
            "juris_window_overflow_single_day",
            tipo=tipo,
            date=date_start,
            total=total,
            relation=relation,
        )
        return _fetch_day_by_orgao(tipo, date_start, total)
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
    start_year_month: str | None = None,
    skip: Callable[[str, str], bool] | None = None,
) -> Iterator[tuple[str, str, list[dict]]]:
    """Yield (tipo, year_month, docs), fetching each month with date filters.

    Server-side ``dtjulgamento`` windows keep every request inside the ES
    result window, so cost is O(docs in range) regardless of corpus size.

    ``start_year_month`` (AAAA-MM) narrows the start below year granularity
    (months before it are not yielded). ``skip(tipo, year_month)`` returning
    True short-circuits a window BEFORE any request is made — used to skip
    windows the manifest already records as complete.
    """
    if end_year_month is None:
        end_year_month = datetime.now(UTC).strftime("%Y-%m")
    for tipo in tipos or TIPOS:
        log.info("crawl_tipo_start", tipo=tipo)
        for year_month in _iter_year_months(start_year, end_year_month):
            if start_year_month is not None and year_month < start_year_month:
                continue
            if skip is not None and skip(tipo, year_month):
                log.info("crawl_window_skipped", tipo=tipo, year_month=year_month)
                continue
            yield tipo, year_month, fetch_tipo_month(tipo, year_month)
