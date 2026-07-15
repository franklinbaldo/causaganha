"""Tests for tjro_juris.crawler — field extraction, windowed pagination, splitting."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

from tjro_juris import crawler
from tjro_juris.client import MAX_RESULT_WINDOW, PAGE_SIZE
from tjro_juris.crawler import (
    JurisWindowOverflowError,
    _exceeds_window,
    _extract_doc,
    _fetch_pages,
    _iter_year_months,
    _load_partial_cache,
    _month_bounds,
    _partial_cache_path,
    _split_range,
    _total,
    crawl_all,
    fetch_tipo_month,
    fetch_tipo_window,
)


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize the politeness delay between JURIS requests."""
    monkeypatch.setattr(time, "sleep", lambda _s: None)


def _hit(doc_id: int, **extra: object) -> dict:
    src = {
        "id_processo_documento": doc_id,
        "nr_processo": f"000{doc_id}-11.2024.8.22.0001",
        "tipo": "ACÓRDÃO",
        "ds_classe_judicial": "Apelação Cível",
        "ds_orgao_julgador_colegiado": "1ª Câmara Cível",
        "nome_relator_acordao": "Des. Fulano",
        "sistema_origem": "pje2instancia",
        "dtjulgamento": "2024-03-15",
        "ds_modelo_documento": "<p>EMENTA: teste</p>",
    }
    src.update(extra)
    return {"_source": src}


def _es_response(hits: list[dict], total: int | None = None) -> dict:
    return {"hits": {"total": {"value": len(hits) if total is None else total}, "hits": hits}}


# ── _extract_doc ─────────────────────────────────────────────────────────


def test_extract_doc_maps_all_fields() -> None:
    doc = _extract_doc(_hit(42, id_documento_principal=7))
    assert doc["id_documento"] == 42
    assert doc["nr_processo"] == "00042-11.2024.8.22.0001"
    assert doc["tipo"] == "ACÓRDÃO"
    assert doc["classe_judicial"] == "Apelação Cível"
    assert doc["orgao"] == "1ª Câmara Cível"
    assert doc["relator"] == "Des. Fulano"
    assert doc["sistema_origem"] == "pje2instancia"
    assert doc["data_julgamento"] == "2024-03-15"
    assert doc["texto_limpo"] == "EMENTA: teste"
    assert "id=42" in doc["url_portal"]
    assert "id_documento_principal=7" in doc["url_portal"]
    assert doc["extraido_em"]  # timestamp stamped


def test_extract_doc_orgao_falls_back_to_non_colegiado() -> None:
    doc = _extract_doc(_hit(1, ds_orgao_julgador_colegiado=None, ds_orgao_julgador="2ª Vara Cível"))
    assert doc["orgao"] == "2ª Vara Cível"


def test_extract_doc_relator_falls_back_to_ds_nome() -> None:
    doc = _extract_doc(_hit(1, nome_relator_acordao=None, ds_nome="Juiz Beltrano"))
    assert doc["relator"] == "Juiz Beltrano"


def test_extract_doc_without_source_wrapper() -> None:
    raw = _hit(9)["_source"]
    doc = _extract_doc(raw)
    assert doc["id_documento"] == 9


def test_extract_doc_missing_id_is_none_and_url_empty() -> None:
    doc = _extract_doc({"_source": {"tipo": "VOTO"}})
    assert doc["id_documento"] is None
    assert doc["url_portal"] == ""


def test_extract_doc_string_id_coerced_to_int() -> None:
    doc = _extract_doc({"_source": {"id_processo_documento": "77"}})
    assert doc["id_documento"] == 77


# ── _month_bounds / _split_range ─────────────────────────────────────────


def test_month_bounds_regular_month() -> None:
    assert _month_bounds("2024-03") == ("2024-03-01", "2024-03-31")


def test_month_bounds_leap_february() -> None:
    assert _month_bounds("2024-02") == ("2024-02-01", "2024-02-29")
    assert _month_bounds("2023-02") == ("2023-02-01", "2023-02-28")


def test_split_range_bisects_without_overlap() -> None:
    mid, mid_next = _split_range("2024-03-01", "2024-03-31")
    assert mid == "2024-03-16"
    assert mid_next == "2024-03-17"


def test_split_range_two_days() -> None:
    mid, mid_next = _split_range("2024-03-01", "2024-03-02")
    assert (mid, mid_next) == ("2024-03-01", "2024-03-02")


