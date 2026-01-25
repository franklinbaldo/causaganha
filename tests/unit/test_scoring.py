"""Tests for scoring module using OpenSkill."""

import pytest
from openskill.models import PlackettLuce
from openskill.models.weng_lin.plackett_luce import PlackettLuceRating as OpenSkillRating

from causaganha.scoring.openskill import (
    create_rating,
    get_openskill_model,
    rate_teams,
)

DEFAULT_MU = 25.0
DEFAULT_SIGMA = 25.0 / 3.0
CUSTOM_MU = 30.0
CUSTOM_SIGMA = 5.0
CUSTOM_RATING_SIGMA = 2.0
BETA = 2.0
TAU = 0.1
EPSILON = 0.001


def test_get_openskill_model_defaults() -> None:
    """Test creating OpenSkill model with default parameters."""
    model = get_openskill_model()
    assert isinstance(model, PlackettLuce)
    assert model.mu == DEFAULT_MU
    assert model.sigma == DEFAULT_SIGMA


def test_get_openskill_model_custom() -> None:
    """Test creating OpenSkill model with custom parameters."""
    config = {"mu": CUSTOM_MU, "sigma": CUSTOM_SIGMA, "beta": BETA, "tau": TAU}
    model = get_openskill_model(config)
    assert model.mu == CUSTOM_MU
    assert model.sigma == CUSTOM_SIGMA


def test_create_rating_default() -> None:
    """Test creating rating with default model values."""
    model = get_openskill_model()
    rating = create_rating(model, name="Player1")
    assert isinstance(rating, OpenSkillRating)
    assert rating.mu == model.mu
    assert rating.sigma == model.sigma
    assert rating.name == "Player1"


def test_create_rating_custom() -> None:
    """Test creating rating with custom values."""
    model = get_openskill_model()
    rating = create_rating(
        model, mu=CUSTOM_MU, sigma=CUSTOM_RATING_SIGMA, name="Player2"
    )
    assert rating.mu == CUSTOM_MU
    assert rating.sigma == CUSTOM_RATING_SIGMA


def test_rate_teams_win() -> None:
    """Test rating update for a win."""
    model = get_openskill_model()
    r1 = create_rating(model, name="Winner")
    r2 = create_rating(model, name="Loser")

    initial_mu_r1 = r1.mu
    initial_mu_r2 = r2.mu

    # Team A (Winner) vs Team B (Loser)
    new_r1, new_r2 = rate_teams(model, [r1], [r2], "win_a")

    # Winner mu should increase
    assert new_r1[0].mu > initial_mu_r1
    # Loser mu should decrease
    assert new_r2[0].mu < initial_mu_r2


def test_rate_teams_draw() -> None:
    """Test rating update for a draw."""
    model = get_openskill_model()
    r1 = create_rating(model, name="P1")
    r2 = create_rating(model, name="P2")

    # Draw
    new_r1, new_r2 = rate_teams(model, [r1], [r2], "draw")

    # Should be symmetric for identical initial ratings
    assert abs(new_r1[0].mu - new_r2[0].mu) < EPSILON


def test_rate_teams_invalid_result() -> None:
    """Test error handling for invalid match result."""
    model = get_openskill_model()
    r1 = create_rating(model)
    r2 = create_rating(model)

    with pytest.raises(ValueError, match="Unknown match result"):
        rate_teams(model, [r1], [r2], "invalid_result")
