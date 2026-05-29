"""Tests for invariant-winner benchmark metrics (gate + conditional)."""

from __future__ import annotations

from causaganha.analysis.benchmark_metrics import (
    evaluate_invariant,
    is_ratable,
    to_winner_polo,
)


# ---------------------------------------------------------------------------
# Invariant: posture-independent winner
# ---------------------------------------------------------------------------


def test_first_instance_maps_to_polo() -> None:
    assert to_winner_polo("procedente") == "A"
    assert to_winner_polo("parcialmente procedente") == "A"
    assert to_winner_polo("improcedente") == "P"
    assert to_winner_polo("acordo") == "draw"


def test_extinto_sem_merito_is_not_ratable() -> None:
    assert to_winner_polo("extinto sem mérito") == "unknown"
    assert not is_ratable(to_winner_polo("extinto sem mérito"))


def test_case_insensitive() -> None:
    assert to_winner_polo("PROCEDENTE") == "A"


def test_recurso_requires_recorrente_polo() -> None:
    # Without knowing who appealed, the appeal outcome is unresolvable.
    assert to_winner_polo("provido", None) == "unknown"


def test_recurso_polarity_inversion() -> None:
    # The SAME surface outcome maps to OPPOSITE winners depending on appellant.
    assert to_winner_polo("provido", "A") == "A"
    assert to_winner_polo("provido", "P") == "P"
    assert to_winner_polo("não provido", "A") == "P"  # appellee (réu) wins
    assert to_winner_polo("não provido", "P") == "A"  # appellee (autor) wins


def test_invariant_collapses_posture() -> None:
    # A first-instance plaintiff win and an appellate equivalent are the SAME
    # invariant winner, even though the surface labels differ.
    first_instance = to_winner_polo("procedente")
    on_appeal = to_winner_polo("não provido", "P")  # réu appealed and lost
    assert first_instance == on_appeal == "A"


# ---------------------------------------------------------------------------
# Gate + conditional decomposition
# ---------------------------------------------------------------------------


def test_gate_separates_ratable_from_procedural() -> None:
    gold = [
        ("procedente", None),
        ("improcedente", None),
        ("extinto sem mérito", None),  # not ratable
        ("unknown", None),  # not ratable (interlocutória/despacho)
    ]
    # Perfect predictions.
    report = evaluate_invariant(gold, gold)
    assert report.gate.support_ratable == 2
    assert report.gate.total == 4
    assert report.gate.accuracy == 1.0
    assert report.conditional.n_scored == 2
    assert report.conditional.accuracy == 1.0


def test_conditional_ignores_gold_unknown() -> None:
    gold = [
        ("procedente", None),  # A
        ("unknown", None),  # gated out
    ]
    pred = [
        ("improcedente", None),  # P — wrong on the ratable case
        ("procedente", None),  # model hallucinates an outcome on a non-decision
    ]
    report = evaluate_invariant(gold, pred)
    # Only the single gold-ratable case is scored in the conditional.
    assert report.conditional.n_scored == 1
    assert report.conditional.accuracy == 0.0


def test_per_polo_breakdown() -> None:
    gold = [("procedente", None), ("procedente", None), ("improcedente", None)]
    pred = [("procedente", None), ("improcedente", None), ("improcedente", None)]
    report = evaluate_invariant(gold, pred)
    assert report.conditional.per_polo["A"]["support"] == 2
    assert report.conditional.per_polo["P"]["support"] == 1
    # One of two A's misclassified as P -> recall 0.5 for A.
    assert report.conditional.per_polo["A"]["recall"] == 0.5
