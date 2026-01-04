"""Domain services for scoring."""

from typing import Any

from causaganha.scoring.openskill import Rating, create_rating, get_openskill_model, rate_teams


def calculate_batch_ratings(
    match_results: list[dict[str, Any]],
    current_ratings: list[dict[str, Any]],
) -> dict[tuple[str, str], Rating]:
    """Calculate new ratings for a batch of match results.

    This function is pure domain logic: it takes data structures (dicts) and
    returns updated Rating objects. It does not perform any I/O.

    Args:
        match_results: List of analysis result dicts containing winner/loser info.
        current_ratings: List of current lawyer rating dicts from the repository.

    Returns:
        A dictionary mapping (oab, state) -> Rating object with updated stats.
    """
    model = get_openskill_model()
    ratings_cache: dict[tuple[str, str], Rating] = {}

    # Initialize cache from current ratings
    for r in current_ratings:
        key = (r["oab_number"], r["oab_state"])
        rating = create_rating(model, mu=r["mu"], sigma=r["sigma"], name=f"{key[0]}-{key[1]}")
        # Attach stats to the rating object (dynamically)
        rating.stats = {
            "total_cases": r["total_cases"],
            "wins": r["wins"],
            "losses": r["losses"],
        }
        ratings_cache[key] = rating

    # Ensure all needed lawyers are in cache (create new if missing)
    # We first identify all needed lawyers from the matches
    needed_lawyers = set()
    for row in match_results:
        if row.get("winner_lawyer_oab") and row.get("winner_lawyer_state"):
            needed_lawyers.add((row["winner_lawyer_oab"], row["winner_lawyer_state"]))
        if row.get("loser_lawyer_oab") and row.get("loser_lawyer_state"):
            needed_lawyers.add((row["loser_lawyer_oab"], row["loser_lawyer_state"]))

    for oab, state in needed_lawyers:
        if (oab, state) not in ratings_cache:
            rating = create_rating(model, name=f"{oab}-{state}")
            rating.stats = {"total_cases": 0, "wins": 0, "losses": 0}
            ratings_cache[(oab, state)] = rating

    # Process matches
    for row in match_results:
        winner_oab = row.get("winner_lawyer_oab")
        winner_state = row.get("winner_lawyer_state")
        loser_oab = row.get("loser_lawyer_oab")
        loser_state = row.get("loser_lawyer_state")

        if not (winner_oab and winner_state and loser_oab and loser_state):
            continue

        r_winner = ratings_cache.get((winner_oab, winner_state))
        r_loser = ratings_cache.get((loser_oab, loser_state))

        if not r_winner or not r_loser:
            continue

        # Determine result for OpenSkill
        result_code = "win_a"  # Winner (A) vs Loser (B)

        # Update ratings
        new_winner, new_loser = rate_teams(model, [r_winner], [r_loser], result_code)

        # Update cache objects
        r_winner_updated = new_winner[0]
        # Copy stats and increment
        r_winner_updated.stats = getattr(r_winner, "stats", {"total_cases": 0, "wins": 0, "losses": 0}).copy()
        r_winner_updated.stats["total_cases"] += 1
        r_winner_updated.stats["wins"] += 1
        ratings_cache[(winner_oab, winner_state)] = r_winner_updated

        r_loser_updated = new_loser[0]
        r_loser_updated.stats = getattr(r_loser, "stats", {"total_cases": 0, "wins": 0, "losses": 0}).copy()
        r_loser_updated.stats["total_cases"] += 1
        r_loser_updated.stats["losses"] += 1
        ratings_cache[(loser_oab, loser_state)] = r_loser_updated

    return ratings_cache
