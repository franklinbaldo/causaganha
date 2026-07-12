"""Tests for tjro_juris.client — HTML cleaning, URL building, payload/HTTP error discipline.

Error discipline (CLAUDE.md): 403 and timeouts are transport failures and
must RAISE — they must never be interpreted as "no documents" (absent).
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import respx

from tjro_juris.client import ENDPOINT, PAGE_SIZE, clean_html, doc_url, get_aggregations, search


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


def test_search_wraps_tipo_in_list_and_returns_payload() -> None:
    """The JURIS backend crashes if ``tipo`` is a bare string — must be a list."""
    payload = {"hits": {"hits": [{"_source": {"id_processo_documento": 1}}]}}
    with respx.mock() as router:
        route = router.post(ENDPOINT).respond(200, json=payload)
        data = search("ACÓRDÃO", from_=400, size=PAGE_SIZE)

    assert data == payload
    body = json.loads(route.calls.last.request.content)
    assert body["tipo"] == ["ACÓRDÃO"]
    assert body["from"] == 400
    assert body["size"] == PAGE_SIZE
    assert body["texto"] == ""


def test_search_403_raises_never_returns_empty() -> None:
    """403 is rate-limiting/WAF — it must raise, never look like zero hits."""
    with respx.mock() as router:
        router.post(ENDPOINT).respond(403)
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            search("SENTENÇA")
    assert exc_info.value.response.status_code == 403


def test_search_timeout_propagates() -> None:
    with respx.mock() as router:
        router.post(ENDPOINT).mock(side_effect=httpx.ReadTimeout("timed out"))
        with pytest.raises(httpx.ReadTimeout):
            search("VOTO")


def test_search_500_raises() -> None:
    with respx.mock() as router:
        router.post(ENDPOINT).respond(500)
        with pytest.raises(httpx.HTTPStatusError):
            search("EMENTA")


# ── get_aggregations ─────────────────────────────────────────────────────


def test_get_aggregations_returns_json() -> None:
    with respx.mock() as router:
        router.get("https://juris-back.tjro.jus.br/search/agregacoes").respond(
            200, json={"tipos": {"ACÓRDÃO": 10}}
        )
        assert get_aggregations() == {"tipos": {"ACÓRDÃO": 10}}


def test_get_aggregations_403_raises() -> None:
    with respx.mock() as router:
        router.get("https://juris-back.tjro.jus.br/search/agregacoes").respond(403)
        with pytest.raises(httpx.HTTPStatusError):
            get_aggregations()