# ── fetch_tipo_window (probe + pagination + split) ───────────────────────


def _fake_search_windows(
    windows: dict[tuple[str, str], dict[int, list[dict]]],
) -> tuple[
    list[dict],
    object,
]:
    """Fake ``search`` with canned pages keyed by (date_start, date_end) then from_.

    The probe (size=1) answers with the window's total; page requests return
    the canned page for ``from_``.
    """
    calls: list[dict] = []

    def _fake(
        tipo: str,
        from_: int = 0,
        size: int = PAGE_SIZE,
        texto: str = "",
        *,
        date_start: str | None = None,
        date_end: str | None = None,
        extra_fields: dict | None = None,
    ) -> dict:
        calls.append(
            {
                "tipo": tipo,
                "from_": from_,
                "size": size,
                "start": date_start,
                "end": date_end,
                "extra_fields": extra_fields,
            }
        )
        pages = windows.get((date_start, date_end), {})
        total = sum(len(v) for v in pages.values())
        if size == 1:  # probe
            first = pages.get(0, [])
            return _es_response(first[:1], total=total)
        return _es_response(pages.get(from_, []), total=total)

    return calls, _fake


def test_fetch_window_stops_on_short_page(monkeypatch: pytest.MonkeyPatch) -> None:
    window = ("2024-03-01", "2024-03-31")
    pages = {
        0: [_hit(i) for i in range(PAGE_SIZE)],
        PAGE_SIZE: [_hit(PAGE_SIZE + i) for i in range(3)],
    }
    calls, fake = _fake_search_windows({window: pages})
    monkeypatch.setattr(crawler, "search", fake)

    docs = fetch_tipo_window("ACÓRDÃO", *window)

    assert len(docs) == PAGE_SIZE + 3
    # probe + two pages, no third page request
    assert [(c["from_"], c["size"]) for c in calls] == [
        (0, 1),
        (0, PAGE_SIZE),
        (PAGE_SIZE, PAGE_SIZE),
    ]
    assert all(c["start"] == window[0] and c["end"] == window[1] for c in calls)


def test_fetch_window_empty_probe_makes_single_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, fake = _fake_search_windows({})
    monkeypatch.setattr(crawler, "search", fake)

    assert fetch_tipo_window("VOTO", "2024-01-01", "2024-01-31") == []
    assert len(calls) == 1  # only the probe


def test_total_extracts_value_and_relation() -> None:
    assert _total({"hits": {"total": {"value": 42, "relation": "eq"}}}) == (42, "eq")
    assert _total({"hits": {"total": {"value": 10_000, "relation": "gte"}}}) == (10_000, "gte")
    # bare-int / missing-total shapes default to an exact zero
    assert _total({"hits": {"total": 7}}) == (7, "eq")
    assert _total({"hits": {}}) == (0, "eq")


def test_exceeds_window_treats_any_non_eq_relation_as_exceeding() -> None:
    """A 'gte' relation means the real total is UNKNOWN — never treat it as exact."""
    assert _exceeds_window(MAX_RESULT_WINDOW + 1, "eq") is True
    assert _exceeds_window(MAX_RESULT_WINDOW, "eq") is False
    assert _exceeds_window(1, "gte") is True  # small value, but relation says "at least"
    assert _exceeds_window(0, "eq") is False


def _fake_orgao_search(
    day: str,
    day_total: int,
    orgao_totals: dict[str, int],
    orgao_docs: dict[str, list[dict]],
    *,
    day_relation: str = "eq",
) -> object:
    """Fake ``search`` serving a single-day window subdivision by órgão.

    - probe with no ``extra_fields`` (or an órgão not in ``orgao_totals``)
      returns the day/órgão total.
    - page requests (size > 1) with an órgão filter return that órgão's docs.
    """

    def _fake(
        tipo: str,
        from_: int = 0,
        size: int = PAGE_SIZE,
        texto: str = "",
        *,
        date_start: str | None = None,
        date_end: str | None = None,
        extra_fields: dict | None = None,
    ) -> dict:
        assert (date_start, date_end) == (day, day)
        orgao = (extra_fields or {}).get("ds_orgao_julgador.raw", [None])[0]
        if size == 1:  # probe
            if orgao is None:
                return {"hits": {"total": {"value": day_total, "relation": day_relation}}}
            total = orgao_totals.get(orgao, 0)
            return {"hits": {"total": {"value": total, "relation": "eq"}}}
        # page fetch — always for a specific órgão
        docs = orgao_docs.get(orgao, [])
        return _es_response(docs[from_ : from_ + size], total=len(docs))

    return _fake


