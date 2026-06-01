"""Resolve winner polo for appeal (recurso) decisions.

Brazilian appellate courts do not say "procedente" or "improcedente" --
they say "provido" (appeal granted) or "nao provido" (appeal denied).
The winner depends on WHO filed the appeal (recorrente_polo):

    provido    + recorrente_polo='A' -> Polo Ativo (autor) won
    provido    + recorrente_polo='P' -> Polo Passivo (reu) won  (polarity inversion)
    nao provido + recorrente_polo='A' -> Polo Passivo (reu) won (polarity inversion)
    nao provido + recorrente_polo='P' -> Polo Ativo (autor) won

Without knowing who filed the appeal (recorrente_polo=None), outcomes
"provido" / "nao provido" are unresolvable and return "unknown".
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from causaganha.analysis.bayesian_fusion import WinnerPolo

# Outcomes that indicate an appeal decision (as opposed to a first-instance ruling)
RECURSO_OUTCOMES: frozenset[str] = frozenset(
    {
        "provido",
        "não provido",
        "parcialmente provido",
        "não conhecido",
        "prejudicado",
    }
)

# First-instance outcome -> winning polo (no polarity inversion)
_FIRST_INSTANCE_MAP: dict[str, str] = {
    "procedente": "A",
    "parcialmente procedente": "A",
    "improcedente": "P",
    "acordo": "draw",
    "extinto sem mérito": "unknown",
    "unknown": "unknown",
}


def is_recurso_outcome(outcome: str) -> bool:
    """Return True if the outcome belongs to the appeal vocabulary."""
    return outcome.lower() in RECURSO_OUTCOMES


def _resolve_recurso(outcome_lower: str, recorrente_polo: str | None) -> str:
    """Resolve appeal outcomes with polarity inversion."""
    if outcome_lower in {"não conhecido", "prejudicado"}:
        return "unknown"

    if outcome_lower in {"provido", "parcialmente provido"}:
        # Appellant wins
        if recorrente_polo == "A":
            return "A"
        if recorrente_polo == "P":
            return "P"
        return "unknown"

    if outcome_lower == "não provido":
        # Appellee wins — flip the polo
        if recorrente_polo == "A":
            return "P"
        if recorrente_polo == "P":
            return "A"
        return "unknown"

    return "unknown"


def resolve_winner_polo(
    outcome: str,
    recorrente_polo: str | None,
) -> WinnerPolo:
    """Resolve the winning polo for any outcome, including appeals.

    For first-instance outcomes (procedente, improcedente, etc.) the
    resolution is deterministic and recorrente_polo is ignored.

    For appeal outcomes (provido, nao provido, etc.) the polarity of the
    result depends on which polo filed the appeal:
        - "provido" means the appellant won
        - "nao provido" means the appellee won (i.e. the OTHER polo)

    Args:
        outcome: Outcome string (lowercase, from Outcome enum or RECURSO_OUTCOMES).
        recorrente_polo: 'A' (polo ativo filed), 'P' (polo passivo filed), or None.

    Returns:
        WinnerPolo: 'A', 'P', 'draw', or 'unknown'.
    """
    outcome_lower = outcome.lower()

    if outcome_lower in _FIRST_INSTANCE_MAP:
        return _FIRST_INSTANCE_MAP[outcome_lower]  # type: ignore[return-value]

    return _resolve_recurso(outcome_lower, recorrente_polo)  # type: ignore[return-value]
