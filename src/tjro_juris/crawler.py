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
import json
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
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


def _partial_cache_path(
    cache_dir: Path, tipo: str, date_start: str, date_end: str, extra_fields: dict | None
) -> Path:
    """Staging file for in-progress pagination of one (tipo, date window).

    Keyed by tipo + date range + extra_fields so bisected sub-windows (and
    órgão-julgador sub-splits, which share a date range but differ by
    extra_fields) never collide.
    """
    safe_tipo = tipo.replace(" ", "_").replace("/", "_")
    suffix = ""
    if extra_fields:
        raw_key = "_".join(f"{k}={v}" for k, v in sorted(extra_fields.items()))
        suffix = "_" + "".join(c if c.isalnum() else "-" for c in raw_key)[:60]
    return cache_dir / safe_tipo / f"{date_start}_{date_end}{suffix}.jsonl"


def _load_partial_cache(path: Path) -> list[dict]:
    """Docs already fetched for this window in a prior, interrupted attempt."""
    if not path.exists():
        return []
    docs = []
    with path.open(encoding="utf-8") as fh:
        for raw_line in fh:
            stripped = raw_line.strip()
            if stripped:
                docs.append(json.loads(stripped))
    return docs


def _append_partial_cache(path: Path, docs: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for doc in docs:
            fh.write(json.dumps(doc, ensure_ascii=False) + "\n")


def _fetch_pages(
    tipo: str,
    date_start: str,
    date_end: str,
    extra_fields: dict | None = None,
    cache_dir: Path | None = None,
) -> list[dict]:
    """Paginate one date window, never exceeding the ES result window.

    When *cache_dir* is given, each page is appended to a staging file as
    soon as it's fetched — so a mid-window failure (STIC block, transport
    error) loses at most one page's worth of work on retry, not the whole
    window. ``from_`` resumes from ``len(cached docs)`` regardless of what
    PAGE_SIZE was used to reach that offset (ES pagination is just a count).
    The staging file is deleted only once the window is PROVABLY complete
    (server returned a short/empty page) — a window that errors out always
    leaves its cache behind, on purpose, rather than risk it being mistaken
    for a finished fetch.
    """
    cache_path = (
        _partial_cache_path(cache_dir, tipo, date_start, date_end, extra_fields)
        if cache_dir is not None
        else None
    )
    results: list[dict] = _load_partial_cache(cache_path) if cache_path is not None else []
    from_ = len(results)
    if from_:
        log.info(
            "fetch_page_resumed_from_cache", tipo=tipo, date_start=date_start, resumed_from=from_
        )
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
        page_docs = [_extract_doc(raw) for raw in hits]
        results.extend(page_docs)
        if cache_path is not None:
            _append_partial_cache(cache_path, page_docs)
        log.debug(
            "fetch_window_page", tipo=tipo, date_start=date_start, from_=from_, page_hits=len(hits)
        )
        if len(hits) < size:
            break
        from_ += size
    if cache_path is not None:
        cache_path.unlink(missing_ok=True)
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


def _fetch_day_by_orgao(
    tipo: str, day: str, day_total: int, cache_dir: Path | None = None
) -> list[dict]:
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
        docs.extend(_fetch_pages(tipo, day, day, extra_fields=extra, cache_dir=cache_dir))

    if covered != day_total:
        msg = (
            f"JURIS window overflow: {tipo} {day} orgao buckets cover {covered} "
            f"of {day_total} docs — the remainder would be silently lost"
        )
        raise JurisWindowOverflowError(msg)
    log.info("juris_window_split_by_orgao", tipo=tipo, date=day, total=day_total, docs=len(docs))
    return docs


def fetch_tipo_window(
    tipo: str, date_start: str, date_end: str, cache_dir: Path | None = None
) -> list[dict]:
    """Fetch all docs of ``tipo`` with dtjulgamento in [date_start, date_end].

    Probes the window total first (1-doc request); windows larger than the
    ES result window are bisected recursively down to single days. A single
    day that still exceeds the window is subdivided by órgão julgador; if
    that cannot provably cover the day, :class:`JurisWindowOverflowError`
    is raised (a truncated window must NEVER be recorded as complete).

    *cache_dir*, when given, enables page-level resume (see ``_fetch_pages``)
    for the leaf window this call bottoms out at.
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
            left = fetch_tipo_window(tipo, date_start, mid, cache_dir=cache_dir)
            right = fetch_tipo_window(tipo, mid_next, date_end, cache_dir=cache_dir)
            return left + right
        log.warning(
            "juris_window_overflow_single_day",
            tipo=tipo,
            date=date_start,
            total=total,
            relation=relation,
        )
        return _fetch_day_by_orgao(tipo, date_start, total, cache_dir=cache_dir)
    return _fetch_pages(tipo, date_start, date_end, cache_dir=cache_dir)


def fetch_tipo_month(tipo: str, year_month: str, cache_dir: Path | None = None) -> list[dict]:
    """Fetch all docs of a given tipo julgados in ``year_month`` (AAAA-MM)."""
    date_start, date_end = _month_bounds(year_month)
    docs = fetch_tipo_window(tipo, date_start, date_end, cache_dir=cache_dir)
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
    cache_dir: Path | None = None,
) -> Iterator[tuple[str, str, list[dict]]]:
    """Yield (tipo, year_month, docs), fetching each month with date filters.

    Server-side ``dtjulgamento`` windows keep every request inside the ES
    result window, so cost is O(docs in range) regardless of corpus size.

    ``start_year_month`` (AAAA-MM) narrows the start below year granularity
    (months before it are not yielded). ``skip(tipo, year_month)`` returning
    True short-circuits a window BEFORE any request is made — used to skip
    windows the manifest already records as complete. ``cache_dir``, when
    given, persists in-progress pagination per window so a mid-month failure
    (STIC block, transport error) resumes from the last completed page on
    retry instead of restarting the whole month — see ``_fetch_pages``.
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
            yield tipo, year_month, fetch_tipo_month(tipo, year_month, cache_dir=cache_dir)
