import json
import random
from pathlib import Path

TRIBUNALS = [
    "Labor Court",
    "Criminal Court",
    "Civil Court",
    "Electoral Court",
]


def generate_case(idx: int) -> dict:
    primary = random.choice(TRIBUNALS)
    others = random.sample([t for t in TRIBUNALS if t != primary], 2)
    return {
        "case_id": f"XT{idx:03d}",
        "primary_tribunal": primary,
        "cross_referenced_tribunals": others,
        "summary": f"Example cross tribunal case {idx}",
    }


def generate_dataset(num_cases: int = 10) -> list:
    return [generate_case(i + 1) for i in range(num_cases)]


def main() -> None:
    dataset = generate_dataset()
    output_path = Path(__file__).parent / "cross_tribunal_cases.json"
    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=2)
    print(f"Generated {output_path}")


if __name__ == "__main__":
    main()