def test_single_day_overflow_subdivides_by_orgao_when_buckets_cover_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A single day over the ES cap is split by órgão, never truncated."""
    day = "2024-03-01"
    orgao_docs = {
        "1ª Câmara Cível": [_hit(i, dtjulgamento=day) for i in range(6_000)],
        "2ª Câmara Cível": [_hit(6_000 + i, dtjulgamento=day) for i in range(4_500)],
    }
    orgao_totals = {k: len(v) for k, v in orgao_docs.items()}
    day_total = sum(orgao_totals.values())
    fake_search = _fake_orgao_search(day, day_total, orgao_totals, orgao_docs)
    monkeypatch.setattr(crawler, "search", fake_search)
    monkeypatch.setattr(
        crawler,
        "get_aggregations",
        lambda fields=None: {  # noqa: ARG005
            "aggregations": {"orgaos_julgadores": {"buckets": [{"key": k} for k in orgao_totals]}}
        },
    )

    docs = fetch_tipo_window("SENTENÇA", day, day)

    assert len(docs) == day_total
    assert {d["id_documento"] for d in docs} == set(range(day_total))


def test_single_day_overflow_raises_when_no_orgao_buckets_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    day = "2024-03-01"
    fake_search = _fake_orgao_search(day, MAX_RESULT_WINDOW + 500, {}, {})
    monkeypatch.setattr(crawler, "search", fake_search)
    monkeypatch.setattr(crawler, "get_aggregations", lambda fields=None: {"aggregations": {}})  # noqa: ARG005

    with pytest.raises(JurisWindowOverflowError, match="no orgaos_julgadores buckets"):
        fetch_tipo_window("SENTENÇA", day, day)


def test_single_day_overflow_raises_when_an_orgao_bucket_itself_exceeds_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    day = "2024-03-01"
    orgao_totals = {"Vara Única": MAX_RESULT_WINDOW + 1}
    fake_search = _fake_orgao_search(day, MAX_RESULT_WINDOW + 1, orgao_totals, {})
    monkeypatch.setattr(crawler, "search", fake_search)
    monkeypatch.setattr(
        crawler,
        "get_aggregations",
        lambda fields=None: {  # noqa: ARG005
            "aggregations": {"orgaos_julgadores": {"buckets": [{"key": "Vara Única"}]}}
        },
    )

    with pytest.raises(JurisWindowOverflowError, match="no further subdivision axis"):
        fetch_tipo_window("SENTENÇA", day, day)


def test_single_day_overflow_raises_when_orgao_buckets_do_not_cover_the_total(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Buckets summing to less than the day total would silently drop documents — raise instead."""
    day = "2024-03-01"
    day_total = MAX_RESULT_WINDOW + 1_000
    orgao_totals = {"1ª Câmara Cível": 6_000}  # covers only 6,000 of day_total
    fake_search = _fake_orgao_search(day, day_total, orgao_totals, {})
    monkeypatch.setattr(crawler, "search", fake_search)
    monkeypatch.setattr(
        crawler,
        "get_aggregations",
        lambda fields=None: {  # noqa: ARG005
            "aggregations": {"orgaos_julgadores": {"buckets": [{"key": "1ª Câmara Cível"}]}}
        },
    )

    with pytest.raises(JurisWindowOverflowError, match="the remainder would be silently lost"):
        fetch_tipo_window("SENTENÇA", day, day)


