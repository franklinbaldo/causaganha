"""OpenSkill rating system implementation."""

from typing import Any, Sequence

from openskill.models import PlackettLuce
from openskill.models.weng_lin.plackett_luce import (
    PlackettLuceRating as OpenSkillRating,
)


# Default model parameters
DEFAULT_OS_MU = 25.0
DEFAULT_OS_SIGMA = 25.0 / 3.0
DEFAULT_OS_BETA = 25.0 / 6.0
DEFAULT_OS_TAU = (25.0 / 3.0) / 5.0  # sigma / 5


def get_openskill_model(os_config: dict[str, Any] | None = None) -> PlackettLuce:
    """Initialize and return an OpenSkill PlackettLuce model.

    Args:
        os_config: Optional configuration dictionary.

    Returns:
        PlackettLuce model.
    """
    if os_config:
        mu = float(os_config.get("mu", DEFAULT_OS_MU))
        sigma = float(os_config.get("sigma", DEFAULT_OS_SIGMA))
        beta = float(os_config.get("beta", DEFAULT_OS_BETA))
        tau = float(os_config.get("tau", DEFAULT_OS_TAU))
    else:
        mu = DEFAULT_OS_MU
        sigma = DEFAULT_OS_SIGMA
        beta = DEFAULT_OS_BETA
        tau = DEFAULT_OS_TAU

    return PlackettLuce(mu=mu, sigma=sigma, beta=beta, tau=tau)


def create_rating(
    os_model: PlackettLuce,
    mu: float | None = None,
    sigma: float | None = None,
    name: str | None = None,
) -> OpenSkillRating:
    """Create an OpenSkill Rating object.

    Args:
        os_model: The OpenSkill model to use.
        mu: Optional mu value.
        sigma: Optional sigma value.
        name: Optional name for the rating.

    Returns:
        OpenSkillRating object.
    """
    if mu is not None and sigma is not None:
        return os_model.create_rating([float(mu), float(sigma)], name=name)
    return os_model.rating(name=name)


def rate_teams(
    os_model: PlackettLuce,
    team_a_ratings: list[OpenSkillRating],
    team_b_ratings: list[OpenSkillRating],
    result: str,
    partial_play_tau: float = 0.7,
) -> tuple[list[OpenSkillRating], list[OpenSkillRating]]:
    """Update ratings based on match outcome.

    Args:
        os_model: The OpenSkill model.
        team_a_ratings: List of ratings for Team A.
        team_b_ratings: List of ratings for Team B.
        result: Outcome ('win_a', 'win_b', 'draw', 'partial_a', 'partial_b').
        partial_play_tau: Tau for partial play.

    Returns:
        Tuple of (updated_team_a_ratings, updated_team_b_ratings).

    Raises:
        ValueError: If result string is unknown.
    """
    teams = [team_a_ratings, team_b_ratings]

    ranks: Sequence[int | float]
    if result == "win_a":
        ranks = [0, 1]
        new_ratings = os_model.rate(teams, ranks=ranks)
    elif result == "win_b":
        ranks = [1, 0]
        new_ratings = os_model.rate(teams, ranks=ranks)
    elif result == "draw":
        ranks = [0, 0]
        new_ratings = os_model.rate(teams, ranks=ranks)
    elif result == "partial_a":
        ranks = [0, 1]
        new_ratings = os_model.rate(teams, ranks=ranks, tau=partial_play_tau)
    elif result == "partial_b":
        ranks = [1, 0]
        new_ratings = os_model.rate(teams, ranks=ranks, tau=partial_play_tau)
    else:
        msg = f"Unknown match result: {result}. Expected 'win_a', 'win_b', 'draw', 'partial_a', or 'partial_b'."
        raise ValueError(
            msg,
        )

    return new_ratings[0], new_ratings[1]
