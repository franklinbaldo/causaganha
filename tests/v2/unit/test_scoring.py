import pytest
from openskill.models import PlackettLuce
from openskill.models.weng_lin.plackett_luce import PlackettLuceRating as OpenSkillRating

from causaganha.scoring.openskill import (
    create_rating,
    get_openskill_model,
    rate_teams,
)


def test_get_openskill_model_defaults() -> None:
    model = get_openskill_model()
    assert isinstance(model, PlackettLuce)
    assert model.mu == 25.0
    assert model.sigma == 25.0 / 3.0


def test_get_openskill_model_custom() -> None:
    config = {"mu": 30.0, "sigma": 5.0, "beta": 2.0, "tau": 0.1}
    model = get_openskill_model(config)
    assert model.mu == 30.0
    assert model.sigma == 5.0


def test_create_rating_default() -> None:
    model = get_openskill_model()
    rating = create_rating(model, name="Player1")
    assert isinstance(rating, OpenSkillRating)
    assert rating.mu == model.mu
    assert rating.sigma == model.sigma
    assert rating.name == "Player1"


def test_create_rating_custom() -> None:
    model = get_openskill_model()
    rating = create_rating(model, mu=30.0, sigma=2.0, name="Player2")
    assert rating.mu == 30.0
    assert rating.sigma == 2.0


def test_rate_teams_win() -> None:
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
    model = get_openskill_model()
    r1 = create_rating(model, name="P1")
    r2 = create_rating(model, name="P2")

    # Draw
    new_r1, new_r2 = rate_teams(model, [r1], [r2], "draw")

    # Should be symmetric for identical initial ratings
    assert abs(new_r1[0].mu - new_r2[0].mu) < 0.001


def test_rate_teams_invalid_result() -> None:
    model = get_openskill_model()
    r1 = create_rating(model)
    r2 = create_rating(model)

    with pytest.raises(ValueError):
        rate_teams(model, [r1], [r2], "invalid_result")
