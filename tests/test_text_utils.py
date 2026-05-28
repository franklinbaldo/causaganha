"""Tests for text_utils.strip_html and is_html."""

from __future__ import annotations

from causaganha.analysis.text_utils import is_html, strip_html


def test_plain_text_passthrough() -> None:
    text = "Ante o exposto, julgo procedente o pedido."
    assert strip_html(text) == text


def test_strips_basic_tags() -> None:
    html = "<p>Ante o exposto, <strong>JULGO PROCEDENTE</strong> o pedido.</p>"
    result = strip_html(html)
    assert result == "Ante o exposto, JULGO PROCEDENTE o pedido."


def test_decodes_named_entities() -> None:
    result = strip_html("Custas ao r&eacute;u.")
    assert "réu" in result


def test_decodes_numeric_entities() -> None:
    result = strip_html("Processo n&#186; 1234.")
    assert "1234" in result


def test_collapses_whitespace() -> None:
    result = strip_html("<p>Linha 1</p>\n\n<p>Linha 2</p>")
    assert "\n" not in result
    assert "  " not in result


def test_br_tag_becomes_space() -> None:
    result = strip_html("Linha 1<br/>Linha 2")
    assert "Linha 1" in result
    assert "Linha 2" in result


def test_real_html_decision() -> None:
    html = (
        "<div class='decisao'>"
        "<p>Ante o exposto, <b>JULGO IMPROCEDENTE</b> o pedido formulado pelo autor.</p>"
        "<p>Custas ao autor. Honor&aacute;rios fixados em 10%.</p>"
        "</div>"
    )
    result = strip_html(html)
    assert "JULGO IMPROCEDENTE" in result
    assert "Honorários" in result
    assert "<" not in result


def test_is_html_detects_tags() -> None:
    assert is_html("<p>texto</p>") is True
    assert is_html("texto simples") is False
    assert is_html("<br/>") is True
