"""Tests for tjro_juris.crawler — field extraction, pagination, stop condition."""

from __future__ import annotations

import time

import pytest

from tjro_juris import crawler
from tjro_juris.client import PAGE_SIZE
from tjro_juris.crawler import (
    _extract_doc,
    _iter_year_months,
    crawl_all,
    crawl_tipo_by_month,
    fetch_tipo_all,
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


# ── fetch_tipo_all (pagination + stop condition) ─────────────────────────


def _fake_search_pages(pages: dict[int, list[dict]]) -> tuple[list[dict], object]:
    """Build a fake ``search`` returning canned pages keyed by ``from_``."""
    calls: list[dict] = []

    def _fake(tipo: str, from_: int = 0, size: int = PAGE_SIZE, texto: str = "") -> dict:
        calls.append({"tipo": tipo, "from_": from_, "size": size})
        return {"hits": {"hits": pages.get(from_, [])}}

    return calls, _fake


def test_fetch_stops_on_short_page(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        0: [_hit(i) for i in range(PAGE_SIZE)],
        PAGE_SIZE: [_hit(PAGE_SIZE + i) for i in range(3)],
    }
    calls, fake = _fake_search_pages(pages)
    monkeypatch.setattr(crawler, "search", fake)

    docs = fetch_tipo_all("ACÓRDÃO")

    assert len(docs) == PAGE_SIZE + 3
    assert [c["from_"] for c in calls] == [0, PAGE_SIZE]  # no third request


def test_fetch_stops_on_empty_first_page(monkeypatch: pytest.MonkeyPatch) -> None:
    calls, fake = _fake_search_pages({})
    monkeypatch.setattr(crawler, "search", fake)

    assert fetch_tipo_all("VOTO") == []
    assert len(calls) == 1


def test_fetch_full_page_then_empty_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """A page of exactly PAGE_SIZE forces one more request; the empty page ends it."""
    pages = {0: [_hit(i) for i in range(PAGE_SIZE)]}
    calls, fake = _fake_search_pages(pages)
    monkeypatch.setattr(crawler, "search", fake)

    docs = fetch_tipo_all("EMENTA")

    assert len(docs) == PAGE_SIZE
    assert [c["from_"] for c in calls] == [0, PAGE_SIZE]


def test_fetch_supports_results_key_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """JURIS sometimes returns hits under a flat ``results`` key."""

    def _fake(tipo: str, from_: int = 0, size: int = PAGE_SIZE, texto: str = "") -> dict:
        if from_ == 0:
            return {"results": [_hit(1), _hit(2)]}
        return {"results": []}

    monkeypatch.setattr(crawler, "search", _fake)
    docs = fetch_tipo_all("SENTENÇA")
    assert [d["id_documento"] for d in docs] == [1, 2]


# ── crawl_tipo_by_month ──────────────────────────────────────────────────


def test_crawl_tipo_by_month_buckets_by_year_month(monkeypatch: pytest.MonkeyPatch) -> None:
    hits = [
        _hit(1, dtjulgamento="2024-03-15"),
        _hit(2, dtjulgamento="2024-03-20"),
        _hit(3, dtjulgamento="2024-04-01"),
        _hit(4, dtjulgamento=""),  # dateless docs are dropped from buckets
    ]
    _calls, fake = _fake_search_pages({0: hits})
    monkeypatch.setattr(crawler, "search", fake)

    buckets = crawl_tipo_by_month("ACÓRDÃO")

    assert sorted(buckets) == ["2024-03", "2024-04"]
    assert [d["id_documento"] for d in buckets["2024-03"]] == [1, 2]
    assert [d["id_documento"] for d in buckets["2024-04"]] == [3]


# ── _iter_year_months / crawl_all ────────────────────────────────────────


def test_iter_year_months_inclusive_range() -> None:
    assert list(_iter_year_months(2024, "2024-03")) == ["2024-01", "2024-02", "2024-03"]


def test_iter_year_months_crosses_year_boundary() -> None:
    got = list(_iter_year_months(2023, "2024-02"))
    assert got[0] == "2023-01"
    assert got[-1] == "2024-02"
    assert "2023-12" in got
    assert len(got) == 14


def test_crawl_all_fetches_each_tipo_once(monkeypatch: pytest.MonkeyPatch) -> None:
    fetched: list[str] = []

    def _fake_buckets(tipo: str) -> dict[str, list[dict]]:
        fetched.append(tipo)
        return {"2024-01": [{"id_documento": 1, "tipo": tipo}]}

    monkeypatch.setattr(crawler, "crawl_tipo_by_month", _fake_buckets)

    out = list(crawl_all(start_year=2024, end_year_month="2024-02", tipos=["ACÓRDÃO", "VOTO"]))

    assert fetched == ["ACÓRDÃO", "VOTO"]  # one sweep per tipo, not per month
    # 2 tipos x 2 months
    assert [(t, ym, len(docs)) for t, ym, docs in out] == [
        ("ACÓRDÃO", "2024-01", 1),
        ("ACÓRDÃO", "2024-02", 0),
        ("VOTO", "2024-01", 1),
        ("VOTO", "2024-02", 0),
    ]
