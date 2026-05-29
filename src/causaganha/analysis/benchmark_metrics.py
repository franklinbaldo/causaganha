"""Invariant-winner benchmark metrics — gate + conditional decomposition.

The surface ``outcome`` label is *posture-dependent*: a first-instance
``procedente`` and an appellate ``recurso do réu não provido`` describe the
*same substantive event* (the plaintiff prevailed) yet carry different words.
Scoring the surface label therefore measures procedural vocabulary, not who
won — and injects label noise that caps achievable accuracy regardless of
model quality.

This module scores the **invariant**: the winning *polo* (``A`` = autor /
plaintiff, ``P`` = passivo / defendant, ``draw`` = autocomposição), which is
stable across instances. The mapping from (outcome, recorrente_polo) to polo
is owned by :func:`recurso_resolver.resolve_winner_polo`.

Evaluation is decomposed into two independent tasks (selective prediction):

- **Gate** — "is this a ratable merits decision?" Interlocutórias, despachos
  and inadmissible appeals resolve to ``unknown`` and belong here, not in the
  outcome metric. Scored as binary ratable / not-ratable.
- **Conditional** — "given a ratable decision, which polo won?" Scored only
  over cases the gold standard marks ratable, so the ~40% procedural
  ``unknown`` mass cannot mask (or flatter) outcome performance.
"""

from __future__ import annotations

from dataclasses import dataclass

from causaganha.analysis.recurso_resolver import resolve_winner_polo


# Polo values that represent a resolved substantive winner (ratable).
RATABLE_POLOS: frozenset[str] = frozenset({"A", "P", "draw"})


def to_winner_polo(outcome: str, recorrente_polo: str | None = None) -> str:
    """Map a surface outcome to its invariant winning polo.

    Thin wrapper over :func:`resolve_winner_polo` so callers depend on a
    single benchmark entry point.

    Args:
        outcome: Surface outcome label (e.g. ``procedente``, ``não provido``).
        recorrente_polo: ``A``/``P``/``None`` — who filed the appeal. Required
            to resolve appeal outcomes; ignored for first-instance outcomes.

    Returns:
        ``A``, ``P``, ``draw`` or ``unknown``.
    """
    return resolve_winner_polo(outcome, recorrente_polo)


def is_ratable(polo: str) -> bool:
    """Return True if the polo is a resolved substantive winner."""
    return polo in RATABLE_POLOS


@dataclass(frozen=True)
class GateMetrics:
    """Binary ratable-detection metrics (the routing decision)."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    support_ratable: int
    total: int


@dataclass(frozen=True)
class ConditionalMetrics:
    """Winner accuracy computed only over gold-ratable cases."""

    accuracy: float
    n_scored: int
    per_polo: dict[str, dict[str, float | int]]


@dataclass(frozen=True)
class InvariantReport:
    """Full gate + conditional decomposition of invariant-winner scoring."""

    gate: GateMetrics
    conditional: ConditionalMetrics


def _binary_prf(
    gold_pos: list[bool],
    pred_pos: list[bool],
) -> tuple[float, float, float, float]:
    """Return (accuracy, precision, recall, f1) for a boolean classification."""
    tp = sum(1 for g, p in zip(gold_pos, pred_pos, strict=True) if g and p)
    fp = sum(1 for g, p in zip(gold_pos, pred_pos, strict=True) if not g and p)
    fn = sum(1 for g, p in zip(gold_pos, pred_pos, strict=True) if g and not p)
    correct = sum(1 for g, p in zip(gold_pos, pred_pos, strict=True) if g == p)
    total = len(gold_pos)

    accuracy = correct / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return accuracy, precision, recall, f1


def evaluate_invariant(
    gold: list[tuple[str, str | None]],
    pred: list[tuple[str, str | None]],
) -> InvariantReport:
    """Score predictions against gold on the invariant winning polo.

    Args:
        gold: list of ``(outcome, recorrente_polo)`` ground-truth pairs.
        pred: list of ``(outcome, recorrente_polo)`` predicted pairs, aligned
            with ``gold`` index-for-index.

    Returns:
        :class:`InvariantReport` with separate gate and conditional metrics.
    """
    gold_polo = [to_winner_polo(o, r) for o, r in gold]
    pred_polo = [to_winner_polo(o, r) for o, r in pred]

    # --- Gate: ratable detection ---
    gold_ratable = [is_ratable(p) for p in gold_polo]
    pred_ratable = [is_ratable(p) for p in pred_polo]
    accuracy, precision, recall, f1 = _binary_prf(gold_ratable, pred_ratable)
    gate = GateMetrics(
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        support_ratable=sum(gold_ratable),
        total=len(gold_polo),
    )

    # --- Conditional: winner | gold-ratable ---
    scored = [(g, p) for g, p, keep in zip(gold_polo, pred_polo, gold_ratable, strict=True) if keep]
    n_scored = len(scored)
    cond_correct = sum(1 for g, p in scored if g == p)
    cond_accuracy = cond_correct / n_scored if n_scored else 0.0

    per_polo: dict[str, dict[str, float | int]] = {}
    for polo in ("A", "P", "draw"):
        tp = sum(1 for g, p in scored if g == polo and p == polo)
        fp = sum(1 for g, p in scored if g != polo and p == polo)
        fn = sum(1 for g, p in scored if g == polo and p != polo)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        pf1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per_polo[polo] = {
            "precision": prec,
            "recall": rec,
            "f1": pf1,
            "support": sum(1 for g, _ in scored if g == polo),
        }

    conditional = ConditionalMetrics(
        accuracy=cond_accuracy,
        n_scored=n_scored,
        per_polo=per_polo,
    )

    return InvariantReport(gate=gate, conditional=conditional)
