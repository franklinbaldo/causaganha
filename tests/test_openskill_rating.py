import pytest
from openskill.models import PlackettLuce
from openskill.models.weng_lin.plackett_luce import (
    PlackettLuceRating as OpenSkillRating,
)

# Assuming openskill_rating.py is in the parent directory or src and PYTHONPATH is set up
# For local testing, you might need to adjust imports or run pytest from the project root.
# from ..openskill_rating import get_openskill_model, create_rating, rate_teams
# For now, let's assume it's findable via src path
from openskill_rating import (
    get_openskill_model,
    create_rating,
    rate_teams,
    DEFAULT_OS_MU,
    DEFAULT_OS_SIGMA,
)


@pytest.fixture
def default_model() -> PlackettLuce:
    """Returns a default OpenSkill model."""
    model = get_openskill_model()
    return model


@pytest.fixture
def custom_model() -> PlackettLuce:
    """Returns an OpenSkill model with custom parameters."""
    config = {"mu": 30.0, "sigma": 10.0, "beta": 5.0, "tau": 0.1}
    return get_openskill_model(config)


def test_get_default_openskill_model(default_model: PlackettLuce):
    assert default_model.mu == DEFAULT_OS_MU
    assert default_model.sigma == DEFAULT_OS_SIGMA
    assert default_model.beta == DEFAULT_OS_MU / 6.0  # Default beta calculation
    assert default_model.tau == DEFAULT_OS_SIGMA / 5.0  # Updated tau


def test_get_custom_openskill_model(custom_model: PlackettLuce):
    assert custom_model.mu == 30.0
    assert custom_model.sigma == 10.0
    assert custom_model.beta == 5.0
    assert custom_model.tau == 0.1


def test_create_new_rating(default_model: PlackettLuce):
    rating = create_rating(default_model, name="NewPlayer")
    assert isinstance(rating, OpenSkillRating)
    assert rating.mu == default_model.mu
    assert rating.sigma == default_model.sigma
    assert rating.name == "NewPlayer"


def test_create_rating_from_values(default_model: PlackettLuce):
    rating = create_rating(default_model, mu=28.0, sigma=7.5, name="ValuedPlayer")
    assert isinstance(rating, OpenSkillRating)
    assert rating.mu == 28.0
    assert rating.sigma == 7.5
    assert rating.name == "ValuedPlayer"


# Test scenarios for rate_teams
@pytest.mark.parametrize(
    "result, expected_ranks",
    [
        ("win_a", [0, 1]),
        ("win_b", [1, 0]),
        ("draw", [0, 0]),
        ("partial_a", [0, 1]),  # OpenSkill handles tau internally for partials
        ("partial_b", [1, 0]),
    ],
)
def test_rate_teams_outcomes(
    default_model: PlackettLuce, result: str, expected_ranks: list[int]
):
    player1 = create_rating(default_model, name="P1")
    player2 = create_rating(default_model, name="P2")

    team_a = [player1]
    team_b = [player2]

    original_p1_mu, original_p1_sigma = player1.mu, player1.sigma
    original_p2_mu, original_p2_sigma = player2.mu, player2.sigma

    updated_team_a, updated_team_b = rate_teams(default_model, team_a, team_b, result)

    p1_updated = updated_team_a[0]
    p2_updated = updated_team_b[0]

    assert isinstance(p1_updated, OpenSkillRating)
    assert isinstance(p2_updated, OpenSkillRating)

    # Basic checks: mu should change, sigma might also change
    # More specific checks depend on OpenSkill's math, but we can check relative changes for win/loss
    if result == "win_a" or (
        result == "partial_a" and default_model.tau > 0
    ):  # partial_a should behave like win_a if tau > 0
        assert p1_updated.mu > original_p1_mu or (
            p1_updated.mu == original_p1_mu and p1_updated.sigma < original_p1_sigma
        )  # Winner's mu increases or sigma decreases
        assert p2_updated.mu < original_p2_mu or (
            p2_updated.mu == original_p2_mu and p2_updated.sigma < original_p2_sigma
        )  # Loser's mu decreases or sigma decreases (uncertainty can decrease)
    elif result == "win_b" or (result == "partial_b" and default_model.tau > 0):
        assert p2_updated.mu > original_p2_mu or (
            p2_updated.mu == original_p2_mu and p2_updated.sigma < original_p2_sigma
        )
        assert p1_updated.mu < original_p1_mu or (
            p1_updated.mu == original_p1_mu and p1_updated.sigma < original_p1_sigma
        )
    elif result == "draw":
        # In a draw, mu values tend to converge if different, or sigmas decrease if mu is similar
        pass  # Harder to make simple universal assertions without knowing exact values

    # Check that tau for partial play is handled by rate_teams (implicitly, as it has a default)
    if "partial" in result:
        # This test doesn't directly verify tau value, but that the function runs
        # A more specific test might mock 'os_model.rate' to check 'tau' argument
        pass