def test_multi_day_window_with_gte_relation_splits_even_under_the_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 'gte' total on a multi-day window still bisects — the real total is unknown."""
    full = ("2024-03-01", "2024-03-02")
    left = ("2024-03-01", "2024-03-01")
    right = ("2024-03-02", "2024-03-02")
    windows = {
        left: {0: [_hit(1, dtjulgamento="2024-03-01")]},
        right: {0: [_hit(2, dtjulgamento="2024-03-02")]},
    }
    calls, fake = _fake_search_windows(windows)

    def _fake_with_gte_probe(*args: object, **kwargs: object) -> dict:
        date_start = kwargs.get("date_start")
        date_end = kwargs.get("date_end")
        if (date_start, date_end) == full:
            # value is comfortably under the cap, but relation says "at least"
            return {"hits": {"total": {"value": 5, "relation": "gte"}, "hits": []}}
        return fake(*args, **kwargs)

    monkeypatch.setattr(crawler, "search", _fake_with_gte_probe)

    docs = fetch_tipo_window("SENTENÇA", *full)

    assert [d["id_documento"] for d in docs] == [1, 2]
    full_pages = [c for c in calls if (c["start"], c["end"]) == full and c["size"] > 1]
    assert full_pages == []


def test_fetch_window_splits_when_total_exceeds_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """An oversized multi-day window is bisected instead of truncated."""
    full = ("2024-03-01", "2024-03-02")
    left = ("2024-03-01", "2024-03-01")
    right = ("2024-03-02", "2024-03-02")
    oversized = {f: [_hit(f + i) for i in range(PAGE_SIZE)] for f in range(0, 10_400, PAGE_SIZE)}
    windows = {
        full: oversized,  # probe sees total > MAX_RESULT_WINDOW
        left: {0: [_hit(1, dtjulgamento="2024-03-01")]},
        right: {0: [_hit(2, dtjulgamento="2024-03-02")]},
    }
    calls, fake = _fake_search_windows(windows)
    monkeypatch.setattr(crawler, "search", fake)

    docs = fetch_tipo_window("SENTENÇA", *full)

    assert [d["id_documento"] for d in docs] == [1, 2]
    # the oversized window is only probed (size=1), never paginated
    full_pages = [c for c in calls if (c["start"], c["end"]) == full and c["size"] > 1]
    assert full_pages == []


def test_fetch_window_supports_results_key_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """JURIS sometimes returns hits under a flat ``results`` key."""

    def _fake(
        tipo: str,
        from_: int = 0,
        size: int = PAGE_SIZE,
        texto: str = "",
        *,
        date_start: str | None = None,
        date_end: str | None = None,
        extra_fields: dict | None = None,
    ) -> dict:
        if size == 1:
            return {"hits": {"total": {"value": 2}, "hits": [_hit(1)]}}
        if from_ == 0:
            return {"results": [_hit(1), _hit(2)]}
        return {"results": []}

    monkeypatch.setattr(crawler, "search", _fake)
    docs = fetch_tipo_window("SENTENÇA", "2024-01-01", "2024-01-31")
    assert [d["id_documento"] for d in docs] == [1, 2]


# ── _fetch_pages page-level resume (cache_dir) ────────────────────────────


def test_partial_cache_path_unique_per_extra_fields(tmp_path: Path) -> None:
    """Bisected/órgão sub-windows sharing a date range must not collide."""
    p1 = _partial_cache_path(tmp_path, "ACÓRDÃO", "2024-01-01", "2024-01-01", None)
    p2 = _partial_cache_path(
        tmp_path, "ACÓRDÃO", "2024-01-01", "2024-01-01", {"ds_orgao_julgador.raw": ["A"]}
    )
    p3 = _partial_cache_path(
        tmp_path, "ACÓRDÃO", "2024-01-01", "2024-01-01", {"ds_orgao_julgador.raw": ["B"]}
    )
    assert len({p1, p2, p3}) == 3


def test_fetch_pages_deletes_cache_on_successful_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake(
        tipo: str,
        from_: int = 0,
        size: int = PAGE_SIZE,
        texto: str = "",
        *,
        date_start: str | None = None,
        date_end: str | None = None,
        extra_fields: dict | None = None,
    ) -> dict:
        if from_ == 0:
            return _es_response([_hit(1), _hit(2)])
        return _es_response([])

    monkeypatch.setattr(crawler, "search", _fake)
    docs = _fetch_pages("ACÓRDÃO", "2024-01-01", "2024-01-31", cache_dir=tmp_path)

    assert [d["id_documento"] for d in docs] == [1, 2]
    cache_path = _partial_cache_path(tmp_path, "ACÓRDÃO", "2024-01-01", "2024-01-31", None)
    assert not cache_path.exists()  # window PROVABLY complete — staging cleaned up


def test_fetch_pages_leaves_cache_behind_on_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure mid-window must leave whatever was fetched so far on disk —
    never silently discarded, never marked complete.
    """

    class _BoomError(RuntimeError):
        pass

    def _fake(
        tipo: str,
        from_: int = 0,
        size: int = PAGE_SIZE,
        texto: str = "",
        *,
        date_start: str | None = None,
        date_end: str | None = None,
        extra_fields: dict | None = None,
    ) -> dict:
        if from_ == 0:
            return _es_response([_hit(1)] * size)  # full page — loop continues
        msg = "simulated STIC block"
        raise _BoomError(msg)

    monkeypatch.setattr(crawler, "search", _fake)
    with pytest.raises(_BoomError):
        _fetch_pages("ACÓRDÃO", "2024-01-01", "2024-01-31", cache_dir=tmp_path)

    cache_path = _partial_cache_path(tmp_path, "ACÓRDÃO", "2024-01-01", "2024-01-31", None)
    cached = _load_partial_cache(cache_path)
    assert len(cached) == PAGE_SIZE  # exactly the one page that succeeded, not lost


