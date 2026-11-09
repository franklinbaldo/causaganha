"""Testes unitários para o resolvedor recursal (CPC art. 1.008 e DESIGN.md)."""

from __future__ import annotations

import pytest
from causaganha.analysis.recurso_resolver import resolve_winner_polo, to_winner_polo


@pytest.mark.parametrize(
    ("outcome", "recorrente", "expected"),
    [
        # 1ª Instância (recorrente_polo ausente ou irrelevante)
        ("procedente", None, "A"),
        ("improcedente", None, "P"),
        ("parcialmente procedente", None, "draw"),
        ("acordo", None, "draw"),
        ("extinto sem mérito", None, "unknown"),
        ("unknown", None, "unknown"),
        ("", None, "unknown"),
        (None, None, "unknown"),
        # 2ª Instância - Recurso do Autor (A)
        ("provido", "A", "A"),
        ("não provido", "A", "P"),
        ("nao provido", "A", "P"),
        ("desprovido", "A", "P"),
        ("parcialmente provido", "A", "draw"),
        # 2ª Instância - Recurso do Réu (P) -> Inversão de Polaridade
        ("provido", "P", "P"),
        ("não provido", "P", "A"),
        ("nao provido", "P", "A"),
        ("desprovido", "P", "A"),
        ("parcialmente provido", "P", "draw"),
        # Inadmissibilidade recursal (gate de admissibilidade)
        ("não conhecido", "A", "unknown"),
        ("não conhecido", "P", "unknown"),
        ("prejudicado", "A", "unknown"),
        ("prejudicado", "P", "unknown"),
    ],
)
def test_resolve_winner_polo(outcome, recorrente, expected):
    assert resolve_winner_polo(outcome, recorrente) == expected
    assert to_winner_polo(outcome, recorrente) == expected
