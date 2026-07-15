"""Provenance schema for the four source categories (RFC 0011 §15).

Lives inside a training record's ``info`` field, alongside ``text``/``label``
(the schema ``scripts/opf_annotate.py`` already validates) — this module
only validates the provenance sub-object, not the record as a whole.

    {"text": ..., "label": [...], "info": {<provenance fields>}}

Four categories, each with different required fields:

- ``pristine_real``   — gold, manually verified. Minimal provenance.
- ``augmented_real``  — mechanical transform of a pristine real training
                         document (RFC 0011 §11). Needs ``source_doc_ids``
                         (exactly one parent) and the transform record.
- ``fully_synthetic`` — generated from specs/phrase banks/LLM, no direct
                         real-text excerpt. Needs generator identity.
- ``hybrid_synthetic`` — synthetic structure containing real-language
                         excerpts from training documents (RFC 0011 §6.2).
                         Needs both generator identity and source_doc_ids.

``generator_version`` (code version) and ``corpus_release_id`` (identity of
the specific materialized batch) are deliberately separate fields — the
same code version can produce many releases (different seeds, LLM reruns).
See RFC 0011 §15.
"""

from __future__ import annotations


SOURCE_TYPES = ("pristine_real", "augmented_real", "fully_synthetic", "hybrid_synthetic")

# Fields required for every non-pristine record, regardless of category.
_COMMON_GENERATED_REQUIRED = ("source_type", "synthetic", "augmented")

# Extra fields required per category, beyond the common set.
_REQUIRED_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "pristine_real": (),
    "augmented_real": ("source_doc_ids",),
    "fully_synthetic": ("generator_version", "corpus_release_id", "seed"),
    "hybrid_synthetic": (
        "generator_version",
        "corpus_release_id",
        "seed",
        "source_doc_ids",
        "contains_real_text",
    ),
}

# Fields that, when present, must have these exact values per category —
# catches the copy-paste class of bug (marking a hybrid record synthetic=false).
_FIXED_VALUES_BY_CATEGORY: dict[str, dict[str, object]] = {
    "pristine_real": {"synthetic": False, "augmented": False, "contains_real_text": False},
    "augmented_real": {"synthetic": False, "augmented": True},
    "fully_synthetic": {"synthetic": True, "augmented": False, "contains_real_text": False},
    "hybrid_synthetic": {"synthetic": True, "augmented": False, "contains_real_text": True},
}


def validate_provenance(info: dict) -> list[str]:
    """Return problem strings for ``info``; empty list = valid.

    Does not check ``source_doc_ids`` against a real split assignment —
    that's ``split_guard.require_train_only_sources``, a separate concern
    (this module checks internal consistency of the provenance object
    itself, not its relationship to the corpus).
    """
    problems: list[str] = []

    source_type = info.get("source_type")
    if source_type is None:
        # pristine_real records may omit source_type entirely (RFC 0011 §15
        # table lists it as the "no provenance needed" baseline case).
        return problems
    if source_type not in SOURCE_TYPES:
        problems.append(f"unknown source_type {source_type!r}, expected one of {SOURCE_TYPES}")
        return problems

    problems.extend(
        f"[{source_type}] missing required field {field!r}"
        for field in _COMMON_GENERATED_REQUIRED
        if field not in info
    )

    problems.extend(
        f"[{source_type}] missing/empty required field {field!r}"
        for field in _REQUIRED_BY_CATEGORY.get(source_type, ())
        if field not in info or info[field] in (None, "", [])
    )

    for field, expected in _FIXED_VALUES_BY_CATEGORY.get(source_type, {}).items():
        if field in info and info[field] != expected:
            problems.append(
                f"[{source_type}] field {field!r}={info[field]!r}, expected {expected!r}"
            )

    if source_type == "augmented_real" and len(info.get("source_doc_ids", [])) != 1:
        problems.append(
            "[augmented_real] source_doc_ids must have exactly one parent document, "
            f"got {info.get('source_doc_ids')!r}"
        )

    if info.get("unmatched_pair") not in (None, True, False):
        problems.append(f"unmatched_pair must be a bool, got {info['unmatched_pair']!r}")

    hard_neg = info.get("hard_negative_families")
    if hard_neg is not None and not isinstance(hard_neg, list):
        problems.append(f"hard_negative_families must be a list, got {hard_neg!r}")

    return problems


def default_provenance(source_type: str) -> dict:
    """A minimal, internally-consistent provenance skeleton for ``source_type``.

    Callers fill in the category-specific required fields.
    """
    if source_type not in SOURCE_TYPES:
        msg = f"unknown source_type {source_type!r}, expected one of {SOURCE_TYPES}"
        raise ValueError(msg)
    base = {"source_type": source_type}
    base.update(_FIXED_VALUES_BY_CATEGORY[source_type])
    return base
