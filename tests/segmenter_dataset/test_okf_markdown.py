"""Tests for the experimental OKF Markdown annotation container (issue #1049).

RFC 0012 §11's existing inline-tagged XML rendering (segmenter_dataset.store)
stays the canonical positional format — this module only swaps the *container*
around it (YAML frontmatter for identity/provenance + the same inline-tagged
body) and must preserve every invariant #1049 lists: no manual offsets,
byte-exact text reconstruction, deterministic conversion, lossless round trip,
and frontmatter carrying provenance untouched by the body encoding.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from segmenter_dataset.okf_markdown import (
    OkfMarkdownError,
    parse_annotated_body,
    parse_okf_markdown,
    render_annotated_body,
    render_okf_markdown,
)
from segmenter_dataset.schemas import Label


def test_render_annotated_body_wraps_single_anchor_inline() -> None:
    text = "Diante do exposto, JULGO PROCEDENTE o pedido."
    labels = [Label(start=19, end=35, category="resultado")]

    body = render_annotated_body(text, labels)

    assert body == 'Diante do exposto, <resultado ord="0">JULGO PROCEDENTE</resultado> o pedido.'


def test_render_annotated_body_nests_matched_pair_as_wrapper_plus_inicio_fim() -> None:
    text = "RELATÓRIO tudo bem. É o relatório. Resto."
    labels = [
        Label(start=0, end=9, category="relatorio_inicio"),
        Label(start=20, end=34, category="relatorio_fim"),
    ]

    body = render_annotated_body(text, labels)

    assert body == (
        '<relatorio><inicio ord="0">RELATÓRIO</inicio> tudo bem. '
        '<fim ord="1">É o relatório.</fim></relatorio> Resto.'
    )


def test_parse_annotated_body_is_inverse_of_render_for_single_anchor() -> None:
    text = "Diante do exposto, JULGO PROCEDENTE o pedido."
    labels = [Label(start=19, end=35, category="resultado")]

    body = render_annotated_body(text, labels)
    recovered_text, recovered_labels = parse_annotated_body(body)

    assert recovered_text == text
    assert recovered_labels == labels


def test_parse_annotated_body_is_inverse_of_render_for_matched_pair() -> None:
    text = "RELATÓRIO tudo bem. É o relatório. Resto."
    labels = [
        Label(start=0, end=9, category="relatorio_inicio"),
        Label(start=20, end=35, category="relatorio_fim"),
    ]

    body = render_annotated_body(text, labels)
    recovered_text, recovered_labels = parse_annotated_body(body)

    assert recovered_text == text
    assert recovered_labels == labels


def test_round_trip_preserves_single_anchor_nested_inside_a_region() -> None:
    """A structural region (cabecalho) legitimately contains another anchor (ref_processual)."""
    text = "CABEÇALHO Processo n. 0000010-11.2024.8.22.0001 texto. Fim do cabeçalho aqui."
    labels = [
        Label(start=0, end=9, category="cabecalho_inicio"),
        Label(start=10, end=48, category="ref_processual"),
        Label(start=55, end=77, category="cabecalho_fim"),
    ]

    body = render_annotated_body(text, labels)
    recovered_text, recovered_labels = parse_annotated_body(body)

    assert recovered_text == text
    assert sorted(recovered_labels, key=lambda label: label.start) == sorted(
        labels, key=lambda label: label.start
    )


def test_round_trip_preserves_unmatched_dangling_inicio_without_fabricating_a_fim() -> None:
    """RFC 0012 §11: an unmatched pair is representable, never invented a closing cue."""
    text = "Texto anterior. CUSTAS pelo vencido, sem mais delongas ate o fim do documento."
    labels = [Label(start=16, end=23, category="custas_inicio")]

    body = render_annotated_body(text, labels)
    recovered_text, recovered_labels = parse_annotated_body(body)

    assert recovered_text == text
    assert recovered_labels == labels


def test_parse_annotated_body_rejects_malformed_markup() -> None:
    with pytest.raises(OkfMarkdownError):
        parse_annotated_body("<resultado>JULGO PROCEDENTE<resultado>")


def test_render_okf_markdown_puts_provenance_in_frontmatter_and_tags_in_body() -> None:
    text = "Diante do exposto, JULGO PROCEDENTE o pedido."
    labels = [Label(start=19, end=35, category="resultado")]
    frontmatter = {
        "type": "segmenter_annotation",
        "document_id": "doc-123",
        "ontology": "segmenter-ontology-v8.0.0",
        "annotator": "llm_technique1:batch1",
    }

    markdown = render_okf_markdown(frontmatter, text, labels)

    assert markdown.startswith("---\n")
    assert "document_id: doc-123" in markdown
    assert "<resultado" in markdown
    # Inline tags stay in the body, never mirrored into frontmatter as offsets.
    assert "start:" not in markdown
    assert "end:" not in markdown


def test_okf_markdown_round_trips_frontmatter_and_body_without_drift() -> None:
    text = "RELATÓRIO tudo bem. É o relatório. Resto."
    labels = [
        Label(start=0, end=9, category="relatorio_inicio"),
        Label(start=20, end=35, category="relatorio_fim"),
    ]
    frontmatter = {
        "type": "segmenter_annotation",
        "document_id": "doc-456",
        "ontology": "segmenter-ontology-v8.0.0",
        "guideline": "segmenter_v7.1",
        "annotator": "llm_technique1:batch1",
    }

    markdown = render_okf_markdown(frontmatter, text, labels)
    recovered_frontmatter, recovered_text, recovered_labels = parse_okf_markdown(
        markdown, path=Path("doc-456.md")
    )

    assert recovered_frontmatter == frontmatter
    assert recovered_text == text
    assert recovered_labels == labels


def test_okf_markdown_uses_the_real_okf_parser_contract(tmp_path: Path) -> None:
    """Confirms the actual okf-parser frontmatter/body split (#1049 invariant), not a bespoke one."""
    from okf_parser.parser import parse_document_text

    text = "Diante do exposto, JULGO PROCEDENTE o pedido."
    labels = [Label(start=19, end=35, category="resultado")]
    frontmatter = {"type": "segmenter_annotation", "document_id": "doc-789"}

    markdown = render_okf_markdown(frontmatter, text, labels)
    parsed = parse_document_text(tmp_path / "doc-789.md", markdown)

    assert parsed.frontmatter["document_id"] == "doc-789"
    recovered_text, recovered_labels = parse_annotated_body(parsed.body)
    assert recovered_text == text
    assert recovered_labels == labels
