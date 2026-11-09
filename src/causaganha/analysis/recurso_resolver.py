"""Resolução determinística de polo vencedor recursal com efeito substitutivo (CPC art. 1.008)."""

from __future__ import annotations

from typing import Literal

WinnerPolo = Literal["A", "P", "draw", "unknown"]

RECURSO_OUTCOMES = frozenset(
    {
        "provido",
        "não provido",
        "parcialmente provido",
        "não conhecido",
        "prejudicado",
    }
)

FIRST_INSTANCE_OUTCOMES = frozenset(
    {
        "procedente",
        "improcedente",
        "parcialmente procedente",
        "acordo",
        "extinto sem mérito",
    }
)


def resolve_winner_polo(
    outcome: str | None,
    recorrente_polo: str | None = None,
) -> WinnerPolo:
    """Mapeia (outcome, recorrente_polo) -> WinnerPolo em O(1) determinístico.

    Aplica a inversão de polaridade recursal (CPC art. 1.008):
    - provido     + recorrente='A' -> 'A'
    - provido     + recorrente='P' -> 'P'
    - não provido + recorrente='A' -> 'P'
    - não provido + recorrente='P' -> 'A'
    - parcialmente provido -> 'draw'
    - não conhecido / prejudicado -> 'unknown'

    1ª Instância:
    - procedente -> 'A'
    - improcedente -> 'P'
    - parcialmente procedente -> 'draw'
    - acordo -> 'draw'
    - extinto sem mérito -> 'unknown'
    """
    if not outcome:
        return "unknown"

    clean_outcome = outcome.strip().lower()

    # 1ª Instância
    if clean_outcome == "procedente":
        return "A"
    if clean_outcome == "improcedente":
        return "P"
    if clean_outcome in {"parcialmente procedente", "acordo"}:
        return "draw"
    if clean_outcome in {"extinto sem mérito", "unknown"}:
        return "unknown"

    # Recursos (2º Grau / Superior)
    rec_polo = (recorrente_polo or "").strip().upper()

    if clean_outcome == "provido":
        if rec_polo == "A":
            return "A"
        if rec_polo == "P":
            return "P"
        return "unknown"

    if clean_outcome in {"não provido", "nao provido", "desprovido", "improvido"}:
        if rec_polo == "A":
            return "P"
        if rec_polo == "P":
            return "A"
        return "unknown"

    if clean_outcome in {"parcialmente provido", "provido em parte"}:
        return "draw"

    return "unknown"


# Alias para ponto de entrada único de benchmark
to_winner_polo = resolve_winner_polo
