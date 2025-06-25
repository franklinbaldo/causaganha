import math
import logging

# --- Advogado ID Management Note ---
# The 'advogado_id' used in ratings.csv and partidas.csv needs to be a unique and stable identifier
# for each lawyer. Potential strategies:
# 1. OAB Number: Ideal if consistently available and unique across states/sections.
# 2. Full Name + State/OAB Section: A composite key if OAB number alone isn't sufficient.
# 3. Internal UUID: Generate a UUID for each unique lawyer encountered. Requires careful
#    management to avoid duplicates if names have variations.
# For initial development, 'nome_advogado' might be used directly as 'advogado_id' under the
# assumption of unique names, but this is not robust for production.
# The actual source and normalization of lawyer names/IDs will be handled during data
# processing before Elo updates.
# --- End Advogado ID Management Note ---


DEFAULT_K_FACTOR = 16


def expected_score(rating_a: float, rating_b: float) -> float:
    """
    Calculates the expected score of player A against player B.
    E_A = 1 / (1 + 10^((rating_B - rating_A) / 400))

    Args:
        rating_a: Elo rating of player A.
        rating_b: Elo rating of player B.

    Returns:
        The expected score (probability of winning) for player A.
    """
    return 1 / (1 + math.pow(10, (rating_b - rating_a) / 400))


def update_elo(
    rating_a: float, rating_b: float, score_a: float, k_factor: int = DEFAULT_K_FACTOR
) -> tuple[float, float]:
    """
    Updates Elo ratings for player A and player B based on the actual score for player A.

    Args:
        rating_a: Current Elo rating of player A.
        rating_b: Current Elo rating of player B.
        score_a: Actual score achieved by player A (1 for win, 0.5 for draw, 0 for loss).
        k_factor: The K-factor, determining the maximum rating change. Defaults to 16.

    Returns:
        A tuple containing the new Elo ratings for player A and player B (new_rating_a, new_rating_b).
    """
    if not (0 <= score_a <= 1):
        raise ValueError("score_a must be between 0 and 1 (inclusive).")

    # Calculate expected scores
    e_a = expected_score(rating_a, rating_b)
    # e_b = expected_score(rating_b, rating_a) # or 1 - e_a

    # Update ratings
    # For player A: R'_A = R_A + K * (S_A - E_A)
    new_rating_a = rating_a + k_factor * (score_a - e_a)

    # For player B, their score (score_b) is (1 - score_a)
    # Their expected score (e_b) is (1 - e_a)
    # So, R'_B = R_B + K * ((1 - S_A) - (1 - E_A))
    # This simplifies to: R'_B = R_B - K * (S_A - E_A)
    # Which means the total change in Elo points in the system is zero.
    new_rating_b = rating_b - k_factor * (score_a - e_a)
    # Alternatively:
    # score_b = 1 - score_a
    # new_rating_b = rating_b + k_factor * (score_b - e_b)
    # Both yield the same result if e_b = 1 - e_a

    return round(new_rating_a, 2), round(
        new_rating_b, 2
    )  # Round to typical Elo precision


