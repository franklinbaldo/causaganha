"""Tests for tjro_juris.client — HTML cleaning, URL building, payload/HTTP error discipline.

Error discipline (CLAUDE.md): 403 and timeouts are transport failures and
must RAISE — they must never be interpreted as "no documents" (absent).

Contract (2026-07): filters are nested under ``fields`` with ES ``.raw``
keyword subfields; free text is ``fields.query``; aggregations are POST.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from tjro_juris import client as client_mod
from tjro_juris.client import (
    AGGREGATIONS_ENDPOINT,
    ENDPOINT,
    MAX_ATTEMPTS,
    PAGE_SIZE,
    JurisBlockedError,
    clean_html,
    doc_url,
    get_aggregations,
    search,
)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Retry backoff must never actually sleep during tests."""
    monkeypatch.setattr(client_mod, "_sleep", lambda _s: None)


# ── clean_html ───────────────────────────────────────────────────────────


def test_clean_html_empty_input() -> None:
    assert clean_html("") == ""


def test_clean_html_strips_tags_and_collapses_whitespace() -> None:
    html = "<p>EMENTA:   Apelação\n<b>cível</b>.</p>"
    assert clean_html(html) == "EMENTA: Apelação cível ."


def test_clean_html_removes_img_style_and_script_blocks() -> None:
    html = (
        '<img src="data:image/png;base64,AAAA">'
        "<style>.x { color: red; }</style>"
        "<script>alert('x')</script>"
        "<div>texto util</div>"
    )
    assert clean_html(html) == "texto util"


def test_clean_html_decodes_entities() -> None:
    assert clean_html("Ju&iacute;zo &amp; partes") == "Juízo & partes"


# ── doc_url ──────────────────────────────────────────────────────────────


def test_doc_url_none_id_returns_empty() -> None:
    assert doc_url(None) == ""


def test_doc_url_builds_all_query_params() -> None:
    url = doc_url(
        123,
        sistema_origem="pje2instancia",
        tipo="ACÓRDÃO",
        id_documento_principal=456,
    )
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert parsed.scheme == "https"
    assert params["id"] == ["123"]
    assert params["sistema_origem"] == ["pje2instancia"]
    assert params["tipo"] == ["ACÓRDÃO"]
    assert params["id_documento_principal"] == ["456"]


def test_doc_url_omits_empty_optional_params() -> None:
    url = doc_url("789")
    params = parse_qs(urlparse(url).query)
    assert params == {"id": ["789"]}


# ── search ───────────────────────────────────────────────────────────────


def test_search_sends_tipo_raw_list_under_fields() -> None:
    """The tipo goes to ``fields["tipo.raw"]`` and MUST be wrapped in a list."""
    payload = {"hits": {"hits": [{"_source": {"id_processo_documento": 1}}]}}
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=payload)
        data = search("ACÓRDÃO", from_=400, size=PAGE_SIZE)

    assert data == payload
    body = json.loads(route.calls.last.request.content)
    assert body["fields"]["tipo.raw"] == ["ACÓRDÃO"]
    assert body["from"] == 400
    assert body["size"] == PAGE_SIZE
    assert body["sort"] == [
        {"dtjulgamento": "desc"},
        {"_score": "desc"},
        {"id_processo_documento": "asc"},
    ]
    # top-level legacy keys must be gone — they now crash the server (500)
    assert "tipo" not in body
    assert "texto" not in body
    assert "token" not in body


def test_search_omits_empty_optional_fields() -> None:
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json={"hits": {"hits": []}})
        search("VOTO")

    body = json.loads(route.calls.last.request.content)
    assert body["fields"] == {"tipo.raw": ["VOTO"]}


def test_search_maps_texto_to_query_field() -> None:
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json={"hits": {"hits": []}})
        search("SENTENÇA", texto="improbidade administrativa")

    body = json.loads(route.calls.last.request.content)
    assert body["fields"]["query"] == "improbidade administrativa"


def test_search_maps_date_window_to_dtjulgamento_fields() -> None:
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json={"hits": {"hits": []}})
        search("EMENTA", date_start="2026-06-01", date_end="2026-06-30")

    body = json.loads(route.calls.last.request.content)
    assert body["fields"]["dtjulgamento_inicio"] == "2026-06-01"
    assert body["fields"]["dtjulgamento_fim"] == "2026-06-30"


