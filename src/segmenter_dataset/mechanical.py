"""Mechanical validation (RFC 0012 §11).

Deliberately separate from annotation-quality review (RFC 0012 §3.2): every
check here is a syntactic/structural property of a ``(text, labels)`` pair —
offsets, pairing, ontology membership — never a judgment about whether a
label is the *correct* one. Runs in-process, never via repeated subprocess
calls to an external validator (§11).

Adapted from PR #832's ``scripts/synthetic_segmenter/transform.py``
(``check_final_invariants``) and ``validators.py`` (pair/ontology checks) —
see RFC 0012 §18. The pair-base derivation here is generalized to read
``_inicio``/``_fim`` suffixes off whatever categories are actually present,
rather than a hardcoded tuple, so it doesn't silently go stale if the
ontology changes.

**Known limitation inherited from #832, not newly closed by this module:**
``validate_pairs`` below pairs ``_inicio``/``_fim`` occurrences by sorted
start offset (``zip`` over two independently sorted lists), exactly as
#832's original algorithm did. This is blind to a real inversion when spans
interleave — e.g. ``_inicio`` at offsets ``[10, 20]`` and ``_fim`` at
``[15, 100]`` reads as two "valid" pairs (10→15, 20→100) even if the true
document-order pairing is 20→15 (an inverted, invalid pair). Detecting that
correctly requires pairing by nesting depth (a stack, matching each
``_fim`` to the most recently opened unmatched ``_inicio``), which this
module does not implement. Treat this as an open gap, not a solved problem.
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from segmenter_dataset.schemas import Label


_INICIO_SUFFIX = "_inicio"
_FIM_SUFFIX = "_fim"


def check_final_invariants(text: str, labels: list[Label]) -> list[str]:
    """Offset-bound and overlap checks (RFC 0012 §11).

    ``0 <= start < end <= len(text)``, no overlapping spans. Pydantic
    already enforces ``start < end`` per-label (``schemas.Label``); this
    additionally checks the bound against ``text`` and cross-label overlap,
    which a single label can't self-validate.
    """
    problems: list[str] = []
    text_len = len(text)
    ordered = sorted(labels, key=lambda label: (label.start, label.end))
    prev_end = -1
    for label in ordered:
        if label.end > text_len:
            problems.append(f"[{label.category}] end={label.end} exceeds text length {text_len}")
            continue
        if label.start < prev_end:
            problems.append(
                f"[{label.category}] overlaps previous span "
                f"(start={label.start} < prev_end={prev_end})"
            )
        prev_end = max(prev_end, label.end)
    return problems


def _pair_bases(labels: list[Label]) -> set[str]:
    """Every ``_inicio``/``_fim`` base name actually present in ``labels``."""
    bases: set[str] = set()
    for label in labels:
        if label.category.endswith(_INICIO_SUFFIX):
            bases.add(label.category[: -len(_INICIO_SUFFIX)])
        elif label.category.endswith(_FIM_SUFFIX):
            bases.add(label.category[: -len(_FIM_SUFFIX)])
    return bases


def validate_pairs(
    labels: list[Label],
    *,
    allowed_unmatched: dict[str, str] | None = None,
    declared_unmatched: bool = False,
) -> list[str]:
    """Pair-balance checks (RFC 0012 §11).

    Catches: orphaned/excess ``_fim`` (no matching ``_inicio``), unbalanced
    counts beyond the single-dangling-``_inicio`` case, and inverted pairs
    (a ``_fim`` at or before its own ``_inicio``) *when pairing by sorted
    start offset happens to line them up* — see the module docstring's
    "known limitation inherited from #832" note: interleaved spans
    (``_inicio`` at ``[10, 20]``, ``_fim`` at ``[15, 100]``) are not
    detected as inverted, because sorted-offset ``zip`` pairs 10→15 and
    20→100 instead of the true nesting-order pairing.

    ``allowed_unmatched`` (a reason keyed by pair base, e.g.
    ``{"cabecalho": "document ends after the opening anchor"}``) is the
    real, per-record mechanism: a base is only excused from the "unmatched
    pair with no declared reason" problem if it's a key in this dict, so one
    base's excusal can never blanket-authorize an unrelated dangling pair.
    ``declared_unmatched`` remains for backwards-compatible callers that
    pass a single blanket boolean instead (§11: "_inicio sem par exige razão
    explícita de allowed-unmatched").
    """
    problems: list[str] = []
    unmatched_bases_in_text: set[str] = set()

    for base in sorted(_pair_bases(labels)):
        inicio_starts = sorted(
            label.start for label in labels if label.category == f"{base}{_INICIO_SUFFIX}"
        )
        fim_starts = sorted(
            label.start for label in labels if label.category == f"{base}{_FIM_SUFFIX}"
        )
        n_inicio, n_fim = len(inicio_starts), len(fim_starts)

        if n_fim > n_inicio:
            problems.append(
                f"{base}: {n_fim} _fim label(s) but only {n_inicio} _inicio label(s) — "
                "orphaned or excess _fim"
            )
        elif n_inicio - n_fim > 1:
            problems.append(
                f"{base}: {n_inicio} _inicio label(s) vs {n_fim} _fim label(s) — unbalanced "
                "beyond the single-dangling-_inicio case"
            )
        elif n_inicio - n_fim == 1:
            unmatched_bases_in_text.add(base)

        for inicio_start, fim_start in zip(inicio_starts, fim_starts, strict=False):
            if fim_start <= inicio_start:
                problems.append(
                    f"{base}: _fim at offset {fim_start} is not after its _inicio at "
                    f"offset {inicio_start} — inverted pair"
                )
                break

    allowed_bases = (
        unmatched_bases_in_text if allowed_unmatched is None and declared_unmatched else set()
    )
    if allowed_unmatched is not None:
        allowed_bases = set(allowed_unmatched)

    missing_reasons = unmatched_bases_in_text - allowed_bases
    extra_reasons = allowed_bases - unmatched_bases_in_text
    if missing_reasons:
        problems.append(
            f"record has unmatched pair(s) {sorted(missing_reasons)} but no "
            "declared allowed-unmatched reason"
        )
    if extra_reasons:
        problems.append(
            f"allowed_unmatched declares bases with no unmatched pair: {sorted(extra_reasons)}"
        )

    return problems


def validate_ontology_membership(labels: list[Label], ontology_categories: set[str]) -> list[str]:
    """Every label's category must be in the trainable ontology (RFC 0012 §11)."""
    return [
        f"category {label.category!r} not in ontology"
        for label in labels
        if label.category not in ontology_categories
    ]


def validate_single_anchor_duplicates(
    labels: list[Label], *, allow_multiple: frozenset[str] = frozenset()
) -> list[str]:
    """Reject duplicate single-anchor categories unless explicitly permitted (RFC 0012 §11).

    A "single anchor" category is one without an ``_inicio``/``_fim``
    pairing (e.g. ``dispositivo_abertura``). More than one occurrence in a
    record is rejected by default — pass its name in ``allow_multiple`` to
    permit it explicitly.
    """
    single_anchor_counts: dict[str, int] = {}
    for label in labels:
        if label.category.endswith(_INICIO_SUFFIX) or label.category.endswith(_FIM_SUFFIX):
            continue
        single_anchor_counts[label.category] = single_anchor_counts.get(label.category, 0) + 1

    return [
        f"category {category!r} appears {count} times — single-anchor categories must "
        "appear at most once unless explicitly permitted"
        for category, count in sorted(single_anchor_counts.items())
        if count > 1 and category not in allow_multiple
    ]


def validate_record(
    text: str,
    labels: list[Label],
    ontology_categories: set[str],
    *,
    allowed_unmatched: dict[str, str] | None = None,
    declared_unmatched: bool = False,
    allow_multiple_single_anchor: frozenset[str] = frozenset(),
) -> list[str]:
    """Full RFC 0012 §11 mechanical validation for one ``(text, labels)`` record.

    Composes every check this module offers; returns an empty list iff the
    record is mechanically valid. Does not check semantic correctness of
    the labels (§3.2) — only structure.
    """
    problems = list(check_final_invariants(text, labels))
    problems.extend(validate_ontology_membership(labels, ontology_categories))
    problems.extend(
        validate_pairs(
            labels, allowed_unmatched=allowed_unmatched, declared_unmatched=declared_unmatched
        )
    )
    problems.extend(
        validate_single_anchor_duplicates(labels, allow_multiple=allow_multiple_single_anchor)
    )
    return problems
