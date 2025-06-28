from typing import Dict, Any, Optional
from openskill.models import PlackettLuce
from openskill.models.weng_lin.plackett_luce import (
    PlackettLuceRating as OpenSkillRating,
)

# Default model parameters, to be used if no config is provided
DEFAULT_OS_MU = 25.0
DEFAULT_OS_SIGMA = 25.0 / 3.0
DEFAULT_OS_BETA = 25.0 / 6.0
DEFAULT_OS_TAU = (25.0 / 3.0) / 5.0  # sigma / 5, increased for more noticeable changes

OS_CONFIG_TYPE = Optional[Dict[str, Any]]


def get_openskill_model(os_config: OS_CONFIG_TYPE = None) -> PlackettLuce:
    """
    Initializes and returns an OpenSkill PlackettLuce model.
    Uses parameters from os_config if provided, otherwise uses defaults.
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
    os_model: PlackettLuce, mu: Optional[float] = None, sigma: Optional[float] = None, name: Optional[str] = None
) -> OpenSkillRating:
    """
    Creates an OpenSkill Rating object using the provided model.
    If mu and sigma are not provided, uses the model's default (os_model.rating()).
    If mu and sigma are provided, it creates a rating with these specific values (os_model.create_rating()).
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
    """
    Updates ratings based on the match outcome using the provided OpenSkill model.
    """
    teams = [team_a_ratings, team_b_ratings]

    if result == "win_a":
        ranks = [0, 1]
        print(
            f"Before rating (win_a): team_a_ratings={team_a_ratings}, team_b_ratings={team_b_ratings}"
        )
        new_ratings = os_model.rate(teams, ranks=ranks)
        print(f"After rating (win_a): new_ratings={new_ratings}")
    elif result == "win_b":
        ranks = [1, 0]
        print(
            f"Before rating (win_b): team_a_ratings={team_a_ratings}, team_b_ratings={team_b_ratings}"
        )
        new_ratings = os_model.rate(teams, ranks=ranks)
        print(f"After rating (win_b): new_ratings={new_ratings}")
    elif result == "draw":
        ranks = [0, 0]
        print(
            f"Before rating (draw): team_a_ratings={team_a_ratings}, team_b_ratings={team_b_ratings}"
        )
        new_ratings = os_model.rate(teams, ranks=ranks)
        print(f"After rating (draw): new_ratings={new_ratings}")
    elif result == "partial_a":
        ranks = [0, 1]
        new_ratings = os_model.rate(teams, ranks=ranks, tau=partial_play_tau)
    elif result == "partial_b":
        ranks = [1, 0]
        new_ratings = os_model.rate(teams, ranks=ranks, tau=partial_play_tau)
    else:
        raise ValueError(
            f"Unknown match result: {result}. Expected 'win_a', 'win_b', 'draw', 'partial_a', or 'partial_b'."
        )

    return new_ratings[0], new_ratings[1]


