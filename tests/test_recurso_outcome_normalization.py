"""Regression tests for appeal-outcome normalization (Bug C).

Analyzers may emit appeal outcomes as uppercase underscored keys (e.g.
"NAO_PROVIDO"). These must normalize to the canonical Portuguese Outcome
values instead of silently resolving every appeal as "unknown".
"""

from __future__ import annotations

import pytest

from causaganha.analysis.models import DecisionAnalysis, Outcome


def _normalized(outcome: str) -> str:
    """Build a minimal DecisionAnalysis and return its normalized outcome."""
    analysis = DecisionAnalysis(
        intimation_id=1,
        decision_type="acórdão",
        outcome=outcome,
        confidence_score=1.0,
    )
    return analysis.outcome


@pytest.mark.parametrize(
    ("rag_key", "expected"),
    [
        ("NAO_PROVIDO", Outcome.NAO_PROVIDO.value),
        ("PARCIALMENTE_PROVIDO", Outcome.PARCIALMENTE_PROVIDO.value),
        ("NAO_CONHECIDO", Outcome.NAO_CONHECIDO.value),
        ("PROVIDO", Outcome.PROVIDO.value),
        ("PREJUDICADO", Outcome.PREJUDICADO.value),
        ("EXTINTO_SEM_MERITO", Outcome.EXTINTO_SEM_MERITO.value),
    ],
)
def test_rag_appeal_keys_normalize_to_canonical(rag_key: str, expected: str) -> None:
    assert _normalized(rag_key) == expected


@pytest.mark.parametrize("rag_key", ["WIN", "LOSS", "PARTIAL", "SETTLEMENT", "UNKNOWN"])
def test_rag_simple_terms_preserved(rag_key: str) -> None:
    assert _normalized(rag_key) == rag_key


def test_raw_underscore_form_is_normalized() -> None:
    # Guards the regression: the underscored form must not leak through
    # normalization unchanged.
    assert _normalized("NAO_PROVIDO") == Outcome.NAO_PROVIDO.value
