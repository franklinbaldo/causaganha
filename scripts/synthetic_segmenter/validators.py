"""Final mechanical + ontology validation (RFC 0011 §4.3, §11, §16.1 item 3).

Composes ``transform.check_final_invariants`` (offset bounds/overlap) with
the ontology-specific rules from ``annotation_guideline_v7.md`` that a
generated record must also satisfy:

- every label's category is in the real v7 label space;
- at most one ``dispositivo_abertura`` (guideline rule 2 — "One
  dispositivo_abertura per decision");
- a declared ``unmatched_pair`` in provenance must actually correspond to
  a real unmatched ``_inicio``/``_fim`` in the record (and vice versa) —
  catches a generator bug where the flag and the text disagree.

Does not re-implement anchor-surface checking against phrase_banks.py —
that's a generator-development aid, not a hard training-data requirement
(paraphrased anchors are legitimate as long as they're in the label
space's category, per the guideline's "short, distinctive cues" rule).
"""

from __future__ import annotations

from scripts.synthetic_segmenter.transform import check_final_invariants


_PAIR_BASE_NAMES = (
    "cabecalho",
    "ementa",
    "relatorio",
    "capitulo_merito",
    "preliminar",
    "honorarios",
    "custas",
    "encerramento",
    "voto",
    "acordao_decisorio",
)


def _category_names(labels: list[dict]) -> list[str]:
    return [label["category"] for label in labels]


def validate_record(
    text: str,
    labels: list[dict],
    label_space_categories: set[str],
    *,
    info: dict | None = None,
) -> list[str]:
    """Return problem strings for one ``(text, labels)`` record; empty = valid.

    ``info`` is the record's provenance dict (RFC 0011 §15) — passed
    optionally so the ``unmatched_pair`` cross-check can run; omit it to
    validate offsets/ontology only.
    """
    problems = list(check_final_invariants(text, labels))

    categories = _category_names(labels)
    problems.extend(
        f"category {cat!r} not in label space"
        for cat in categories
        if cat not in label_space_categories
    )

    n_dispositivo = categories.count("dispositivo_abertura")
    if n_dispositivo > 1:
        problems.append(
            f"{n_dispositivo} dispositivo_abertura labels — guideline requires exactly one "
            "operative dispositivo_abertura per decision"
        )

    unmatched_bases_in_text = {
        base
        for base in _PAIR_BASE_NAMES
        if f"{base}_inicio" in categories and f"{base}_fim" not in categories
    }
    if info is not None:
        declared_unmatched = bool(info.get("unmatched_pair", False))
        if unmatched_bases_in_text and not declared_unmatched:
            problems.append(
                f"record has unmatched pair(s) {sorted(unmatched_bases_in_text)} but "
                "info.unmatched_pair is not True"
            )
        if declared_unmatched and not unmatched_bases_in_text:
            problems.append("info.unmatched_pair=True but no unmatched pair found in labels")

    return problems


def load_label_space_categories(label_space_json: dict) -> set[str]:
    """Extract the non-``O`` category set from a parsed ``label_space.json``."""
    names = label_space_json.get("span_class_names") or []
    return {name for name in names if name != "O"}