if __name__ == "__main__":
    logging.info("=" * 50)
    logging.info("ELO CALCULATION DEMONSTRATION")
    logging.info("=" * 50)

    # Example 1: Player A (1500) vs Player B (1500)
    r_a1, r_b1 = 1500.0, 1500.0
    logging.info(f"\n--- SCENARIO 1: Equal Ratings (A={r_a1}, B={r_b1}) ---")

    # Scenario 1.1: Player A wins (score_a = 1.0)
    logging.info(
        f"Inputs: rating_a={r_a1}, rating_b={r_b1}, score_a=1.0, k_factor={DEFAULT_K_FACTOR}"
    )
    e_a1_win = expected_score(r_a1, r_b1)
    logging.info(f"Expected score for A: {e_a1_win:.4f}")
    new_r_a1_win, new_r_b1_win = update_elo(r_a1, r_b1, 1.0)
    logging.info(f"Output: A wins -> New Ratings: A={new_r_a1_win}, B={new_r_b1_win}")
    logging.info(
        f"Rating change for A: {new_r_a1_win - r_a1:+.2f}, for B: {new_r_b1_win - r_b1:+.2f}"
    )

    # Scenario 1.2: Draw (score_a = 0.5)
    logging.info(
        f"\nInputs: rating_a={r_a1}, rating_b={r_b1}, score_a=0.5, k_factor={DEFAULT_K_FACTOR}"
    )
    e_a1_draw = expected_score(
        r_a1, r_b1
    )  # Expected score doesn't change based on outcome
    logging.info(f"Expected score for A: {e_a1_draw:.4f}")
    new_r_a1_draw, new_r_b1_draw = update_elo(r_a1, r_b1, 0.5)
    logging.info(f"Output: Draw -> New Ratings: A={new_r_a1_draw}, B={new_r_b1_draw}")
    logging.info(
        f"Rating change for A: {new_r_a1_draw - r_a1:+.2f}, for B: {new_r_b1_draw - r_b1:+.2f}"
    )

    # Scenario 1.3: Player A loses (score_a = 0.0)
    logging.info(
        f"\nInputs: rating_a={r_a1}, rating_b={r_b1}, score_a=0.0, k_factor={DEFAULT_K_FACTOR}"
    )
    e_a1_loss = expected_score(r_a1, r_b1)
    logging.info(f"Expected score for A: {e_a1_loss:.4f}")
    new_r_a1_loss, new_r_b1_loss = update_elo(r_a1, r_b1, 0.0)
    logging.info(
        f"Output: A loses -> New Ratings: A={new_r_a1_loss}, B={new_r_b1_loss}"
    )
    logging.info(
        f"Rating change for A: {new_r_a1_loss - r_a1:+.2f}, for B: {new_r_b1_loss - r_b1:+.2f}"
    )

    # Example 2: Player A (1600) vs Player B (1400)
    r_a2, r_b2 = 1600.0, 1400.0
    logging.info(f"\n--- SCENARIO 2: Different Ratings (A={r_a2}, B={r_b2}) ---")

    # Scenario 2.1: Player A (higher rated) wins
    logging.info(
        f"\nInputs: rating_a={r_a2}, rating_b={r_b2}, score_a=1.0, k_factor={DEFAULT_K_FACTOR}"
    )
    e_a2_win = expected_score(r_a2, r_b2)
    logging.info(f"Expected score for A: {e_a2_win:.4f}")
    new_r_a2_win, new_r_b2_win = update_elo(r_a2, r_b2, 1.0)
    logging.info(
        f"Output: A (1600) wins against B (1400) -> New Ratings: A={new_r_a2_win}, B={new_r_b2_win}"
    )
    logging.info(
        f"Rating change for A: {new_r_a2_win - r_a2:+.2f}, for B: {new_r_b2_win - r_b2:+.2f}"
    )

    # Scenario 2.2: Player A (higher rated) loses (upset)
    logging.info(
        f"\nInputs: rating_a={r_a2}, rating_b={r_b2}, score_a=0.0, k_factor={DEFAULT_K_FACTOR}"
    )
    e_a2_loss = expected_score(r_a2, r_b2)
    logging.info(f"Expected score for A: {e_a2_loss:.4f}")
    new_r_a2_loss, new_r_b2_loss = update_elo(r_a2, r_b2, 0.0)
    logging.info(
        f"Output: A (1600) loses against B (1400) -> New Ratings: A={new_r_a2_loss}, B={new_r_b2_loss}"
    )
    logging.info(
        f"Rating change for A: {new_r_a2_loss - r_a2:+.2f}, for B: {new_r_b2_loss - r_b2:+.2f}"
    )

    # Example 3: Different K-factor
    r_a3, r_b3 = 1500.0, 1500.0
    k_custom = 32
    logging.info(f"\n--- SCENARIO 3: Custom K-Factor (K={k_custom}) ---")
    logging.info(
        f"Inputs: rating_a={r_a3}, rating_b={r_b3}, score_a=1.0, k_factor={k_custom}"
    )
    e_a3_win = expected_score(r_a3, r_b3)
    logging.info(f"Expected score for A: {e_a3_win:.4f}")
    new_r_a3_win, new_r_b3_win = update_elo(r_a3, r_b3, 1.0, k_factor=k_custom)
    logging.info(
        f"Output: A wins (K={k_custom}) -> New Ratings: A={new_r_a3_win}, B={new_r_b3_win}"
    )
    logging.info(
        f"Rating change for A: {new_r_a3_win - r_a3:+.2f}, for B: {new_r_b3_win - r_b3:+.2f}"
    )

    # Test ValueError for score_a
    logging.info("\n--- SCENARIO 4: Invalid Score Input ---")
    try:
        logging.info(
            f"Inputs: rating_a=1500, rating_b=1500, score_a=1.5, k_factor={DEFAULT_K_FACTOR}"
        )
        update_elo(1500, 1500, 1.5)
    except ValueError as e:
        logging.info(f"Output: Successfully caught error for invalid score_a: {e}")

    logging.info("=" * 50)
    logging.info("END OF DEMONSTRATION")
    logging.info("=" * 50)
