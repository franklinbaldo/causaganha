"""Example: Load testing script for multi-tribunal ingestion."""

import subprocess

TRIBUNALS = ["TJRO", "TJSP", "TJMG"]


def run_pipeline(tribunal: str) -> None:
    """Run the async pipeline for a specific tribunal in stats-only mode."""
    subprocess.run(
        [
            "uv",
            "run",
            "python",
            "src/async_diario_pipeline.py",
            f"--tribunal={tribunal}",
            "--max-items",
            "1",
            "--stats-only",
        ],
        check=False,
    )


def main() -> None:
    for trib in TRIBUNALS:
        print(f"\nRunning pipeline for {trib} (stats only)...")
        run_pipeline(trib)


if __name__ == "__main__":
    main()
