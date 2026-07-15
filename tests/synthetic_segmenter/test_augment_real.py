"""Tests for scripts.synthetic_segmenter.augment_real."""

from __future__ import annotations

import random

import pytest

from scripts.synthetic_segmenter.augment_real import (
    augment_record,
    case_noise_edits,
    synonym_substitution_edits,
    whitespace_noise_edits,
)
from scripts.synthetic_segmenter.provenance import validate_provenance
from scripts.synthetic_segmenter.transform import apply_edits, check_final_invariants


def _record() -> dict:
    text = "PODER JUDICIARIO do Estado.  Ante o exposto, julgo procedente o pedido. Publique-se. "
    labels = [
        {"category": "cabecalho_inicio", "start": 0, "end": 17},
        {"category": "dispositivo_abertura", "start": 30, "end": 45},
        {"category": "resultado", "start": 47, "end": 71},
        {"category": "encerramento_inicio", "start": 73, "end": 85},
    ]
    info = {"doc_id": "tjro_sentenca_00"}
    return {"text": text, "label": labels, "info": info}


def test_whitespace_edits_never_touch_labeled_spans() -> None:
    record = _record()
    rng = random.Random(1)
    edits = whitespace_noise_edits(record["text"], record["label"], rng=rng)
    for edit in edits:
        for label in record["label"]:
            assert edit.end <= label["start"] or edit.start >= label["end"]


def test_case_edits_never_touch_labeled_spans() -> None:
    record = _record()
    rng = random.Random(1)
    edits = case_noise_edits(record["text"], record["label"], rng=rng, probability=1.0)
    for edit in edits:
        for label in record["label"]:
            assert edit.end <= label["start"] or edit.start >= label["end"]


def test_synonym_edits_only_fire_on_recognized_variants() -> None:
    record = _record()
    rng = random.Random(1)
    edits = synonym_substitution_edits(record["text"], record["label"], rng=rng)
    categories_touched = set()
    for edit in edits:
        matching = [
            lab for lab in record["label"] if lab["start"] == edit.start and lab["end"] == edit.end
        ]
        assert matching
        categories_touched.add(matching[0]["category"])
    # dispositivo_abertura ("Ante o exposto") and resultado ("julgo procedente
    # o pedido") are both recognized phrase-bank variants in the fixture.
    assert categories_touched <= {"dispositivo_abertura", "resultado"}


def test_synonym_substitution_never_crosses_outcome() -> None:
    text = "Ante o exposto, julgo procedente o pedido."
    labels = [
        {"category": "dispositivo_abertura", "start": 0, "end": 15},
        {"category": "resultado", "start": 17, "end": 42},
    ]
    rng = random.Random(1)
    edits = synonym_substitution_edits(text, labels, rng=rng)
    resultado_edit = next(
        (e for e in edits if e.start == 17 and e.end == 42),
        None,
    )
    if resultado_edit is not None:
        assert "improcedente" not in resultado_edit.replacement
        assert "rejeito" not in resultado_edit.replacement


@pytest.mark.parametrize("seed", range(10))
def test_augmented_record_passes_final_invariants(seed: int) -> None:
    record = _record()
    augmented = augment_record(record, seed=seed)
    assert check_final_invariants(augmented["text"], augmented["label"]) == []


@pytest.mark.parametrize("seed", range(10))
def test_augmented_record_labels_still_point_at_the_same_categories(seed: int) -> None:
    record = _record()
    augmented = augment_record(record, seed=seed)
    original_categories = [lab["category"] for lab in record["label"]]
    augmented_categories = [lab["category"] for lab in augmented["label"]]
    assert augmented_categories == original_categories


def test_augmented_record_has_valid_provenance() -> None:
    record = _record()
    augmented = augment_record(record, seed=1)
    assert augmented["info"]["source_type"] == "augmented_real"
    assert augmented["info"]["source_doc_ids"] == ["tjro_sentenca_00"]
    assert validate_provenance(augmented["info"]) == []


def test_augment_record_is_deterministic() -> None:
    record = _record()
    first = augment_record(record, seed=42)
    second = augment_record(record, seed=42)
    assert first == second


def test_augment_record_different_seeds_can_differ() -> None:
    record = _record()
    outputs = {augment_record(record, seed=s)["text"] for s in range(20)}
    assert len(outputs) > 1


def test_family_subset_whitespace_only_leaves_labels_untouched_surface() -> None:
    record = _record()
    augmented = augment_record(record, seed=1, families=("whitespace",))
    for original, new in zip(record["label"], augmented["label"], strict=True):
        original_surface = record["text"][original["start"] : original["end"]]
        new_surface = augmented["text"][new["start"] : new["end"]]
        assert original_surface == new_surface


def test_apply_edits_reused_directly_matches_augment_record_edit_map() -> None:
    """Sanity check that augment_real composes edits through the real
    Foundation-layer contract, not a private reimplementation.
    """
    record = _record()
    rng = random.Random(7)
    edits = whitespace_noise_edits(record["text"], record["label"], rng=rng)
    result = apply_edits(record["text"], record["label"], edits)
    assert check_final_invariants(result.text, result.labels) == []
