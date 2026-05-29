"""Regression tests for RAG appeal-outcome normalization (Bug C).

RAG emits appeal outcomes as uppercase underscored keys (e.g. "NAO_PROVIDO").
These must normalize to the canonical Portuguese Outcome values so that
recurso_resolver recognises them and applies polarity inversion, instead of
silently resolving every appeal as "unknown".
"""

from __future__ import annotations

import pytest

from causaganha.analysis.models import DecisionAnalysis, Outcome
from causaganha.analysis.recurso_resolver import is_recurso_outcome, resolve_winner_polo


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


def test_normalized_appeal_outcome_is_recognised_by_resolver() -> None:
    # The whole point: a RAG "NAO_PROVIDO" must flow through normalization and
    # be recognised as an appeal outcome by the resolver.
    assert is_recurso_outcome(_normalized("NAO_PROVIDO"))


def test_nao_provido_inverts_polarity() -> None:
    # "não provido" => appellee wins => the polo that did NOT appeal.
    outcome = _normalized("NAO_PROVIDO")
    assert resolve_winner_polo(outcome, recorrente_polo="A") == "P"
    assert resolve_winner_polo(outcome, recorrente_polo="P") == "A"


def test_provido_keeps_appellant() -> None:
    outcome = _normalized("PROVIDO")
    assert resolve_winner_polo(outcome, recorrente_polo="A") == "A"
    assert resolve_winner_polo(outcome, recorrente_polo="P") == "P"


def test_raw_underscore_form_would_not_resolve() -> None:
    # Guards the regression: the un-normalized form is NOT recognised, which is
    # exactly the bug this fix prevents from reaching the resolver.
    assert not is_recurso_outcome("nao_provido")
