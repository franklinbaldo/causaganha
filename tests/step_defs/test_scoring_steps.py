from pytest_bdd import scenarios, given, when, then, parsers
import pytest
from openskill.models import PlackettLuce
from openskill.models.weng_lin.plackett_luce import PlackettLuceRating as OpenSkillRating

from causaganha.scoring.openskill import (
    create_rating,
    get_openskill_model,
    rate_teams,
)
from types import SimpleNamespace

scenarios("../features/scoring.feature")


@pytest.fixture
def context():
    return {}


# Scenarios: Initialize OpenSkill model


@given(parsers.parse("a configuration with mu {mu:f} and sigma {sigma:f}"), target_fixture="config")
def custom_config(mu, sigma):
    return {"mu": mu, "sigma": sigma}


@when("I request a default OpenSkill model", target_fixture="model")
def default_model():
    return get_openskill_model()


@when("I request an OpenSkill model with this configuration", target_fixture="model")
def custom_model(config):
    return get_openskill_model(config)


@then("the model should be a PlackettLuce instance")
def check_model_type(model):
    assert isinstance(model, PlackettLuce)


@then(parsers.parse("the model mu should be {expected:f}"))
def check_model_mu(model, expected):
    assert model.mu == expected


@then(parsers.parse("the model sigma should be {expected:f}"))
def check_model_sigma(model, expected):
    # handling floating point approximation for 25.0/3.0
    assert abs(model.sigma - expected) < 0.001


# Scenarios: Create rating


@given("a default OpenSkill model", target_fixture="model")
def given_default_model():
    return get_openskill_model()


@when(parsers.parse('I create a rating for "{name}"'), target_fixture="rating")
def create_default_rating(model, name):
    return create_rating(model, name=name)


@when(
    parsers.parse('I create a rating for "{name}" with mu {mu:f} and sigma {sigma:f}'),
    target_fixture="rating",
)
def create_custom_rating(model, name, mu, sigma):
    return create_rating(model, mu=mu, sigma=sigma, name=name)


@then("the rating should have the model's default mu")
def check_rating_default_mu(rating, model):
    assert rating.mu == model.mu


@then("the rating should have the model's default sigma")
def check_rating_default_sigma(rating, model):
    assert rating.sigma == model.sigma


@then(parsers.parse('the rating name should be "{expected}"'))
def check_rating_name(rating, expected):
    assert rating.name == expected


@then(parsers.parse("the rating mu should be {expected:f}"))
def check_rating_mu(rating, expected):
    assert rating.mu == expected


@then(parsers.parse("the rating sigma should be {expected:f}"))
def check_rating_sigma(rating, expected):
    assert rating.sigma == expected


# Scenarios: Update ratings


@given(parsers.parse('a player "{name}" with default rating'))
def player_with_default_rating(context, model, name):
    rating = create_rating(model, name=name)
    context[name] = rating
    # Store a snapshot, as rating objects might be mutable or reused
    context[f"initial_{name}"] = SimpleNamespace(mu=rating.mu, sigma=rating.sigma)
    return rating


@when(parsers.parse('the "{winner}" wins against "{loser}"'))
def winner_wins(context, model, winner, loser):
    r1 = context[winner]
    r2 = context[loser]
    new_r1, new_r2 = rate_teams(model, [r1], [r2], "win_a")
    # rate_teams returns list of lists (teams), extracting first player of each team
    context[winner] = new_r1[0]
    context[loser] = new_r2[0]


@when(parsers.parse('"{p1}" and "{p2}" draw'))
def players_draw(context, model, p1, p2):
    r1 = context[p1]
    r2 = context[p2]
    new_r1, new_r2 = rate_teams(model, [r1], [r2], "draw")
    context[p1] = new_r1[0]
    context[p2] = new_r2[0]


@then(parsers.parse('the "{player}" rating mu should increase'))
def check_rating_increase(context, player):
    initial = context[f"initial_{player}"]
    current = context[player]
    assert current.mu > initial.mu


@then(parsers.parse('the "{player}" rating mu should decrease'))
def check_rating_decrease(context, player):
    initial = context[f"initial_{player}"]
    current = context[player]
    assert current.mu < initial.mu


@then(parsers.parse('the rating difference between "{p1}" and "{p2}" should be negligible'))
def check_rating_diff_negligible(context, p1, p2):
    r1 = context[p1]
    r2 = context[p2]
    assert abs(r1.mu - r2.mu) < 0.001


# Scenario: Invalid results


@when(parsers.parse('I attempt to rate them with an invalid result "{result}"'))
def attempt_invalid_rate(context, model, result):
    # We assume P1 and P2 are already in context from previous steps or setup
    # But for this specific scenario, let's ensure we grab them or fail if not present.
    # The scenario says: Given ... And a player "P1" ... And a player "P2" ...
    # So they are in context.
    r1 = context["P1"]
    r2 = context["P2"]

    with pytest.raises(ValueError) as excinfo:
        rate_teams(model, [r1], [r2], result)
    context["error"] = excinfo.value


@then("a ValueError should be raised")
def check_value_error(context):
    assert isinstance(context.get("error"), ValueError)
