import json
import random
from datetime import datetime, timedelta
from pathlib import Path

COURTS = [
    "Supreme Court",
    "District Court",
    "Appellate Court",
    "Labor Court",
    "Small Claims Court",
]

OUTCOMES = ["Affirmed", "Dismissed", "Reversed", "Remanded", "Settled"]
KEYWORDS = [
    "contract",
    "negligence",
    "criminal law",
    "labor dispute",
    "appeal",
    "torts",
    "due process",
]


def random_date(start_year=2022, end_year=2025):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")


def generate_decision(case_id: int) -> dict:
    """Generate a single mock judicial decision."""
    return {
        "case_id": f"CASE{case_id:04d}",
        "date": random_date(),
        "court": random.choice(COURTS),
        "judges": [f"Judge {chr(65 + i)}" for i in range(random.randint(1, 3))],
        "outcome": random.choice(OUTCOMES),
        "keywords": random.sample(KEYWORDS, random.randint(1, 3)),
    }


def generate_dataset(num_cases: int = 20) -> list:
    """Create a list of mock decisions."""
    return [generate_decision(i + 1) for i in range(num_cases)]


def main():
    dataset = generate_dataset()
    output_path = Path(__file__).parent / "judicial_decisions.json"
    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"Generated {len(dataset)} mock decisions to {output_path}")


if __name__ == "__main__":
    main()
