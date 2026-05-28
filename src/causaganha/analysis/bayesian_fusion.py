"""Bayesian fusion of multiple outcome classification signals.

Combines probability distributions from independent classifiers
(heuristic regex, embedding k-NN, LLM) using the product-of-experts
approach in log-space for numerical stability.

Each classifier returns a full probability distribution over outcomes,
and this module fuses them into a single posterior distribution.
"""

from __future__ import annotations

import math
from typing import Literal

import structlog


logger = structlog.get_logger()

# Canonical outcome keys — must be consistent across all classifiers
OUTCOME_KEYS: list[str] = [
    "procedente",
    "parcialmente procedente",
    "improcedente",
    "acordo",
    "extinto sem mérito",
    "unknown",
]

WinnerPolo = Literal["A", "P", "draw", "unknown"]

# Maps outcome to which polo wins
OUTCOME_TO_POLO: dict[str, WinnerPolo] = {
    "procedente": "A",            # Polo Ativo (autor) ganha
    "parcialmente procedente": "A",  # Polo Ativo ganha parcialmente
    "improcedente": "P",          # Polo Passivo (réu) ganha
    "acordo": "draw",             # Nenhum perde — acordo mútuo
    "extinto sem mérito": "unknown",  # Sem julgamento de mérito
    "unknown": "unknown",
}

# Minimum probability to avoid log(0) issues
_EPS = 1e-9

OutcomeDistribution = dict[str, float]


def uniform_prior() -> OutcomeDistribution:
    """Return a uniform distribution over all outcomes.

    Used as the starting prior when no domain-specific base rates
    are available.
    """
    p = 1.0 / len(OUTCOME_KEYS)
    return dict.fromkeys(OUTCOME_KEYS, p)


def normalize(dist: OutcomeDistribution) -> OutcomeDistribution:
    """Normalize a distribution so its values sum to 1.0.

    Ensures all keys from OUTCOME_KEYS are present, filling missing
    keys with _EPS before normalizing.

    Args:
        dist: Raw probability distribution (may not sum to 1.0).

    Returns:
        Normalized distribution summing to 1.0.
    """
    # Ensure all keys are present
    full = {k: max(dist.get(k, _EPS), _EPS) for k in OUTCOME_KEYS}
    total = sum(full.values())
    return {k: v / total for k, v in full.items()}


def fuse(
    sources: list[tuple[OutcomeDistribution, float]],
    prior: OutcomeDistribution | None = None,
) -> OutcomeDistribution:
    """Fuse multiple outcome distributions via product-of-experts.

    Each source is a (distribution, weight) tuple. The weight controls
    how strongly that source influences the posterior. Weights should
    reflect the confidence/reliability of each classifier.

    Uses log-space arithmetic to avoid underflow when combining many
    distributions.

    Args:
        sources: List of (distribution, weight) tuples. Weight is
            typically the classifier's confidence score (0.0-1.0).
            An empty list returns the prior.
        prior: Starting distribution. Defaults to uniform_prior().

    Returns:
        Normalized posterior distribution.

    Example:
        heuristic = {"procedente": 0.85, "improcedente": 0.10, ...}
        embedding  = {"procedente": 0.70, "improcedente": 0.25, ...}
        posterior  = fuse([(heuristic, 0.85), (embedding, 0.75)])
    """
    if prior is None:
        prior = uniform_prior()

    if not sources:
        return normalize(prior)

    # Start with log-prior
    log_posterior: dict[str, float] = {
        k: math.log(max(prior.get(k, _EPS), _EPS))
        for k in OUTCOME_KEYS
    }

    # Add each source's weighted log-likelihood
    for dist, weight in sources:
        for outcome in OUTCOME_KEYS:
            p = max(dist.get(outcome, _EPS), _EPS)
            log_posterior[outcome] += weight * math.log(p)

    # Convert from log-space via log-sum-exp trick for numerical stability
    max_log = max(log_posterior.values())
    exp_vals = {k: math.exp(v - max_log) for k, v in log_posterior.items()}
    total = sum(exp_vals.values())
    posterior = {k: v / total for k, v in exp_vals.items()}

    logger.debug(
        "bayesian_fusion_complete",
        num_sources=len(sources),
        top_outcome=max(posterior, key=posterior.__getitem__),
        top_prob=round(max(posterior.values()), 3),
    )

    return posterior


def get_winner_polo(
    distribution: OutcomeDistribution,
    min_confidence: float = 0.50,
) -> WinnerPolo:
    """Map a posterior distribution to a winning polo.

    Args:
        distribution: Posterior outcome distribution.
        min_confidence: Minimum probability for the top outcome to
            be accepted. Below this threshold, returns "unknown".

    Returns:
        "A"  — Polo Ativo (autor) won
        "P"  — Polo Passivo (réu) won
        "draw" — Settlement (acordo)
        "unknown" — Cannot determine winner
    """
    if not distribution:
        return "unknown"

    best_outcome = max(distribution, key=distribution.__getitem__)
    best_prob = distribution[best_outcome]

    if best_prob < min_confidence:
        logger.debug(
            "winner_polo_uncertain",
            best_outcome=best_outcome,
            best_prob=round(best_prob, 3),
            threshold=min_confidence,
        )
        return "unknown"

    polo = OUTCOME_TO_POLO.get(best_outcome, "unknown")
    logger.debug(
        "winner_polo_resolved",
        outcome=best_outcome,
        polo=polo,
        confidence=round(best_prob, 3),
    )
    return polo


def posterior_confidence(distribution: OutcomeDistribution) -> float:
    """Return the maximum probability in the distribution.

    This is the simplest confidence metric — the probability assigned
    to the most likely outcome.

    Args:
        distribution: Posterior outcome distribution.

    Returns:
        Maximum probability (0.0-1.0).
    """
    if not distribution:
        return 0.0
    return max(distribution.values())


def distributions_agree(
    dist_a: OutcomeDistribution,
    dist_b: OutcomeDistribution,
) -> bool:
    """Check if two distributions agree on the top outcome.

    Args:
        dist_a: First distribution.
        dist_b: Second distribution.

    Returns:
        True if both distributions assign highest probability to the
        same outcome.
    """
    if not dist_a or not dist_b:
        return False
    top_a = max(dist_a, key=dist_a.__getitem__)
    top_b = max(dist_b, key=dist_b.__getitem__)
    return top_a == top_b


def heuristic_distribution(outcome: str, confidence: float) -> OutcomeDistribution:
    """Convert a single (outcome, confidence) pair to a distribution.

    Used to translate the legacy heuristic output format into the
    unified OutcomeDistribution format expected by fuse().

    The confidence is assigned to the matched outcome; remaining
    probability mass is distributed uniformly among other outcomes.

    Args:
        outcome: The matched outcome string (must be in OUTCOME_KEYS).
        confidence: Confidence score (0.0-1.0).

    Returns:
        OutcomeDistribution with ``confidence`` on the matched outcome
        and remaining mass spread uniformly.
    """
    if outcome not in OUTCOME_KEYS or outcome == "unknown":
        return uniform_prior()

    other_keys = [k for k in OUTCOME_KEYS if k != outcome]
    remaining = max(1.0 - confidence, _EPS)
    other_p = remaining / len(other_keys)

    dist: OutcomeDistribution = dict.fromkeys(other_keys, other_p)
    dist[outcome] = confidence
    return dist
