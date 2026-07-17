from __future__ import annotations

from segmenter_dataset.release import _support_gates


def test_support_gates_count_absent_ontology_categories_as_zero() -> None:
    train_gate, val_gate = _support_gates([], [], {"resultado"})

    assert train_gate.passed is False
    assert val_gate.passed is False
    assert "'resultado': 0" in train_gate.detail
    assert "'resultado': 0" in val_gate.detail