def test_fetch_pages_resumes_from_partial_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second attempt picks up at from_=len(cached docs), not from_=0 —
    the earlier page is never re-fetched.
    """
    cache_path = _partial_cache_path(tmp_path, "ACÓRDÃO", "2024-01-01", "2024-01-31", None)
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text('{"id_documento": 1, "tipo": "ACÓRDÃO"}\n', encoding="utf-8")

    seen_from: list[int] = []

    def _fake(
        tipo: str,
        from_: int = 0,
        size: int = PAGE_SIZE,
        texto: str = "",
        *,
        date_start: str | None = None,
        date_end: str | None = None,
        extra_fields: dict | None = None,
    ) -> dict:
        seen_from.append(from_)
        if from_ == 1:
            return _es_response([_hit(2)])
        return _es_response([])

    monkeypatch.setattr(crawler, "search", _fake)
    docs = _fetch_pages("ACÓRDÃO", "2024-01-01", "2024-01-31", cache_dir=tmp_path)

    assert seen_from[0] == 1  # resumed, did not restart at 0
    assert [d["id_documento"] for d in docs] == [1, 2]
    assert not cache_path.exists()  # completed normally — cleaned up


# ── fetch_tipo_month ─────────────────────────────────────────────────────


def test_fetch_tipo_month_uses_month_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, str, str]] = []

    def _fake_window(
        tipo: str, date_start: str, date_end: str, cache_dir: object = None
    ) -> list[dict]:
        seen.append((tipo, date_start, date_end))
        return [{"id_documento": 5, "tipo": tipo}]

    monkeypatch.setattr(crawler, "fetch_tipo_window", _fake_window)

    docs = fetch_tipo_month("ACÓRDÃO", "2024-02")

    assert seen == [("ACÓRDÃO", "2024-02-01", "2024-02-29")]
    assert [d["id_documento"] for d in docs] == [5]


# ── _iter_year_months / crawl_all ────────────────────────────────────────


def test_iter_year_months_inclusive_range() -> None:
    assert list(_iter_year_months(2024, "2024-03")) == ["2024-01", "2024-02", "2024-03"]


def test_iter_year_months_crosses_year_boundary() -> None:
    got = list(_iter_year_months(2023, "2024-02"))
    assert got[0] == "2023-01"
    assert got[-1] == "2024-02"
    assert "2023-12" in got
    assert len(got) == 14


def test_crawl_all_fetches_each_tipo_month_once(monkeypatch: pytest.MonkeyPatch) -> None:
    fetched: list[tuple[str, str]] = []

    def _fake_month(tipo: str, year_month: str, cache_dir: object = None) -> list[dict]:
        fetched.append((tipo, year_month))
        if year_month == "2024-01":
            return [{"id_documento": 1, "tipo": tipo}]
        return []

    monkeypatch.setattr(crawler, "fetch_tipo_month", _fake_month)

    out = list(crawl_all(start_year=2024, end_year_month="2024-02", tipos=["ACÓRDÃO", "VOTO"]))

    assert fetched == [
        ("ACÓRDÃO", "2024-01"),
        ("ACÓRDÃO", "2024-02"),
        ("VOTO", "2024-01"),
        ("VOTO", "2024-02"),
    ]
    assert [(t, ym, len(docs)) for t, ym, docs in out] == [
        ("ACÓRDÃO", "2024-01", 1),
        ("ACÓRDÃO", "2024-02", 0),
        ("VOTO", "2024-01", 1),
        ("VOTO", "2024-02", 0),
    ]
