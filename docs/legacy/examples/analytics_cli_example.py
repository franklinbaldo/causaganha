"""Example usage of the analytics CLI commands."""

import subprocess


def show_outcome_trend(limit: int = 20) -> None:
    subprocess.run([
        "causaganha",
        "analytics",
        "outcome-trend",
        "--limit",
        str(limit),
    ], check=False)


def show_rating_trend(lawyer_id: str) -> None:
    subprocess.run([
        "causaganha",
        "analytics",
        "rating-trend",
        "--lawyer-id",
        lawyer_id,
    ], check=False)


if __name__ == "__main__":
    print("Resumo de tendências de decisões:")
    show_outcome_trend(limit=10)
    print("\nTendência de rating para advogado 123:")
    show_rating_trend("123")