if __name__ == "__main__":
    print("OpenSkill Rating Module Example (Configurable Model)")

    example_model = get_openskill_model()
    print(
        f"Example model initialized with: mu={example_model.mu:.2f}, sigma={example_model.sigma:.2f}, beta={example_model.beta:.2f}, tau={example_model.tau:.4f}"
    )

    # Initial ratings for first scenario (Team A wins)
    player1_ex1 = create_rating(example_model, name="Player1_ex1")
    player2_ex1 = create_rating(
        example_model, mu=30.0, sigma=example_model.sigma, name="Player2_ex1"
    )
    player3_ex1 = create_rating(example_model, name="Player3_ex1")

    print(
        f"Initial {player1_ex1.name}: mu={player1_ex1.mu:.2f}, sigma={player1_ex1.sigma:.2f}"
    )
    print(
        f"Initial {player2_ex1.name}: mu={player2_ex1.mu:.2f}, sigma={player2_ex1.sigma:.2f}"
    )
    print(
        f"Initial {player3_ex1.name}: mu={player3_ex1.mu:.2f}, sigma={player3_ex1.sigma:.2f}"
    )

    print("\n--- Scenario 1: Team A (P1, P2) vs Team B (P3) ---")
    team_a_ex1 = [player1_ex1, player2_ex1]
    team_b_ex1 = [player3_ex1]

    print("\nTeam A wins:")
    updated_team_a_ex1, updated_team_b_ex1 = rate_teams(
        example_model, team_a_ex1, team_b_ex1, "win_a"
    )
    p1_updated_ex1, p2_updated_ex1 = updated_team_a_ex1
    p3_updated_ex1 = updated_team_b_ex1[0]
    print(
        f"Updated {p1_updated_ex1.name}: mu={p1_updated_ex1.mu:.2f}, sigma={p1_updated_ex1.sigma:.2f}"
    )
    print(
        f"Updated {p2_updated_ex1.name}: mu={p2_updated_ex1.mu:.2f}, sigma={p2_updated_ex1.sigma:.2f}"
    )
    print(
        f"Updated {p3_updated_ex1.name}: mu={p3_updated_ex1.mu:.2f}, sigma={p3_updated_ex1.sigma:.2f}"
    )

    # Fresh ratings for Draw scenario
    player1_ex2 = create_rating(example_model, name="Player1_ex2")
    player2_ex2 = create_rating(
        example_model, mu=30.0, sigma=example_model.sigma, name="Player2_ex2"
    )
    player3_ex2 = create_rating(example_model, name="Player3_ex2")
    team_a_ex2 = [player1_ex2, player2_ex2]
    team_b_ex2 = [player3_ex2]

    print("\nDraw:")
    updated_team_a_draw, updated_team_b_draw = rate_teams(
        example_model, team_a_ex2, team_b_ex2, "draw"
    )
    p1_draw, p2_draw = updated_team_a_draw
    p3_draw = updated_team_b_draw[0]
    print(f"Updated {p1_draw.name}: mu={p1_draw.mu:.2f}, sigma={p1_draw.sigma:.2f}")
    print(f"Updated {p2_draw.name}: mu={p2_draw.mu:.2f}, sigma={p2_draw.sigma:.2f}")
    print(f"Updated {p3_draw.name}: mu={p3_draw.mu:.2f}, sigma={p3_draw.sigma:.2f}")

    # Fresh ratings for Partial Win scenario
    player1_ex3 = create_rating(example_model, name="Player1_ex3")
    player2_ex3 = create_rating(
        example_model, mu=30.0, sigma=example_model.sigma, name="Player2_ex3"
    )
    player3_ex3 = create_rating(example_model, name="Player3_ex3")
    team_a_ex3 = [player1_ex3, player2_ex3]
    team_b_ex3 = [player3_ex3]

    print("\nPartial win for Team A (tau=0.7):")
    updated_team_a_partial, updated_team_b_partial = rate_teams(
        example_model, team_a_ex3, team_b_ex3, "partial_a", partial_play_tau=0.7
    )
    p1_partial, p2_partial = updated_team_a_partial
    p3_partial = updated_team_b_partial[0]

    print(
        f"Updated {p1_partial.name}: mu={p1_partial.mu:.2f}, sigma={p1_partial.sigma:.2f}"
    )
    print(
        f"Updated {p2_partial.name}: mu={p2_partial.mu:.2f}, sigma={p2_partial.sigma:.2f}"
    )
    print(
        f"Updated {p3_partial.name}: mu={p3_partial.mu:.2f}, sigma={p3_partial.sigma:.2f}"
    )

    print("\n--- Scenario 2: 1v1 ---")
    player1_sc2 = create_rating(example_model, name="Player1_sc2")
    player3_sc2 = create_rating(example_model, name="Player3_sc2")
    team_p1_sc2 = [player1_sc2]
    team_p3_sc2 = [player3_sc2]

    print("\nPlayer 1 wins:")
    updated_p1_team, updated_p3_team = rate_teams(
        example_model, team_p1_sc2, team_p3_sc2, "win_a"
    )
    p1_1v1_win = updated_p1_team[0]
    p3_1v1_lose = updated_p3_team[0]
    print(
        f"Updated {p1_1v1_win.name}: mu={p1_1v1_win.mu:.2f}, sigma={p1_1v1_win.sigma:.2f}"
    )
    print(
        f"Updated {p3_1v1_lose.name}: mu={p3_1v1_lose.mu:.2f}, sigma={p3_1v1_lose.sigma:.2f}"
    )

    teams_for_predict = [[player1_sc2], [player3_sc2]]
    draw_probability = example_model.predict_draw(teams_for_predict)
    win_probabilities = example_model.predict_win(teams_for_predict)
    print(
        f"\nPrediction for {player1_sc2.name} vs {player3_sc2.name} (initial ratings for this 1v1 scenario):"
    )
    print(f"Draw probability: {draw_probability * 100:.2f}%")
    if win_probabilities:
        print(
            f"Win probability for {player1_sc2.name}: {win_probabilities[0] * 100:.2f}%"
        )
        print(
            f"Win probability for {player3_sc2.name}: {win_probabilities[1] * 100:.2f}%"
        )
