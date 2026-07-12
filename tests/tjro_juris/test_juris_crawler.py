"""Tests for tjro_juris.crawler — field extraction, windowed pagination, splitting."""

from __future__ import annotations

import time

import pytest

from tjro_juris import crawler
from tjro_juris.client import MAX_RESULT_WINDOW, PAGE_SIZE
from tjro_juris.crawler import (
    _extract_doc,
    _iter_year_months,
    _month_bounds,
    _split_range,
    crawl_all,
    fetch_tipo_month,
    fetch_tipo_window,
)


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
    ) -> dict:
        calls.append(
            {"tipo": tipo, "from_": from_, "size": size, "start": date_start, "end": date_end}
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


def test_fetch_window_never_exceeds_result_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Page requests must keep from_ + size <= MAX_RESULT_WINDOW (server 500s past it)."""
    window = ("2024-03-01", "2024-03-01")  # single day: cannot split further
    pages = {f: [_hit(f + i) for i in range(PAGE_SIZE)] for f in range(0, 12_000, PAGE_SIZE)}
    calls, fake = _fake_search_windows({window: pages})
    monkeypatch.setattr(crawler, "search", fake)

    docs = fetch_tipo_window("SENTENÇA", *window)

    assert len(docs) == MAX_RESULT_WINDOW  # truncated at the window cap
    page_calls = [c for c in calls if c["size"] > 1]
    assert all(c["from_"] + c["size"] <= MAX_RESULT_WINDOW for c in page_calls)


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
    ) -> dict:
        if size == 1:
            return {"hits": {"total": {"value": 2}, "hits": [_hit(1)]}}
        if from_ == 0:
            return {"results": [_hit(1), _hit(2)]}
        return {"results": []}

    monkeypatch.setattr(crawler, "search", _fake)
    docs = fetch_tipo_window("SENTENÇA", "2024-01-01", "2024-01-31")
    assert [d["id_documento"] for d in docs] == [1, 2]


# ── fetch_tipo_month ─────────────────────────────────────────────────────


def test_fetch_tipo_month_uses_month_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, str, str]] = []

    def _fake_window(tipo: str, date_start: str, date_end: str) -> list[dict]:
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

    def _fake_month(tipo: str, year_month: str) -> list[dict]:
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
