"""Cheap heuristics to find rare-category training candidates (#1050).

#1050 asks to mine **real** candidate documents for rare categories
(``preliminar``, ``honorarios``, ``custas``, ``voto``, ``acordao_decisorio``)
using cheap target heuristics "only to find likely documents" — the
resulting hits must never become labels themselves. This module is
deliberately a pure text-substring/regex triage layer, entirely separate
from :mod:`segmenter_dataset.mechanical` (structural label validation) and
from actual annotation: a positive hit means "worth an annotator's time",
nothing about position, category correctness, or ground truth.

Keyword choice trades precision for recall on purpose — a maintainer
reviewing a false-positive candidate costs little, while a false negative
means a genuine rare-category document is never surfaced for annotation.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING, Protocol


if TYPE_CHECKING:
    from collections.abc import Iterable


class _TextDocument(Protocol):
    """The only two fields this module needs from a document-like object.

    Deliberately a narrower shape than :class:`segmenter_dataset.schemas.DocumentRecord`
    so this module stays a standalone triage tool, not coupled to the full
    dataset-lifecycle schema.
    """

    document_id: str
    text: str


RARE_CATEGORIES: frozenset[str] = frozenset(
    {"preliminar", "honorarios", "custas", "voto", "acordao_decisorio"}
)

# Patterns are matched against text already normalized by ``_normalize``
# (lowercased, accents stripped), so every pattern below is itself
# lowercase and unaccented.
_CATEGORY_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "preliminar": tuple(
        re.compile(pattern)
        for pattern in (
            r"preliminarmente",
            r"preliminar(?:es)? (?:de|arguid|suscitad|levantad)",
            r"questao prejudicial",
            r"prejudicial de merito",
        )
    ),
    "honorarios": tuple(
        re.compile(pattern)
        for pattern in (
            r"honorarios advocaticios",
            r"honorarios de sucumbencia",
            r"verba honoraria",
        )
    ),
    "custas": tuple(
        re.compile(pattern)
        for pattern in (
            r"custas processuais",
            r"custas judiciais",
            r"isento(?:s)? de custas",
        )
    ),
    "voto": tuple(
        re.compile(pattern)
        for pattern in (
            r"voto do relator",
            r"voto[:.]",
            r"acompanho o relator",
            r"peco venia",
            r"divirjo do relator",
        )
    ),
    "acordao_decisorio": tuple(
        re.compile(pattern)
        for pattern in (
            r"\bacordam\b",
            r"a unanimidade de votos",
            r"por unanimidade",
            r"vistos, relatados e discutidos",
        )
    ),
}


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.lower()


def find_rare_category_hints(
    text: str, *, categories: frozenset[str] = RARE_CATEGORIES
) -> frozenset[str]:
    """Return which of *categories* have a cheap heuristic cue in *text*.

    A hit is a weak, recall-oriented signal that the document is worth an
    annotator's attention for that category — never a claim that the
    category is actually present, and never a span/position.
    """
    normalized = _normalize(text)
    hits = {
        category
        for category in categories
        for pattern in _CATEGORY_PATTERNS.get(category, ())
        if pattern.search(normalized)
    }
    return frozenset(hits)


def mine_rare_category_candidates(
    documents: Iterable[_TextDocument],
    *,
    categories: frozenset[str] = RARE_CATEGORIES,
) -> dict[str, tuple[str, ...]]:
    """Bucket ``document_id`` by rare-category heuristic hit.

    A document with hits for more than one category is listed under every
    matching category. Categories with no hits across *documents* are
    absent from the result rather than mapped to an empty tuple. Document
    IDs within a category are sorted for a deterministic, diffable report.
    """
    by_category: dict[str, list[str]] = {}
    for document in documents:
        for category in find_rare_category_hints(document.text, categories=categories):
            by_category.setdefault(category, []).append(document.document_id)
    return {category: tuple(sorted(ids)) for category, ids in by_category.items()}