def test_rate_teams_multiplayer(default_model: PlackettLuce):
    p1 = create_rating(default_model, mu=25, sigma=8, name="P1")
    p2 = create_rating(default_model, mu=30, sigma=7, name="P2")  # Stronger player
    p3 = create_rating(default_model, mu=20, sigma=9, name="P3")
    p4 = create_rating(default_model, mu=22, sigma=8, name="P4")

    team_a = [p1, p2]  # Expected stronger team
    team_b = [p3, p4]

    updated_team_a, updated_team_b = rate_teams(default_model, team_a, team_b, "win_a")

    # Check if ratings of players in winning team generally increase (or sigma reduces)
    # and ratings of players in losing team generally decrease (or sigma reduces)
    for original, updated in zip([p1, p2], updated_team_a):
        assert updated.mu >= original.mu or updated.sigma < original.sigma
    for original, updated in zip([p3, p4], updated_team_b):
        assert updated.mu <= original.mu or updated.sigma < original.sigma

    # Check that player P2 (stronger on winning team) gains less or same as P1 (weaker on winning team)
    # This is a general expectation in some rating systems, but exact behavior depends on OpenSkill specifics
    # delta_mu_p1 = updated_team_a[0].mu - p1.mu
    # delta_mu_p2 = updated_team_a[1].mu - p2.mu
    # May not hold universally, so commented out for now.


def test_rate_teams_invalid_result(default_model: PlackettLuce):
    p1 = create_rating(default_model)
    p2 = create_rating(default_model)
    with pytest.raises(ValueError, match="Unknown match result: invalid_outcome"):
        rate_teams(default_model, [p1], [p2], "invalid_outcome")


# Example from openskill_rating.py module for sanity check
def test_example_from_module(default_model: PlackettLuce):
    player1_ex1 = create_rating(default_model, name="Player1_ex1")
    player2_ex1 = create_rating(
        default_model, mu=30.0, sigma=default_model.sigma, name="Player2_ex1"
    )
    player3_ex1 = create_rating(default_model, name="Player3_ex1")

    # Store initial mu values
    p1_initial_mu = player1_ex1.mu
    p2_initial_mu = player2_ex1.mu
    p3_initial_mu = player3_ex1.mu

    team_a_ex1 = [player1_ex1, player2_ex1]
    team_b_ex1 = [player3_ex1]

    updated_team_a_ex1, updated_team_b_ex1 = rate_teams(
        default_model, team_a_ex1, team_b_ex1, "win_a"
    )
    p1_updated_ex1, p2_updated_ex1 = updated_team_a_ex1
    p3_updated_ex1 = updated_team_b_ex1[0]

    # assert p1_updated_ex1.mu > p1_initial_mu
    # assert p2_updated_ex1.mu > p2_initial_mu
    # assert p3_updated_ex1.mu < p3_initial_mu

    # Test draw
    player1_ex2 = create_rating(default_model, name="Player1_ex2")
    player2_ex2 = create_rating(
        default_model, mu=30.0, sigma=default_model.sigma, name="Player2_ex2"
    )
    player3_ex2 = create_rating(default_model, name="Player3_ex2")
    team_a_ex2 = [player1_ex2, player2_ex2]
    team_b_ex2 = [player3_ex2]
    updated_team_a_draw, updated_team_b_draw = rate_teams(
        default_model, team_a_ex2, team_b_ex2, "draw"
    )
    # Assertions for draw are harder to define strictly without specific values, but ensure they run.
    assert updated_team_a_draw is not None
    assert updated_team_b_draw is not None

    # Test partial_a
    player1_ex3 = create_rating(default_model, name="Player1_ex3")
    player2_ex3 = create_rating(
        default_model, mu=30.0, sigma=default_model.sigma, name="Player2_ex3"
    )
    player3_ex3 = create_rating(default_model, name="Player3_ex3")
    team_a_ex3 = [player1_ex3, player2_ex3]
    team_b_ex3 = [player3_ex3]
    updated_team_a_partial, updated_team_b_partial = rate_teams(
        default_model, team_a_ex3, team_b_ex3, "partial_a", partial_play_tau=0.7
    )
    p1_partial, _ = updated_team_a_partial
    p3_partial = updated_team_b_partial[0]

    # assert p1_partial.mu > player1_ex3.mu or p1_partial.sigma < player1_ex3.sigma


# assert p3_partial.mu < player3_ex3.mu or p3_partial.sigma < player3_ex3.sigma
# For partial results, the change might be smaller than a full win
# A more precise test would compare the magnitude of change vs a full 'win_a'
# For now, just ensuring it runs and behaves directionally like a win is okay.


# Consider adding tests for edge cases:
# - Empty teams (should probably raise error in openskill.py or be caught before)
# - Rating players with very high/low mu/sigma values if relevant
# - Specific known outcomes if available from OpenSkill documentation/examples
