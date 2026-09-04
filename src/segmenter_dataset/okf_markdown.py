"""Experimental OKF Markdown container for segmenter annotations (issue #1049).

RFC 0012 §11's inline-tagged XML (see ``segmenter_dataset.store``'s module
docstring) stays the canonical way to express *positions*: a label is a real
tag wrapping its own span text, so an LLM/human never has to compute or report
integer offsets, and a matched ``_inicio``/``_fim`` pair nests under a
``<base>`` wrapper with generic ``<inicio>``/``<fim>`` children. This module
does not replace any of that — it only offers an alternative *container*
around the same inline-tagged body: YAML frontmatter (identity, provenance,
ontology/guideline versions, annotator lineage) followed by the body, instead
of a full XML file with metadata as sibling elements.

Per #1049's decision rule, this is an experiment: adopt only if it preserves
every current validation guarantee and materially simplifies provenance/bundle
tooling; otherwise keep the existing XML artifact format. This module commits
to none of that on its own — it is the round-trip machinery the decision needs
to be made on evidence.

The body's inline-tag rendering itself is deliberately not reimplemented here:
:func:`render_annotated_body`/:func:`parse_annotated_body` delegate to
``segmenter_dataset.store``'s own ``_labels_to_text_element``/
``_text_element_to_labels`` (already reused the same way by
``scripts/ingest_juris_technique1_batch.py``), so both containers always agree
on what "the same annotation" looks like as inline tags.

Frontmatter is parsed with the real ``okf-parser`` contract
(``okf_parser.parser.parse_document_text``), not a bespoke splitter — #1049
explicitly asks to confirm that contract before adopting any schema built on
top of it.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

import yaml
from okf_parser.parser import parse_document_text

from segmenter_dataset.store import _labels_to_text_element, _text_element_to_labels


if TYPE_CHECKING:
    from segmenter_dataset.schemas import Label


_BODY_ROOT_TAG = "text"
_IN_MEMORY_PATH = Path("<okf-markdown>")


class OkfMarkdownError(ValueError):
    """The annotated body is not well-formed inline-tagged markup."""


def render_annotated_body(text: str, labels: list[Label]) -> str:
    """Render ``text`` with ``labels`` inlined as tags, deterministically.

    Reuses ``segmenter_dataset.store``'s render tree
    (:func:`~segmenter_dataset.store._labels_to_text_element`) so the body
    matches, tag-for-tag, what the existing XML document/annotation/review
    files already encode — only the surrounding container changes, never the
    positional scheme.
    """
    root = _labels_to_text_element(_BODY_ROOT_TAG, text, labels)
    chunks = [root.text or ""]
    chunks.extend(ET.tostring(child, encoding="unicode") for child in root)
    return "".join(chunks)


def parse_annotated_body(body: str) -> tuple[str, list[Label]]:
    """Inverse of :func:`render_annotated_body`: recover exact text and offset labels."""
    try:
        root = ET.fromstring(f"<{_BODY_ROOT_TAG}>{body}</{_BODY_ROOT_TAG}>")  # noqa: S314
    except ET.ParseError as exc:
        message = f"annotated body is not well-formed inline-tagged markup: {exc}"
        raise OkfMarkdownError(message) from exc
    return _text_element_to_labels(root)


def render_okf_markdown(frontmatter: dict[str, object], text: str, labels: list[Label]) -> str:
    """Render one OKF Markdown document: YAML frontmatter + inline-tagged body.

    Frontmatter carries identity/provenance/relations (#1049's "narrower
    idea"); the inline tags in the body remain the sole positional source of
    truth — no offsets are ever mirrored into the frontmatter.
    """
    yaml_block = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).rstrip("\n")
    body = render_annotated_body(text, labels)
    return f"---\n{yaml_block}\n---\n{body}"


def parse_okf_markdown(
    markdown_text: str, *, path: Path = _IN_MEMORY_PATH
) -> tuple[dict[str, object], str, list[Label]]:
    """Inverse of :func:`render_okf_markdown`, via the real ``okf-parser`` frontmatter split."""
    parsed = parse_document_text(path, markdown_text)
    text, labels = parse_annotated_body(parsed.body)
    return dict(parsed.frontmatter), text, labels
