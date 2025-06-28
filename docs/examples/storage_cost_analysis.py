"""Example: Estimate storage costs on Internet Archive."""

from pathlib import Path

BYTES_IN_TB = 1024 ** 4
DEFAULT_PRICE_PER_TB = 6.0  # USD per month


def estimate_monthly_cost(bytes_stored: int, price_per_tb: float = DEFAULT_PRICE_PER_TB) -> float:
    """Return estimated monthly cost in USD."""
    return (bytes_stored / BYTES_IN_TB) * price_per_tb


def main() -> None:
    # Example using the provided DuckDB file size
    db_file = Path("data/causaganha.duckdb")
    if db_file.exists():
        size = db_file.stat().st_size
    else:
        # Fallback to 1 GiB if the file is missing
        size = 1 * 1024 ** 3

    cost = estimate_monthly_cost(size)
    print(f"Archive size: {size / 1_048_576:.2f} MB")
    print(f"Estimated monthly cost: ${cost:.2f} at $6/TB")


if __name__ == "__main__":
    main()