def test_search_403_raises_immediately_never_retried() -> None:
    """403 is rate-limiting/WAF — raises on the FIRST attempt, never retried, never absent."""
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(403)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            search("SENTENÇA")
    assert exc_info.value.response.status_code == 403
    assert route.call_count == 1


def test_search_raises_juris_blocked_error_on_stic_block_page() -> None:
    """A 200 carrying TJRO's STIC block page (not JSON) must raise a clear,
    diagnosable error instead of an opaque JSONDecodeError — and never retry,
    since the block is IP-level, not a transient blip.
    """
    block_page = (
        '<!DOCTYPE html><html lang="pt-br"><head>'
        "<title>STIC - Página Bloqueada</title></head><body></body></html>"
    )
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, html=block_page)
        with pytest.raises(JurisBlockedError):
            search("ACÓRDÃO")
    assert route.call_count == 1


def test_search_extra_fields_merged_into_fields() -> None:
    """``extra_fields`` (used to slice by órgão julgador) merges into ``fields``."""
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json={"hits": {"hits": []}})
        search("ACÓRDÃO", extra_fields={"ds_orgao_julgador.raw": ["1ª Câmara Cível"]})

    body = json.loads(route.calls.last.request.content)
    assert body["fields"]["ds_orgao_julgador.raw"] == ["1ª Câmara Cível"]
    assert body["fields"]["tipo.raw"] == ["ACÓRDÃO"]


def test_search_retries_transport_error_then_succeeds() -> None:
    """A transient connect timeout is retried; a later success is returned."""
    payload = {"hits": {"hits": [{"_source": {"id_processo_documento": 1}}]}}
    with respx.mock() as router:
        route = router.post(ENDPOINT)
        route.side_effect = [
            httpx.ConnectTimeout("timed out"),
            httpx.ConnectTimeout("timed out"),
            httpx.Response(200, json=payload),
        ]
        data = search("VOTO")
    assert data == payload
    assert route.call_count == 3


def test_search_persistent_transport_error_raises_after_max_attempts() -> None:
    with respx.mock() as router:
        route = router.post(ENDPOINT).mock(side_effect=httpx.ConnectTimeout("timed out"))
        with pytest.raises(httpx.ConnectTimeout):
            search("VOTO")
    assert route.call_count == MAX_ATTEMPTS


def test_search_retries_5xx_then_succeeds() -> None:
    payload = {"hits": {"hits": []}}
    with respx.mock() as router:
        route = router.post(ENDPOINT)
        route.side_effect = [httpx.Response(500), httpx.Response(200, json=payload)]
        data = search("EMENTA")
    assert data == payload
    assert route.call_count == 2


def test_search_persistent_500_raises_after_max_attempts() -> None:
    """Persistent 5xx still raises — the original contract-break symptom."""
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(500)
        with pytest.raises(httpx.HTTPStatusError):
            search("EMENTA")
    assert route.call_count == MAX_ATTEMPTS


# ── get_aggregations ─────────────────────────────────────────────────────


def test_get_aggregations_posts_fields_body() -> None:
    """Aggregations moved to POST (GET now returns 405)."""
    payload = {"aggregations": {"tipos_documentos": {"buckets": []}}}
    with respx.mock() as router:
        route = router.post(AGGREGATIONS_ENDPOINT).respond(200, json=payload)
        assert get_aggregations() == payload

    body = json.loads(route.calls.last.request.content)
    assert body == {"fields": {}}


def test_get_aggregations_narrows_by_fields() -> None:
    with respx.mock() as router:
        route = router.post(AGGREGATIONS_ENDPOINT).respond(200, json={"aggregations": {}})
        get_aggregations({"tipo.raw": ["VOTO"]})

    body = json.loads(route.calls.last.request.content)
    assert body == {"fields": {"tipo.raw": ["VOTO"]}}


def test_get_aggregations_403_raises_immediately() -> None:
    with respx.mock() as router:
        route = router.post(AGGREGATIONS_ENDPOINT).respond(403)
        with pytest.raises(httpx.HTTPStatusError):
            get_aggregations()
    assert route.call_count == 1
